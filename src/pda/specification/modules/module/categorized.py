from __future__ import annotations

from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any, NamedTuple, Optional, Tuple, Union

from pda.config import ValidationOptions
from pda.exceptions.spec import PDAModuleSpecError
from pda.specification.imports.origin import OriginType
from pda.specification.modules.module.category import ModuleCategory
from pda.specification.modules.module.module import Module
from pda.specification.modules.module.type import ModuleType
from pda.specification.modules.module.unavailable import UnavailableModule
from pda.specification.modules.spec.spec import find_module_spec
from pda.tools.logger import logger
from pda.tools.paths import resolve_path
from pda.types import Pathlike


class CategorizedModule(NamedTuple):
    module: Union[Module, UnavailableModule]
    category: ModuleCategory

    def __getattr__(self, item: Any) -> Any:
        return getattr(self.module, item)

    @property
    def name(self) -> str:
        return self.module.name

    @property
    def module_name(self) -> str:
        return self.module.module_name

    @property
    def qualified_name(self) -> str:
        return self.module.qualified_name

    @property
    def spec(self) -> Optional[ModuleSpec]:
        return self.module.spec

    @property
    def origin(self) -> Optional[Path]:
        return self.module.origin if isinstance(self.module, Module) else None

    @property
    def origin_type(self) -> OriginType:
        return self.module.origin_type if isinstance(self.module, Module) else OriginType.NONE

    @property
    def submodule_search_locations(self) -> Optional[Tuple[Path, ...]]:
        return self.module.submodule_search_locations if isinstance(self.module, Module) else None

    @property
    def base_path(self) -> Optional[Path]:
        return self.module.base_path if isinstance(self.module, Module) else None

    @property
    def top_level_module(self) -> str:
        return self.module.top_level_module

    @property
    def is_top_level(self) -> bool:
        return self.module.is_top_level

    @property
    def is_private(self) -> bool:
        return self.module.is_private

    @property
    def is_module(self) -> Optional[bool]:
        return self.module.is_module if isinstance(self.module, Module) else None

    @property
    def is_package(self) -> Optional[bool]:
        return self.module.is_package if isinstance(self.module, Module) else None

    @property
    def is_namespace_package(self) -> Optional[bool]:
        return self.module.is_namespace_package if isinstance(self.module, Module) else None

    @property
    def type(self) -> ModuleType:
        return self.module.type if isinstance(self.module, Module) else ModuleType.UNKNOWN

    @staticmethod
    def from_spec(
        spec: ModuleSpec,
        *,
        category: Optional[ModuleCategory] = None,
        project_root: Optional[Pathlike] = None,
        package: Optional[str] = None,
    ) -> CategorizedModule:
        module: Union[Module, UnavailableModule]
        try:
            module = Module.from_spec(spec, package=package)
        except PDAModuleSpecError as error:
            module = UnavailableModule(name=spec.name, package=package, error=error)
        return CategorizedModule.from_module(
            module,
            category=category,
            project_root=project_root,
        )

    @staticmethod
    def from_module(
        module: Union[Module, UnavailableModule],
        *,
        category: Optional[ModuleCategory] = None,
        project_root: Optional[Pathlike] = None,
    ) -> CategorizedModule:
        category = CategorizedModule.infer_category(module, category=category, project_root=project_root)
        return CategorizedModule(module=module, category=category)

    @staticmethod
    def create(
        name: str,
        *,
        project_root: Optional[Pathlike] = None,
        package: Optional[str] = None,
        validation_options: Optional[ValidationOptions] = None,
    ) -> CategorizedModule:
        options: ValidationOptions = validation_options or ValidationOptions.strict()

        spec: Optional[ModuleSpec] = None
        error: Optional[PDAModuleSpecError] = None
        try:
            spec = find_module_spec(name, package=package, **options.model_dump())
        except PDAModuleSpecError as exception:
            error = exception
            if options.raise_error:
                raise exception

        if not spec:
            logger.debug("Module '%s' not found", name)
            module = UnavailableModule(
                name=name,
                package=package,
                error=error,
            )
            return CategorizedModule(
                module=module,
                category=ModuleCategory.UNAVAILABLE,
            )

        return CategorizedModule.from_spec(
            spec,
            project_root=project_root,
            package=package,
        )

    @staticmethod
    def infer_category(
        module: Union[Module, UnavailableModule],
        *,
        category: Optional[ModuleCategory] = None,
        project_root: Optional[Pathlike] = None,
    ) -> ModuleCategory:
        if isinstance(module, UnavailableModule):
            return ModuleCategory.UNAVAILABLE

        if category is None:
            base_path = resolve_path(project_root)
            return module.get_category(base_path)

        return category
