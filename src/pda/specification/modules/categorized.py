from __future__ import annotations

from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any, NamedTuple, Optional, Tuple

from pda.config import ValidationOptions
from pda.specification.imports.origin import OriginType
from pda.specification.modules.category import ModuleCategory
from pda.specification.modules.module import Module
from pda.specification.modules.spec import find_module_spec
from pda.specification.modules.type import ModuleType
from pda.tools.logger import logger
from pda.tools.paths import resolve_path
from pda.types import Pathlike


class CategorizedModule(NamedTuple):
    module: Module
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
    def spec(self) -> ModuleSpec:
        return self.module.spec

    @property
    def origin(self) -> Optional[Path]:
        return self.module.origin

    @property
    def origin_type(self) -> OriginType:
        return self.module.origin_type

    @property
    def submodule_search_locations(self) -> Optional[Tuple[Path, ...]]:
        return self.module.submodule_search_locations

    @property
    def base_path(self) -> Path:
        return self.module.base_path

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
    def is_module(self) -> bool:
        return self.module.is_module

    @property
    def is_package(self) -> bool:
        return self.module.is_package

    @property
    def is_namespace_package(self) -> bool:
        return self.module.is_namespace_package

    @property
    def type(self) -> ModuleType:
        return self.module.type

    @staticmethod
    def from_spec(
        spec: ModuleSpec,
        *,
        category: Optional[ModuleCategory] = None,
        project_root: Optional[Pathlike] = None,
        package: Optional[str] = None,
    ) -> CategorizedModule:
        module = Module.from_spec(spec, package=package)
        return CategorizedModule.from_module(
            module,
            category=category,
            project_root=project_root,
        )

    @staticmethod
    def from_module(
        module: Module,
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
    ) -> Optional[CategorizedModule]:
        options: ValidationOptions = validation_options or ValidationOptions.strict()
        spec = find_module_spec(name, package=package, **options.model_dump())
        if not spec:
            logger.debug("Module '%s' not found", name)
            return None

        origin_type = OriginType.from_spec(spec)
        if options.expect_python and origin_type not in (
            OriginType.NONE,
            OriginType.PYTHON,
        ):
            logger.debug("Skipping non-Python module: %s of origin %s", name, origin_type)
            return None

        return CategorizedModule.from_spec(
            spec,
            project_root=project_root,
            package=package,
        )

    @staticmethod
    def infer_category(
        module: Module,
        *,
        category: Optional[ModuleCategory] = None,
        project_root: Optional[Pathlike] = None,
    ) -> ModuleCategory:
        if category is None:
            base_path = resolve_path(project_root)
            return module.get_category(base_path)

        return category
