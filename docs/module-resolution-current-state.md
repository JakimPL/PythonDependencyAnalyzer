# Module Resolution Current State

Status: implementation review against `docs/module-resolution-policy.md`

This document summarizes where the current code matches the module-resolution
policy, where it only partially matches, and which gaps should shape the next
reviewable phases.

## Implemented

### Central Resolution Service

`ModuleResolutionService` is now the central facade for module-name resolution,
import-path resolution, filesystem-path resolution, source-context creation, and
conversion to graph-facing module models.

Focused collaborators own the lower-level responsibilities:

- `TargetSearchPath` and `ModuleSpecResolver` own path-based import-system
  lookup.
- `ModuleLocationFactory` converts transient `ModuleSpec` evidence into PDA
  facts.
- `FilesystemModuleLocator` derives module identity from known source paths.
- `ImportPathCandidateBuilder` handles relative import absolutization and
  candidate module names.
- `ModuleClassifier` owns module kind and dependency category classification.
- `CategorizedModuleBuilder` converts resolution results into compatibility
  graph models.

### Explicit Project Context

`ProjectResolutionContext` normalizes:

- `project_root`;
- one or more `source_roots`;
- `local_boundary`.
- explicit `external_roots`;
- whether active interpreter `sys.path` should be included.

Analyzer configs expose `ModuleResolutionConfig` with `source_roots`,
`local_boundary`, `external_roots`, and `include_sys_path`. The CLI maps the
same options into that config. The old analyzer-level `package` input has been
replaced by `AnalysisTarget.root_module_name`.

### Target-Constrained Analysis

When CLI analysis paths are omitted, `AnalysisTargetResolver` resolves the root
module and starts from local target paths instead of scanning the whole source
root.

`ModulesCollector` also starts local collection from the resolved target module
and recurses through that module's package or namespace portions. Sibling
top-level modules are no longer included unless they are the target.

### Fact-Only Module Models

`Module`, `UnavailableModule`, `CategorizedModule`, and `ModuleSource` no longer
perform ambient module resolution.

The model layer no longer exposes or reconstructs `ModuleSpec`. `ModuleSpec`
usage is limited to the resolution layer as transient import-system evidence.

`Module` and `CategorizedModule` also no longer infer dependency categories.
Callers must provide an explicit `ModuleCategory`, and project/runtime category
decisions flow through resolution-layer classification or analyzer lookup
adapters.

### Structured Resolution Diagnostics

Unavailable `ModuleResolution` results now carry a `ResolutionDiagnostic` with a
stable `ResolutionDiagnosticCode`, human-readable message, and keyed details.
The compatibility `reason` property is derived from the diagnostic message
rather than being the only stored failure fact.

Initial diagnostic codes cover missing module specs, empty import paths,
relative imports escaping their package, unresolved import paths, ambiguous
from-imports, paths outside configured source roots, non-Python module paths,
namespace directories without Python children, and generic unresolved filesystem
paths.

### Namespace Package Basics

Filesystem resolution and collection treat directories without `__init__.py` as
namespace package portions when they contain at least one Python file or
package-like child.

Multi-root local namespace portions are collected with per-portion base-path
derivation, so `namespace_pkg.one` and `namespace_pkg.two` can be collected from
different source roots.

`ModuleLocation` now preserves `NamespacePortion` specification facts for
namespace packages. Each portion records the portion path, the matched
configured root, and the portion category. Conversion to `Module` keeps those
facts as explicit module fields so graph models do not lose mixed
local/external namespace information.

### Runtime Collection Through Resolution

Bare runtime/environment collection no longer uses `ModuleCreator`.
`RuntimeModuleLookup` uses `ModuleResolutionService(TargetEnvironment.runtime())`.

### Explicit Resolution Modes

Name-based resolution has explicit project, runtime, and environment entry
points. `ModuleResolution.mode` now records the query mode selected by the
caller instead of always reporting `PROJECT`.

Runtime module lookup uses runtime name resolution, so runtime/environment
collection preserves `ResolutionMode.RUNTIME` in resolver results instead of
passing through the project-resolution path.

### From-Import Ambiguity

Central import-path resolution preserves `from package import name` ambiguity in
`ModuleResolution` results. Ambiguous results carry typed alternatives for the
submodule candidate and the exported-object container candidate, including
whether each alternative resolved.

Regular packages and modules can export names dynamically, so PDA does not
pretend that a `from` import is only a submodule dependency. Namespace packages
without `__init__.py` cannot define exported objects through package code, so a
resolved namespace submodule can still resolve directly.

The current import dependency analyzer adapts ambiguous results back to a module
dependency by preferring a resolved submodule alternative and then a resolved
exported-object container. This is compatibility behavior for module graphs, not
the final symbol-binding model.

### Configurable Project Search Paths

Project contexts can build strict target environments with
`include_sys_path=False`. This is the low-level default for deterministic
project-context construction.

Analyzer and CLI entry points expose the same option through
`ModuleResolutionConfig` and default to `include_sys_path=True` for
compatibility with existing application behavior: `external_depth` can discover
active-environment third-party packages unless a caller disables it.

Config construction emits `PDAExternalResolutionWarning` when external traversal
is enabled but neither active `sys.path` nor explicit `external_roots` can
provide third-party search roots.

Project resolution searches configured source roots before explicit external
roots, interpreter stdlib roots, and optional active `sys.path` roots.

This keeps local project packages and namespace portions source-root bounded.
For example, a local namespace package named `tests` is still resolved from the
project when an unrelated regular `tests` package exists on ambient `sys.path`.

Project analyzers also no longer call `register_search_path`, so constructing
or running an analyzer does not mutate the interpreter search path. The
`register_search_path` helper remains only for explicit runtime-compatible
workflows.

### Explicit External Roots

`ProjectResolutionContext`, `ModuleResolutionConfig`, and the CLI now expose
explicit external dependency roots. `ModulesCollector` also uses the configured
target environment for top-level package discovery, so collection and resolution
share the same external search policy.

## Open Or Not Implemented

### Cache Policy

The policy defines cache-key requirements, but no resolver-level cache keyed by
target environment exists yet.

### Symbol And Call-Graph Readiness

The policy describes `ScopeIdentity`, `SymbolBinding`, `NameReference`, and
`CallSite` requirements. Current module resolution now provides the necessary
module identity and source context primitives, but scope/call analysis has not
yet been migrated onto those primitives.

Open work includes:

- attaching ASTs to `SourceModuleContext`;
- modeling lexical symbol paths;
- preserving import bindings separately from local binding names;
- resolving name references through lexical scopes and imports;
- representing call sites and unresolved candidate callees.

### Import Binding Ambiguity

Import analysis currently builds module dependency edges. It does not yet create
symbol-level import bindings with local name, target, ambiguity, and confidence.

This is required before function-call dependencies can be principled.

## Recommended Next Phases

1. **Source Context For Scope And Calls**
   Start a new phase that attaches parsed AST modules to `SourceModuleContext`
   and prepares lexical symbol FQNs.
