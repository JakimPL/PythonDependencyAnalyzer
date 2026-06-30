from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pda.constants import DELIMITER
from pda.resolution import ModuleResolution, ModuleResolutionService, ProjectResolutionContext
from pda.resolution.models.location import ModuleLocation
from pda.resolution.paths import longest_containing_root


@dataclass(frozen=True)
class AnalysisTarget:
    """The import root the user asked an analyzer to examine."""

    root_module_name: str

    def __post_init__(self) -> None:
        if not self.root_module_name:
            raise ValueError("Root module name must be provided")

        if self.root_module_name.startswith(DELIMITER):
            raise ValueError("Root module name must be absolute")

        if any(not part for part in self.root_module_name.split(DELIMITER)):
            raise ValueError(f"Invalid root module name: '{self.root_module_name}'")


@dataclass(frozen=True)
class ResolvedAnalysisTarget:
    target: AnalysisTarget
    resolution: ModuleResolution
    local_entry_paths: tuple[Path, ...]


class AnalysisTargetResolver:
    def __init__(self, project_context: ProjectResolutionContext) -> None:
        self._project_context = project_context
        self._resolution = ModuleResolutionService(project_context.environment)

    def resolve(self, target: AnalysisTarget) -> ResolvedAnalysisTarget:
        resolution = self._resolution.resolve_name(target.root_module_name)
        if not resolution.resolved or resolution.location is None:
            raise ValueError(f"Analysis target '{target.root_module_name}' was not resolved")

        local_entry_paths = self._local_entry_paths(resolution.location)
        if not local_entry_paths:
            raise ValueError(f"Analysis target '{target.root_module_name}' was not found under configured source roots")

        return ResolvedAnalysisTarget(
            target=target,
            resolution=resolution,
            local_entry_paths=local_entry_paths,
        )

    def _local_entry_paths(self, location: ModuleLocation) -> tuple[Path, ...]:
        if location.submodule_search_locations:
            return tuple(
                path for path in location.submodule_search_locations if self._is_under_configured_source_root(path)
            )

        if location.origin is not None and self._is_under_configured_source_root(location.origin):
            return (location.origin,)

        return ()

    def _is_under_configured_source_root(self, path: Path) -> bool:
        return longest_containing_root(path, self._project_context.source_roots) is not None
