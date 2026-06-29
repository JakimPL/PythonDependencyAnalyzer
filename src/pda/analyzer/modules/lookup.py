from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from pda.analyzer.modules.creator import ModuleCreator
from pda.resolution import ModuleResolutionService, TargetEnvironment
from pda.specification import CategorizedModule
from pda.types import Pathlike


class ModuleLookup(Protocol):
    def filesystem_module(
        self,
        origin: Pathlike,
        *,
        package: Optional[str],
    ) -> CategorizedModule: ...

    def discovered_module(
        self,
        name: str,
        *,
        package: Optional[str],
    ) -> CategorizedModule: ...


@dataclass(frozen=True)
class ProjectModuleLookup:
    source_root: Path
    resolver: ModuleResolutionService

    @classmethod
    def create(cls, source_root: Path) -> ProjectModuleLookup:
        return cls(
            source_root=source_root,
            resolver=ModuleResolutionService(
                TargetEnvironment.create(
                    (source_root,),
                )
            ),
        )

    def filesystem_module(
        self,
        origin: Pathlike,
        *,
        package: Optional[str],
    ) -> CategorizedModule:
        resolution = self.resolver.resolve_filesystem_path(
            origin,
            source_root=self.source_root,
        )
        return self.resolver.to_categorized_module(
            resolution,
            package=package,
        )

    def discovered_module(
        self,
        name: str,
        *,
        package: Optional[str],
    ) -> CategorizedModule:
        resolution = self.resolver.resolve_project_name(name, package=package)
        return self.resolver.to_categorized_module(resolution, package=package)


@dataclass(frozen=True)
class RuntimeModuleLookup:
    creator: ModuleCreator

    @classmethod
    def create(cls) -> RuntimeModuleLookup:
        return cls(creator=ModuleCreator())

    def filesystem_module(
        self,
        origin: Pathlike,
        *,
        package: Optional[str],
    ) -> CategorizedModule:
        raise RuntimeError("Runtime module collection does not resolve local filesystem modules")

    def discovered_module(
        self,
        name: str,
        *,
        package: Optional[str],
    ) -> CategorizedModule:
        return self.creator.create_module(name, package=package)
