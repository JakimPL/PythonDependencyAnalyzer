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
from pda.resolution.models.resolution import ModuleResolution, ResolutionMode, ResolutionStatus
from pda.resolution.models.source import SourceModuleContext
from pda.resolution.search.paths import TargetSearchPath
from pda.resolution.search.specs import ModuleSpecResolver
from pda.specification import CategorizedModule, ImportPath
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

    def resolve_project_name(
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
                mode=ResolutionMode.PROJECT,
                reason=f"Module spec for '{fullname}' not found",
            )

        return self._resolved(
            self._locations.from_spec(spec),
            requested=name,
            mode=ResolutionMode.PROJECT,
        )

    def resolve_import_path(
        self,
        context: SourceModuleContext,
        import_path: ImportPath,
    ) -> ModuleResolution:
        candidates = self._import_candidates.candidates(context, import_path)
        if not candidates:
            return self._unavailable(
                requested=str(import_path),
                mode=ResolutionMode.PROJECT,
                reason=f"Import path '{import_path}' does not specify a module",
            )

        unresolved: Optional[ModuleResolution] = None
        for module_name in candidates:
            resolution = self.resolve_project_name(module_name)
            if resolution.resolved:
                return resolution

            unresolved = resolution

        return unresolved or self._unavailable(
            requested=str(import_path),
            mode=ResolutionMode.PROJECT,
            reason=f"Import path '{import_path}' does not resolve to an available module",
        )

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
                reason=lookup.reason or f"Path '{lookup.requested}' was not resolved",
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
        reason: str,
    ) -> ModuleResolution:
        return ModuleResolution(
            requested=requested,
            mode=mode,
            status=ResolutionStatus.UNAVAILABLE,
            reason=reason,
        )
