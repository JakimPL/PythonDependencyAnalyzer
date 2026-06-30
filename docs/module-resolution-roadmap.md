# Module Resolution Roadmap

The module-resolution design in `module-resolution-policy.md` is in place: a
central resolution service, an explicit target environment, fact-only module
models, structured diagnostics, and namespace-aware classification. This document
is the forward plan from there to PDA's end goal — a function call graph that
answers which function calls which — together with the smaller resolution work
still outstanding. The policy is the north star; this roadmap only sequences the
remaining work and records what is deliberately not built yet.

## End goal

A principled call graph. The policy's "Symbol and Call-Graph Readiness" stages the
pipeline: parse → attach module identity → lexical scopes and bindings → import
bindings → name references → call sites → resolved call graph. Each stage owns one
kind of fact, and unresolved edges stay explicit rather than being dropped.

## Phase 1 — Source context for scope and calls

The keystone, and the immediate next step. Attach each parsed AST module to a
resolved `SourceModuleContext` so symbol FQNs carry module identity. Today the
`analyzer/scope` subsystem derives symbol names from AST node names alone, so a
top-level function comes out as `outer.inner` rather than `pkg.mod.outer.inner` —
the exact gap the policy names ("an AST by itself cannot provide a correct module
FQN"). Resolution now supplies that identity; the scope layer must consume it.

## Phase 2 — Symbol and binding model

- Model a lexical symbol path for every binding, marked importable or internal
  (see the policy's "Symbol FQN Policy").
- Preserve import bindings as first-class facts: local name, resolved target, and
  the submodule-vs-exported-object ambiguity that import-path resolution already
  produces — kept separate from ordinary local bindings.
- Resolve `Name` and attribute references through lexical scopes and import
  bindings, keeping attribute chains unflattened.

## Phase 3 — Call extraction and resolution

- Extract call sites syntactically from the AST.
- Resolve callees in tiers: direct lexical functions, import-bound calls, module
  attribute calls, inferred receivers, then dynamic or unknown.
- Emit a call graph carrying confidence and unresolved/partial-edge metadata.

## Cross-cutting resolution work

- A resolution cache keyed by the full target environment (the policy's "Caching
  Policy"). None exists yet; a name-only cache is unsafe because the same name
  resolves differently under different source roots or `sys.path`.
- A live interpreter-state resolution strategy (observing `sys.modules` /
  `importlib.util.find_spec`) remains intentionally unbuilt. Project resolution is
  deterministic by design; if a "what would this interpreter import right now"
  diagnostic is ever wanted, add it as an opt-in strategy selected by the target
  environment, never as default behavior.

## Specification boundary cleanups

`pda.specification` should hold durable facts only; a few types still sit on the
wrong side of that line:

- `SysPaths` reads interpreter installation paths and resolves filesystem paths to
  `ImportPath` — machinery, not a fact. Move it to a tools or resolution-support
  module.
- `PKGModuleInfo` is a `pkgutil` discovery DTO used by `PkgModuleScanner`. Move it
  next to the scanner or into an environment-discovery package.
- `Symbol` stores a raw `ast.AST` node — transient parser state, not a durable
  fact. Keep its source span and identity and reference the node indirectly;
  revisit with Phase 2.
- `ModuleSource` is acceptable as a spec fact while it is a stable source-file
  fact, but revisit once `SourceModuleContext` carries parsed AST and lexical
  context (Phase 1).
- `ModuleIdentity` is resolution-local; promote it to a specification fact only if
  the symbol and call-graph phases need module identity as a first-class
  graph-facing value rather than only `Module.name`.

## Open design questions

The questions gating the symbol and call-graph phases — local-binding FQN
spelling, first-generation call-resolution precision, and whether to adopt
`symtable` — are listed in the policy's "Open Questions" and should be settled
when Phase 1 begins.
