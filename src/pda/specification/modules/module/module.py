from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional, Self, Tuple

from pydantic import Field, model_validator

from pda.exceptions import PDAInvalidModuleOriginError, PDAMissingModuleNameError
from pda.specification.imports.origin import OriginType
from pda.specification.modules.module.base import BaseModule
from pda.specification.modules.module.category import ModuleCategory
from pda.specification.modules.module.namespace import NamespacePortion
from pda.specification.modules.module.type import ModuleType
from pda.tools.paths import is_python_file


class Module(BaseModule):
    """
    Module specification containing metadata about a Python module, including
    its fully qualified name, file path, category, and submodule directories.
    """

    origin: Optional[Path] = Field(default=None, description="Absolute file path to the module")
    origin_type: OriginType = Field(
        default=OriginType.PYTHON,
        description="Type of the origin, e.g. file, frozen, or built-in",
    )
    submodule_search_locations: Optional[Tuple[Path, ...]] = Field(
        default=None,
        description="Tuple of directories to search for submodules. Only for packages.",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata about the module",
    )
    namespace_portions: Tuple[NamespacePortion, ...] = Field(
        default=(),
        description="Namespace package portions with their root and category facts.",
    )

    @model_validator(mode="after")
    def validate_module(self) -> Self:
        if not self.name:
            raise PDAMissingModuleNameError("Module name cannot be empty")

        if self.origin_type == OriginType.PYTHON:
            if self.origin is None:
                raise PDAInvalidModuleOriginError(f"Module '{self.name}' has file origin type but no origin path")

            if not is_python_file(self.origin):
                raise PDAInvalidModuleOriginError(f"Module '{self.name}' has non-Python origin file: '{self.origin}'")

        return self

    @property
    def is_module(self) -> bool:
        return not self.is_package

    @property
    def is_package(self) -> bool:
        return self.submodule_search_locations is not None

    @property
    def is_namespace_package(self) -> bool:
        return self.is_package and self.origin is None

    @property
    def type(self) -> ModuleType:
        match (self.is_package, self.is_namespace_package):
            case (True, False):
                return ModuleType.PACKAGE
            case (True, True):
                return ModuleType.NAMESPACE_PACKAGE
            case (False, _):
                return ModuleType.MODULE
            case _:
                raise ValueError(f"Invalid module type for module '{self.name}'")

    @property
    def path(self) -> Optional[Path]:
        if self.origin is not None:
            return self.origin

        if self.submodule_search_locations:
            return self.submodule_search_locations[0]

        return None

    @property
    def base_path(self) -> Optional[Path]:
        base_location = self._base_location
        if base_location is None:
            return None

        return self._base_path_from_location(base_location)

    @property
    def _base_location(self) -> Optional[Path]:
        if self.submodule_search_locations:
            return self.submodule_search_locations[0]

        if self.origin is None:
            return None

        if self.origin_type not in {OriginType.PYTHON, OriginType.NO_PYTHON}:
            return None

        return self.origin.with_suffix("") if self.origin.suffix else self.origin

    def _base_path_from_location(self, path: Path) -> Optional[Path]:
        index = len(self.parts) - 1
        if index >= len(path.parents):
            return None

        return path.parents[index]

    def get_category(self, base_path: Optional[Path] = None) -> ModuleCategory:
        """
        Determine module category based on its origin path and top-level module name.
        If base_path is provided, modules with origins under that path
        are categorized as LOCAL.

        Standard library modules are categorized as STDLIB, and all others
        are categorized as EXTERNAL.
        """
        if base_path is not None:
            path = self.path
            parents = path.parents if path else []
            if path == base_path or base_path in parents:
                return ModuleCategory.LOCAL

        if self.top_level_module in sys.stdlib_module_names:
            return ModuleCategory.STDLIB

        return ModuleCategory.EXTERNAL
