from __future__ import annotations

from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any, NamedTuple, Optional, Tuple, Union

from pda.exceptions.spec import PDAModuleSpecError
from pda.specification.imports.origin import OriginType
from pda.specification.modules.module.category import ModuleCategory
from pda.specification.modules.module.module import Module
from pda.specification.modules.module.type import ModuleType
from pda.specification.modules.module.unavailable import UnavailableModule
from pda.tools.paths import is_file, resolve_path
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

    def prefix(self, level: int) -> str:
        return self.module.prefix(level)

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

    @property
    def available(self) -> bool:
        if isinstance(self.module, UnavailableModule):
            return False

        if self.origin_type == OriginType.PYTHON:
            return self.origin is not None and is_file(self.origin)

        return True

    @property
    def availability_reason(self) -> Optional[str]:
        if isinstance(self.module, UnavailableModule):
            return str(self.module.error) if self.module.error else "module not found"

        if not self.available:
            return "source not available for analysis"

        return None

    @staticmethod
    def from_spec(
        spec: ModuleSpec,
        *,
        category: Optional[ModuleCategory] = None,
        project_root: Optional[Pathlike] = None,
    ) -> CategorizedModule:
        module: Union[Module, UnavailableModule]
        try:
            module = Module.from_spec(spec)
        except PDAModuleSpecError as error:
            module = UnavailableModule(name=spec.name, error=error)
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
    def infer_category(
        module: Union[Module, UnavailableModule],
        *,
        category: Optional[ModuleCategory] = None,
        project_root: Optional[Pathlike] = None,
    ) -> ModuleCategory:
        if isinstance(module, UnavailableModule):
            return ModuleCategory.UNKNOWN

        if category is None:
            base_path = resolve_path(project_root)
            return module.get_category(base_path)

        return category
