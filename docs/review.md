I've now read the full resolution layer, the specification models, both analyzers, the config/CLI wiring, the scope/symbol subsystem, and run the suite (288 pass) plus targeted empirical checks. Here are my notes.

---

## Verdict

The module-resolution refactor is **strong, principled work**. The central architecture matches the policy closely, the motivating failure case is genuinely solved and tested, and the model layer is now free of ambient resolution. The main gaps are (1) two concrete correctness bugs, both latent today but real, (2) a conceptual mismatch where the policy's "resolution modes" collapsed into one algorithm in practice, and (3) the end-goal scaffolding exists but the *existing* scope/symbol subsystem is a pre-resolution island that currently embodies the exact anti-pattern the policy warns against.

I'll go through your six questions, then give a prioritized fix list.

---

## 1. Conceptual issues with the design

**Resolution modes are cosmetic, not behavioral.** `resolve_project_name`, `resolve_runtime_name`, and `resolve_environment_name` (`resolution/resolver.py:45-79`) all dispatch to the same `_resolve_module_name`, which is byte-identical except for the `mode` enum it stamps onto the result. The only thing that actually changes behavior is the `TargetEnvironment` passed at *construction* time. Consequences:

- `resolve_environment_name` is never called anywhere; `resolve_runtime_name` is used only by `RuntimeModuleLookup`. The mode taxonomy the policy spends a whole section on ("Runtime resolution *may consult `sys.modules`*… *may use `importlib.util.find_spec`*"; environment uses `pkgutil`/`importlib`) is **not implemented** — everything is `PathFinder` against an environment's paths.
- `mode` is a property of the *call* while the search behavior is a property of the *service*; nothing keeps them consistent. A `resolve_runtime_name` on a project-configured service would do project resolution but label it `RUNTIME`.
- The diagnostic use case that *motivates* the whole document — "what would this interpreter import right now, given a polluted `sys.modules`?" — is now unsupported by any mode.

I think the unification is actually *better* than the policy's three-algorithm vision (it's deterministic and never executes code), but the document oversells distinct modes and the code carries dead API. Either give the modes teeth or collapse to one method + a provenance label, and update the policy to say so.

**Structured diagnostics are discarded at the graph boundary.** `ModuleResolution` carries a rich `ResolutionDiagnostic` (stable code + keyed details). But the conversion to the graph-facing model collapses it to `Exception(resolution.reason or "module not resolved")` (`resolution/conversion.py:18`). Design goal #4 ("every resolution result explainable: which name, path, root, category, and spec source") holds *inside* the resolution layer and is lost the moment a result becomes an `UnavailableModule` — which is the object your consumers and output actually see. The diagnostic code in particular (`MODULE_SPEC_NOT_FOUND` vs `RELATIVE_IMPORT_ESCAPES_PACKAGE` vs `AMBIGUOUS_FROM_IMPORT`) is exactly the kind of thing that should survive to output.

**`is_package` is defined on the wrong axis from how the resolution layer reasons.** The resolution layer treats "not a package" as an *empty tuple* and tests packagehood by truthiness (`classification.py:35`, `collector.py:341-342`). The spec `Module` treats it as `None` and tests `is not None` (`module.py:60`). These two conventions collide at the conversion boundary — see bug #1 below. This is a conflated-concept smell: "has no submodule search locations" and "is not a package" are being encoded two different ways.

---

## 2. Does the code follow the document's principles?

Largely **yes**, and impressively so on the structural points:

- Facade + focused collaborators is implemented exactly as the "Expected Resolver Responsibilities" section prescribes (`ModuleSpecResolver`, `ModuleLocationFactory`, `FilesystemModuleLocator`, `ImportPathCandidateBuilder`, `ModuleClassifier`, `CategorizedModuleBuilder`, `TargetSearchPath`).
- Ubiquitous language is honored almost 1:1 with the terminology section.
- `Module`/`ModuleSource` no longer perform ambient resolution — grep for `util.find_spec`/`sys.modules`/`register_search_path` across `specification/` and `models/` is **clean**. `register_search_path` is now defined (`analyzer/base.py:13`) but never called, confirming "analyzers no longer mutate the interpreter search path."
- The spec-vs-helper boundary is documented (`specification-boundary-audit.md`) and mostly honored: `ModuleCoordinates` is correctly un-exported, `NamespacePortion` correctly promoted to a fact.

