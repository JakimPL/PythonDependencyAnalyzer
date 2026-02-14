from __future__ import annotations

import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any, Dict, Optional, Self, Tuple

from pydantic import Field, model_validator

from pda.constants import DELIMITER
from pda.exceptions import PDAInvalidOriginTypeError, PDAMissingModuleNameError, PDAPathResolutionError
from pda.specification.base import Specification
from pda.specification.imports.origin import OriginType
from pda.specification.imports.path import ImportPath
from pda.specification.modules.category import ModuleCategory
from pda.specification.modules.spec import find_module_spec, validate_spec
from pda.specification.modules.type import ModuleType
from pda.tools.paths import resolve_path


class Module(Specification):
    """
    Module specification containing metadata about a Python module, including
    its fully qualified name, file path, category, and submodule directories.
    """

    name: str = Field(description="Fully qualified module name, e.g. 'package.module'")
    package: Optional[str] = Field(default=None, description="Corresponding package name, e.g. 'package'")
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

    @model_validator(mode="after")
    def validate_module(self) -> Self:
        if not self.name:
            raise PDAMissingModuleNameError("Module name cannot be empty")

        if self.package is not None and not self.package:
            raise PDAMissingModuleNameError("Package name cannot be empty if provided")

        if self.origin is not None:
            validate_spec(self.spec, validate_origin=False, expect_python=self.origin_type == OriginType.PYTHON)

        elif self.origin_type == OriginType.PYTHON:
            raise PDAInvalidOriginTypeError(f"Module '{self.name}' has file origin type but no origin path")

        _ = self.base_path
        _ = self.spec
        return self

    @property
    def parts(self) -> Tuple[str, ...]:
        return tuple(self.name.split(DELIMITER))

    @property
    def top_level_module(self) -> str:
        top_level = self.package or self.name
        return top_level.split(DELIMITER)[0]

    @property
    def is_top_level(self) -> bool:
        return self.name == self.top_level_module

    @property
    def is_private(self) -> bool:
        return self.parts[0].startswith("_")

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
    def import_path(self) -> ImportPath:
        return ImportPath.from_string(self.name)

    @property
    def path(self) -> Optional[Path]:
        if self.origin is not None:
            return self.origin

        if self.submodule_search_locations:
            return self.submodule_search_locations[0]

        return None

    @property
    def base_path(self) -> Path:
        spec = find_module_spec(
            self.top_level_module,
            validate_origin=False,
            expect_python=False,
        )

        path: Optional[Path] = None
        if spec and spec.origin:
            if spec.submodule_search_locations:
                path = resolve_path(spec.submodule_search_locations[0])
            else:
                path = resolve_path(spec.origin)

        if path is None:
            raise PDAPathResolutionError(
                f"Cannot determine base path for module '{self.name}' with top-level '{self.top_level_module}'"
            )

        return path.parent

    @staticmethod
    def retrieve_submodule_search_locations(spec: ModuleSpec) -> Tuple[Path, ...]:
        locations = spec.submodule_search_locations or []
        return tuple(path for location in locations if (path := resolve_path(location)) is not None)

    @classmethod
    def from_spec(
        cls,
        spec: ModuleSpec,
        package: Optional[str] = None,
    ) -> Module:
        """
        Create a Module instance from a ModuleSpec and category.
        """
        origin_type = OriginType.from_spec(spec)
        origin = resolve_path(spec.origin)
        submodule_search_locations = cls.retrieve_submodule_search_locations(spec)

        return cls(
            name=spec.name,
            package=package,
            origin=origin,
            origin_type=origin_type,
            submodule_search_locations=submodule_search_locations,
        )

    @property
    def spec(self) -> ModuleSpec:
        """
        Convert the Module instance back to a ModuleSpec for compatibility with importlib.
        """
        return find_module_spec(
            self.name,
            package=self.package,
            allow_missing_spec=False,
            raise_error=True,
            validate_origin=False,
            expect_python=False,
        )

    def get_category(self, base_path: Optional[Path] = None) -> ModuleCategory:
        """
        Determine module category based on its origin path and top-level module name.
        If base_path is provided, modules with origins under that path
        are categorized as LOCAL.

        Standard library modules are categorized as STDLIB, and all others
        are categorized as EXTERNAL.
        """
        if base_path is not None:
            parents = self.path.parents if self.path else []
            if base_path in parents:
                return ModuleCategory.LOCAL

        if self.top_level_module in sys.stdlib_module_names:
            return ModuleCategory.STDLIB

        return ModuleCategory.EXTERNAL
