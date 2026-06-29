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

The CLI and analyzer constructors expose `source_roots` and `local_boundary`.
The old analyzer-level `package` input has been replaced by
`AnalysisTarget.root_module_name`.

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

### Namespace Package Basics

Filesystem resolution and collection treat directories without `__init__.py` as
namespace package portions when they contain at least one Python file or
package-like child.

Multi-root local namespace portions are collected with per-portion base-path
derivation, so `namespace_pkg.one` and `namespace_pkg.two` can be collected from
different source roots.

`ModuleLocation` now preserves `NamespacePortion` facts for namespace packages.
Each portion records the portion path, the matched configured root, and the
portion category. Conversion to `Module` keeps those facts in metadata so graph
models do not lose mixed local/external namespace information.

### Runtime Collection Through Resolution

Bare runtime/environment collection no longer uses `ModuleCreator`.
`RuntimeModuleLookup` uses `ModuleResolutionService(TargetEnvironment.runtime())`.

### Strict Project Search Paths

Project contexts now build target environments with `include_sys_path=False`.
Project resolution searches configured source roots, explicit external roots,
and interpreter stdlib roots, but it does not append the process's ambient
`sys.path`.

This keeps local project packages and namespace portions source-root bounded.
For example, a local namespace package named `tests` is still resolved from the
project when an unrelated regular `tests` package exists on ambient `sys.path`.

Project analyzers also no longer call `register_search_path`, so constructing
or running an analyzer does not mutate the interpreter search path. The
`register_search_path` helper remains only for explicit runtime-compatible
workflows.

## Partially Implemented

### Resolution Modes Are Not Fully Reflected In Results

`ResolutionMode.RUNTIME` and `ResolutionMode.ENVIRONMENT` exist, but runtime
lookup currently calls `resolve_project_name`, so resulting `ModuleResolution`
objects still report `mode=PROJECT`.

The service needs explicit methods or parameters for runtime/environment
resolution if mode is meant to be a reliable fact.

### Ambiguity Is Modeled But Not Used

`ResolutionStatus.AMBIGUOUS` exists, but no resolver path creates ambiguous
results yet.

`from package import name` is still resolved by trying a submodule candidate and
then falling back to the containing package. The policy calls for preserving the
ambiguity between:

- `name` as a submodule;
- `name` as an exported object;
- `name` as unavailable.

This is not represented yet.

### Resolution Reasons Are Mostly Strings

Unavailable resolution results preserve a `reason`, but reasons are plain
strings. The policy asks for explainable failures such as missing module,
relative import escape, non-Python origin, namespace without scan-eligible
portion, and ambiguous object-vs-submodule.

Typed reason codes or structured diagnostics are still missing.

### Module Models Still Own Compatibility Categorization

Project resolution uses `ModuleClassifier`, but `Module.get_category(...)` and
`CategorizedModule.infer_category(...)` still exist for compatibility paths.

This keeps some category policy in the specification model layer, contrary to
the policy direction. It is less dangerous now because project analyzers use the
central resolver, but it remains an architectural inconsistency.

## Open Or Not Implemented

### Explicit External Roots

`TargetEnvironment` supports `external_roots`, but project context, CLI, and
analyzer constructors do not expose them. External resolution currently requires
manual construction of a target environment or the runtime compatibility path.

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

1. **Structured Resolution Diagnostics**
   Replace string-only unavailable reasons with typed reason codes and add first
   use of `ResolutionStatus.AMBIGUOUS` for `from package import name`.

2. **Expose Explicit External Roots**
   Add project context, analyzer, and CLI configuration for dependency roots
   without falling back to ambient `sys.path`.

3. **Remove Remaining Category Policy From Module Models**
   Migrate `Module.get_category` and `CategorizedModule.infer_category` callers
   to resolver/classifier paths, then remove those compatibility methods.

4. **Source Context For Scope And Calls**
   Start a new phase that attaches parsed AST modules to `SourceModuleContext`
   and prepares lexical symbol FQNs.
