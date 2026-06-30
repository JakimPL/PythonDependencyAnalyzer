from __future__ import annotations

from importlib.util import resolve_name
from pathlib import Path
from typing import Optional

from pda.constants import DELIMITER
from pda.resolution.classification import ModuleClassifier
from pda.resolution.conversion import CategorizedModuleBuilder
from pda.resolution.filesystem import FilesystemModuleLocator
from pda.resolution.imports import ImportPathCandidateBuilder
from pda.resolution.locations import ModuleLocationFactory
from pda.resolution.models.environment import TargetEnvironment
from pda.resolution.models.location import ModuleCoordinates
from pda.resolution.models.resolution import (
    ModuleResolution,
    ResolutionAlternative,
    ResolutionAlternativeKind,
    ResolutionMode,
    ResolutionStatus,
)
from pda.resolution.models.source import SourceModuleContext
from pda.resolution.search.paths import TargetSearchPath
from pda.resolution.search.specs import ModuleSpecResolver
from pda.specification import (
    CategorizedModule,
    ImportPath,
    ModuleKind,
    ResolutionDiagnostic,
    ResolutionDiagnosticCode,
)
from pda.types import Pathlike


class ModuleResolutionService:
    def __init__(self, environment: TargetEnvironment) -> None:
        self._environment = environment
        self._classifier = ModuleClassifier(environment)
        self._filesystem = FilesystemModuleLocator(environment)
        self._import_candidates = ImportPathCandidateBuilder()
        self._locations = ModuleLocationFactory(self._classifier)
        self._specs = ModuleSpecResolver(TargetSearchPath(environment))
        self._modules = CategorizedModuleBuilder()

    @property
    def environment(self) -> TargetEnvironment:
        return self._environment

    def resolve_name(
        self,
        name: str,
        *,
        containing_package: Optional[str] = None,
    ) -> ModuleResolution:
        fullname = self._resolve_name(name, containing_package)
        spec = self._specs.find(fullname)
        if spec is None:
            return self._unavailable(
                requested=name,
                mode=self._environment.mode,
                diagnostic=ResolutionDiagnostic.create(
                    ResolutionDiagnosticCode.MODULE_SPEC_NOT_FOUND,
                    f"Module spec for '{fullname}' not found",
                    fullname=fullname,
                ),
            )

        return self._resolved(
            self._locations.from_spec(spec),
            requested=name,
            mode=self._environment.mode,
        )

    def resolve_import_path(
        self,
        context: SourceModuleContext,
        import_path: ImportPath,
    ) -> ModuleResolution:
        if self._is_named_from_import(import_path):
            from_import_resolution = self._resolve_named_from_import(context, import_path)
            if from_import_resolution is not None:
                return from_import_resolution

        candidates = self._import_candidates.candidates(context, import_path)
        if not candidates:
            return self._unavailable(
                requested=str(import_path),
                mode=self._environment.mode,
                diagnostic=self._import_path_diagnostic(context, import_path),
            )

        unresolved: Optional[ModuleResolution] = None
        for module_name in candidates:
            resolution = self.resolve_name(module_name)
            if resolution.resolved:
                return resolution

            unresolved = resolution

        return unresolved or self._unavailable(
            requested=str(import_path),
            mode=self._environment.mode,
            diagnostic=ResolutionDiagnostic.create(
                ResolutionDiagnosticCode.IMPORT_PATH_UNRESOLVED,
                f"Import path '{import_path}' does not resolve to an available module",
                import_path=str(import_path),
            ),
        )

    def _is_named_from_import(self, import_path: ImportPath) -> bool:
        return import_path.name is not None and import_path.name != "*"

    def _resolve_named_from_import(
        self,
        context: SourceModuleContext,
        import_path: ImportPath,
    ) -> Optional[ModuleResolution]:
        base_name = self._import_candidates.base_name(context, import_path)
        if import_path.relative and base_name is None:
            return self._unavailable(
                requested=str(import_path),
                mode=self._environment.mode,
                diagnostic=self._import_path_diagnostic(context, import_path),
            )

        if not base_name or not import_path.name:
            return None

        submodule_name = f"{base_name}{DELIMITER}{import_path.name}"
        submodule_resolution = self.resolve_name(submodule_name)
        exported_object_resolution = self.resolve_name(base_name)

        if exported_object_resolution.resolved and exported_object_resolution.kind == ModuleKind.NAMESPACE_PACKAGE:
            return submodule_resolution

        if exported_object_resolution.resolved:
            return self._ambiguous_from_import(
                requested=str(import_path),
                import_path=import_path,
                submodule_name=submodule_name,
                exported_from=base_name,
                submodule_resolution=submodule_resolution,
                exported_object_resolution=exported_object_resolution,
            )

        if submodule_resolution.resolved:
            return submodule_resolution

        return exported_object_resolution

    def resolve_filesystem_path(
        self,
        path: Pathlike,
        *,
        source_root: Optional[Pathlike] = None,
    ) -> ModuleResolution:
        lookup = self._filesystem.locate(path, source_root=source_root)
        if not lookup.resolved or lookup.coordinates is None:
            return self._unavailable(
                requested=str(lookup.requested),
                mode=ResolutionMode.FILESYSTEM,
                diagnostic=lookup.diagnostic
                or ResolutionDiagnostic.create(
                    ResolutionDiagnosticCode.PATH_UNRESOLVED,
                    f"Path '{lookup.requested}' was not resolved",
                    path=str(lookup.requested),
                ),
            )

        return self._resolved(
            lookup.coordinates,
            requested=str(lookup.requested),
            mode=ResolutionMode.FILESYSTEM,
        )

    def source_context(
        self,
        path: Pathlike,
        *,
        source_root: Optional[Pathlike] = None,
    ) -> Optional[SourceModuleContext]:
        resolution = self.resolve_filesystem_path(path, source_root=source_root)
        if not resolution.resolved or resolution.identity is None or resolution.location is None:
            return None

        root = resolution.location.matched_root
        if root is None:
            root = Path(source_root).resolve() if source_root is not None else self.environment.source_roots[0]

        if self.environment.local_boundary is None:
            return None

        return SourceModuleContext(
            identity=resolution.identity,
            location=resolution.location,
            source_root=root,
            local_boundary=self.environment.local_boundary,
            environment=self.environment,
        )

    def to_categorized_module(
        self,
        resolution: ModuleResolution,
    ) -> CategorizedModule:
        return self._modules.from_resolution(resolution)

    def _resolve_name(self, name: str, containing_package: Optional[str]) -> str:
        if name.startswith(DELIMITER):
            return resolve_name(name, containing_package)

        return name

    def _resolved(
        self,
        coordinates: ModuleCoordinates,
        *,
        requested: str,
        mode: ResolutionMode,
    ) -> ModuleResolution:
        return ModuleResolution(
            requested=requested,
            mode=mode,
            status=ResolutionStatus.RESOLVED,
            identity=coordinates.identity,
            location=coordinates.location,
            kind=self._classifier.kind(coordinates.location),
            category=self._classifier.category(coordinates.identity, coordinates.location),
        )

    def _unavailable(
        self,
        *,
        requested: str,
        mode: ResolutionMode,
        diagnostic: ResolutionDiagnostic,
    ) -> ModuleResolution:
        return ModuleResolution(
            requested=requested,
            mode=mode,
            status=ResolutionStatus.UNAVAILABLE,
            diagnostic=diagnostic,
        )

    def _ambiguous_from_import(
        self,
        *,
        requested: str,
        import_path: ImportPath,
        submodule_name: str,
        exported_from: str,
        submodule_resolution: ModuleResolution,
        exported_object_resolution: ModuleResolution,
    ) -> ModuleResolution:
        return ModuleResolution(
            requested=requested,
            mode=self._environment.mode,
            status=ResolutionStatus.AMBIGUOUS,
            diagnostic=ResolutionDiagnostic.create(
                ResolutionDiagnosticCode.AMBIGUOUS_FROM_IMPORT,
                (
                    f"Import path '{import_path}' is ambiguous between submodule "
                    f"'{submodule_name}' and an object exported by '{exported_from}'"
                ),
                import_path=str(import_path),
                submodule=submodule_name,
                exported_from=exported_from,
            ),
            alternatives=(
                ResolutionAlternative(
                    kind=ResolutionAlternativeKind.SUBMODULE,
                    resolution=submodule_resolution,
                ),
                ResolutionAlternative(
                    kind=ResolutionAlternativeKind.EXPORTED_OBJECT,
                    resolution=exported_object_resolution,
                ),
            ),
        )

    def _import_path_diagnostic(
        self,
        context: SourceModuleContext,
        import_path: ImportPath,
    ) -> ResolutionDiagnostic:
        if import_path.relative:
            containing_package = context.containing_package
            if containing_package is None:
                message = f"Relative import path '{import_path}' has no containing package"
            else:
                message = f"Relative import path '{import_path}' escapes package '{containing_package}'"

            return ResolutionDiagnostic.create(
                ResolutionDiagnosticCode.RELATIVE_IMPORT_ESCAPES_PACKAGE,
                message,
                import_path=str(import_path),
                containing_package=containing_package or "",
            )

        return ResolutionDiagnostic.create(
            ResolutionDiagnosticCode.IMPORT_PATH_EMPTY,
            f"Import path '{import_path}' does not specify a module",
            import_path=str(import_path),
        )