One real inconsistency with your own coding rules: the **new** resolution layer has zero comments/docstrings (matches your no-comments rule), but the **older** `analyzer/scope/*` subsystem is heavily docstringed (76 comment/docstring lines). Two eras living in one tree.

---

## 3. Does it achieve the document's stated goals?

The headline goals are **met and verified**:

- **Motivating case solved.** A local regular package `tests` resolves `LOCAL` even with an external `tests` on an external root, and `test_resolver.py` covers the harder variants — including `test_project_resolution_prefers_source_root_over_loaded_shadow_module`, which loads the shadow into `sys.modules` first and confirms the local one still wins. This is the core promise and it holds.
- Target environment is explicit, source-roots-first, reproducible, no `sys.path` mutation.
- Namespace portions are preserved as typed facts with per-portion root + category.
- From-import ambiguity is modeled with typed `SUBMODULE`/`EXPORTED_OBJECT` alternatives, with the namespace-package special-case handled correctly (namespace can't export, so a named import must be a submodule — `resolver.py:166-170`).

Not yet met (and the current-state doc is honest about these): caching keyed by environment, and the entire symbol/call-graph layer.

---

## 4. Is the implementation correct?

Two **confirmed bugs** (both reproduced):

**Bug 1 — every source module is mis-typed as a package.** `CategorizedModuleBuilder` forwards `submodule_search_locations=resolution.location.submodule_search_locations` (`conversion.py:26`), which is `()` for a `.py` module. `Module.is_package` is `submodule_search_locations is not None` (`module.py:60`), and `() is not None` is `True`. Reproduced end-to-end:

```
resolve_filesystem_path("src/pda/constants.py") -> kind=source_module
  CategorizedModule.is_package = True
  CategorizedModule.is_module = False
  CategorizedModule.type      = package
```

It's **latent today** — no consumer branches on `is_package`/`type`/`is_module`; recursion keys off tuple truthiness (`collector.py:341`) and serialization emits `category`, not `type` (`models/module/node.py:65`). But it's a false fact in a model whose entire selling point is correct facts, and the symbol/call work *will* care about module-vs-package. Root-cause fix: pick one convention. Either the builder maps `() → None`, or `ModuleLocation`/`Module` agree on truthiness throughout.

**Bug 2 — a top-level single-file module fabricates its own containing package.** `SourceModuleContext.containing_package` returns `parent_name or self.identity.top_level_name` (`models/source.py:25`). For a top-level module `lonely`, `parent_name` is `None`, so it returns `"lonely"` — treating the module as if it were its own package. Reproduced: `from . import sibling` inside top-level `lonely.py` resolves to `status=ambiguous` (submodule `lonely.sibling` vs object exported by `lonely`) instead of `RELATIVE_IMPORT_ESCAPES_PACKAGE`. Per the policy ("If the relative import escapes the containing package, the result is unavailable with a resolution error"), a top-level module has no containing package and level≥1 should escape. Fix is localized: return `""`/`None` when there's no parent and the module isn't itself a package.

One **latent inconsistency** (low impact): `matched_root_for_path` (`classification.py:92`) checks `local_boundary` *after* stdlib/sys_path roots, while `category_for_path` (`classification.py:107`) checks it *before*. A path under both `local_boundary` and a stdlib/sys_path root would be categorized `LOCAL` but matched to a stdlib root. Only reachable with pathological overlap (e.g. local_boundary inside a venv), but the two orderings should match.

Everything else I traced — the parent-path traversal in `ModuleSpecResolver._find_project_path_spec`, the local-spec-vs-full-spec selection for namespace shadowing (`specs.py:56-67`), the candidate ordering, the namespace special-casing — is correct.

---

## 5. Is the code well organized and written?

**Yes**, with minor nits. The decomposition is clean, the dataclasses are frozen, `StrEnum`/typed throughout, error handling is typed (no bare `except`). Nits, in descending order:

- **Duplicated `_namespace_portions`** — identical in `filesystem.py:114` and `locations.py:50`. Both guard `origin is not None or not locations` then delegate to the classifier. Pull into the classifier or a shared helper.
- **`is_relative_to` reimplements stdlib** — `Path.is_relative_to` has existed since 3.9 and you're on 3.13. `resolution/paths.py:8` can go.
- **`CategorizedModule`** has both a `__getattr__` delegation *and* ~15 explicit property delegations to the wrapped module (`categorized.py`). The explicit ones make `__getattr__` mostly dead, and `__getattr__` on a `NamedTuple` is fragile. Pick one.
- `ModuleClassifier.kind` (`classification.py:22`) is an if-ladder where the rest of the file uses `match`; minor stylistic inconsistency.
- `base.py:33` uses a literal `".__init__"` while `identity.py:19` uses `f"{DELIMITER}__init__"` — same value, two spellings.

---

## 6. Does it prepare for the end-goal (function call graph)?

This is the most important answer, and it's **mixed**.

The *primitives* are right and in place: `ModuleIdentity`, `ModuleLocation`, `SourceModuleContext`, `SourceSpan`, `Symbol`, `ScopeType`, and the staged-pipeline vocabulary from the policy. The resolution layer can now hand a parsed file a correct module identity. Good foundation.

**But the existing scope/symbol subsystem is a pre-resolution island that contradicts the policy.** `analyzer/scope/` is ~780 lines (incl. a 453-line `SymbolCollector`) and a `models/scope/` tree — and none of it touches `ModuleResolutionService`, `SourceModuleContext`, or `ModuleIdentity`. `ScopeAnalyzer` builds an `ASTForest` straight from file paths, and symbol FQNs come from `ASTNode.fqn` (`models/python/node.py:41`), which walks AST `.name` attributes. An `ast.Module` has no `.name`, so the module-level prefix is the empty string — symbols come out as `outer.inner`, `Widget.render`, **with no module identity at all**. That is verbatim the failure the policy calls out:

> "An AST by itself cannot provide a correct module FQN… PDA must attach module identity before finalizing symbol FQNs."

Supporting evidence that this layer is unfinished and not yet on the new foundation: `scope/resolver.py` is **empty**, `ScopeBuilder` carries `imports={}  # TODO: populate imports` (`builder.py:100,127`), and `Symbol` stores a raw `ast.AST` as a "specification fact" (`symbol.py:14`) — arguably a worse spec-boundary violation than the ones your audit doc flags (`SysPaths`, `PKGModuleInfo`), yet it's unflagged.

So the honest framing for Q6: the module-resolution refactor builds the *correct* substrate, and the current-state doc correctly names "Source Context for Scope and Calls" as the next phase. But "prepares for the end-goal" should be qualified — the existing symbol layer needs to be **reworked onto `SourceModuleContext`**, not merely extended, and until then it produces module-less FQNs the policy explicitly forbids.

---

## Prioritized fixes

1. **Bug 1** — normalize `() → None` (or unify on truthiness) so source modules aren't packages. One-line root cause at the conversion boundary.
2. **Bug 2** — `containing_package` must not fabricate a package for a top-level module; make level≥1 escape.
3. **Diagnostics** — carry `ResolutionDiagnosticCode` into `UnavailableModule` instead of a bare `Exception`, so failure reasons survive to output.
4. **Modes** — decide: real behavior or provenance label. Remove/justify the unused `resolve_environment_name`, and reconcile the doc.
5. **Scope bridge** — make `Symbol`/`ScopeNode` FQNs derive from a resolved `SourceModuleContext`; treat the existing scope code as needing migration, and add `Symbol`'s raw-`ast.AST` storage to the boundary audit.
6. Cleanups: dedup `_namespace_portions`, drop `is_relative_to`, align the `matched_root`/`category` ordering.
