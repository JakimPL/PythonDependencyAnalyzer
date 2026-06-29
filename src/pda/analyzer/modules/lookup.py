from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from pda.resolution import ModuleResolutionService, ProjectResolutionContext, TargetEnvironment
from pda.specification import CategorizedModule, Module, ModuleCategory
from pda.types import Pathlike


class ModuleLookup(Protocol):
    def filesystem_module(
        self,
        origin: Pathlike,
    ) -> CategorizedModule: ...

    def discovered_module(
        self,
        name: str,
        *,
        containing_package: Optional[str],
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
    ) -> CategorizedModule:
        resolution = self.resolver.resolve_filesystem_path(origin)
        return self.resolver.to_categorized_module(resolution)

    def discovered_module(
        self,
        name: str,
        *,
        containing_package: Optional[str],
    ) -> CategorizedModule:
        resolution = self.resolver.resolve_project_name(name, containing_package=containing_package)
        return self.resolver.to_categorized_module(resolution)

    def category(self, module: Module) -> ModuleCategory:
        return module.get_category(self.context.local_boundary)


@dataclass(frozen=True)
class RuntimeModuleLookup:
    resolver: ModuleResolutionService

    @classmethod
    def create(cls) -> RuntimeModuleLookup:
        return cls(resolver=ModuleResolutionService(TargetEnvironment.runtime()))

    def filesystem_module(
        self,
        origin: Pathlike,
    ) -> CategorizedModule:
        raise RuntimeError("Runtime module collection does not resolve local filesystem modules")

    def discovered_module(
        self,
        name: str,
        *,
        containing_package: Optional[str],
    ) -> CategorizedModule:
        resolution = self.resolver.resolve_project_name(name, containing_package=containing_package)
        return self.resolver.to_categorized_module(resolution)

    def category(self, module: Module) -> ModuleCategory:
        return module.get_category(None)
