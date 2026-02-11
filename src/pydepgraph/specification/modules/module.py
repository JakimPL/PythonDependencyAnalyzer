from __future__ import annotations

import sys
from importlib.machinery import ModuleSpec
from importlib.util import find_spec
from pathlib import Path
from typing import Optional, Self, Tuple

from pydantic import Field, model_validator

from pydepgraph.constants import DELIMITER
from pydepgraph.exceptions import PDGInvalidOriginTypeError, PDGMissingModuleNameError, PDGPathResolutionError
from pydepgraph.specification.base import Specification
from pydepgraph.specification.modules.category import ModuleCategory
from pydepgraph.specification.modules.origin import OriginType
from pydepgraph.specification.modules.spec import validate_spec
from pydepgraph.tools.utils import resolve_path


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
    submodule_search_locations: Tuple[Path, ...] = Field(
        default_factory=tuple,
        description="List of directories to search for submodules. Only for packages.",
    )

    @model_validator(mode="after")
    def validate_module(self) -> Self:
        if not self.name:
            raise PDGMissingModuleNameError("Module name cannot be empty")

        if self.package is not None and not self.package:
            raise PDGMissingModuleNameError("Package name cannot be empty if provided")

        if self.origin is not None:
            validate_spec(self.spec, validate_origin=True, expect_python=self.origin_type == OriginType.PYTHON)

        elif self.origin_type == OriginType.PYTHON:
            raise PDGInvalidOriginTypeError(f"Module '{self.name}' has file origin type but no origin path")

        self.top_level_module
        self.is_package
        self.base_path
        self.spec
        return self

    @property
    def top_level_module(self) -> str:
        top_level = self.package or self.name
        return top_level.split(DELIMITER)[0]

    @property
    def is_top_level(self) -> bool:
        return self.name == self.top_level_module

    @property
    def is_package(self) -> bool:
        return bool(self.submodule_search_locations)

    @property
    def base_path(self) -> Path:
        spec = find_spec(self.top_level_module)
        if spec and spec.origin:
            if spec.submodule_search_locations:
                return resolve_path(spec.submodule_search_locations[0]).parent

            return resolve_path(spec.origin).parent

        raise PDGPathResolutionError(
            f"Cannot determine base path for module '{self.name}' with top-level '{self.top_level_module}'"
        )

    @classmethod
    def from_spec(
        cls,
        spec: ModuleSpec,
        package: Optional[str] = None,
    ) -> Module:
        """
        Create a Module instance from a ModuleSpec and category.
        """
        if not spec.origin:
            raise ValueError(f"Module '{spec.name}' has no origin path")

        origin_type = OriginType.from_spec(spec)
        origin = resolve_path(spec.origin)
        submodule_search_locations = tuple(resolve_path(location) for location in spec.submodule_search_locations or [])

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
        spec = find_spec(self.name, package=self.package)
        return validate_spec(spec, expect_python=False)

    def get_category(self, base_path: Optional[Path] = None) -> ModuleCategory:
        """
        Determine module category based on its origin path and top-level module name.
        If base_path is provided, modules with origins under that path
        are categorized as INTERNAL.

        Standard library modules are categorized as STDLIB, and all others
        are categorized as EXTERNAL.
        """
        if base_path and self.origin is not None and base_path in self.origin.parents:
            return ModuleCategory.INTERNAL

        if self.top_level_module in sys.stdlib_module_names:
            return ModuleCategory.STDLIB

        return ModuleCategory.EXTERNAL
