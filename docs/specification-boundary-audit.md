# Specification Boundary Audit

Status: working audit after introducing the specification/helper policy.

## Rule

Specification types are durable PDA facts. They may cross analyzer boundaries,
be stored in graph-facing models, appear in output, or be consumed by later
analysis phases.

Helper types are subsystem machinery. They may represent candidate state,
lookup results, factories, traversal state, parser helpers, or DTOs used only
between collaborators.

## Addressed In This Phase

`NamespacePortion` is now a specification fact because namespace package
portions are durable module facts. They are consumed beyond raw resolution and
must survive conversion into graph-facing `Module` instances.

`ModuleCoordinates` is no longer exported from `pda.resolution` or
`pda.resolution.models`. It remains a resolution-internal DTO in
`pda.resolution.models.location`.

`ModuleKind` is now a specification fact. Module kind (source module, regular
package, namespace package, builtin, frozen, extension, unknown) is a durable
fact stored on `Module` and consumed across the graph boundary. It replaces the
coarser `ModuleType`, which has been removed.

`ResolutionDiagnostic`, `ResolutionDiagnosticCode`, and
`ResolutionDiagnosticDetail` are now specification facts. They explain why a
module is unavailable, are stored on `UnavailableModule`, and appear in
serialized output, so they belong in `pda.specification` rather than in the
resolution layer.

## Correctly Outside Specification

These types are helper or subsystem types and should remain outside
`pda.specification`:

- `ModuleLocation`, `ModuleResolution`, `SourceModuleContext`, and
  `TargetEnvironment` in `pda.resolution.models`;
- `ModuleCoordinates` and `FilesystemModuleLookup`;
- `TargetSearchPath`, `ModuleSpecResolver`, `ModuleLocationFactory`,
  `FilesystemModuleLocator`, `ImportPathCandidateBuilder`,
  `CategorizedModuleBuilder`, and `ModuleClassifier`;
- analyzer traversal helpers such as `PendingNode`, `CategoryContext`, and
  `CategoryDepthPolicy`;
- parser helpers such as `ImportScopeResolver`;
- CLI helpers such as `_Flag`;
- visualization/layout helpers such as `_TreeNode` and `LayoutResult`.

## Remaining Suspect Boundaries

`SysPaths` currently lives under `pda.specification.modules`, but it is a helper
that reads interpreter installation paths and resolves filesystem paths to
`ImportPath`. It is not a durable PDA fact. It should move to a tools,
resolution, or analyzer-support package.

`PKGModuleInfo` currently lives under `pda.specification.modules.spec`, but it
is a `pkgutil` discovery DTO used by `PkgModuleScanner`. It should likely move
near the scanner or into an environment-discovery package.

`ModuleSource` is specification today. This is acceptable while it is a stable
source-file fact used across import analysis, but it should be revisited when
`SourceModuleContext` starts carrying parsed AST and lexical FQN context.

`ModuleIdentity` is currently resolution-local. It may become a specification
fact later if call-graph and symbol analysis need to store module identity as a
first-class graph-facing value rather than only as `Module.name`.
