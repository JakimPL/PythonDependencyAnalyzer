from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from pda.analyzer.modules.creator import ModuleCreator
from pda.resolution import ModuleResolutionService, ProjectResolutionContext
from pda.specification import CategorizedModule, Module, ModuleCategory
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

    def category(self, module: Module) -> ModuleCategory: ...


@dataclass(frozen=True)
class ProjectModuleLookup:
    context: ProjectResolutionContext
    resolver: ModuleResolutionService

    @classmethod
    def create(cls, context: ProjectResolutionContext) -> ProjectModuleLookup:
        return cls(
            context=context,
            resolver=ModuleResolutionService(context.environment),
        )

    def filesystem_module(
        self,
        origin: Pathlike,
        *,
        package: Optional[str],
    ) -> CategorizedModule:
        resolution = self.resolver.resolve_filesystem_path(origin)
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

    def category(self, module: Module) -> ModuleCategory:
        return module.get_category(self.context.local_boundary)


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

    def category(self, module: Module) -> ModuleCategory:
        return module.get_category(None)
