from __future__ import annotations

import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import List, Optional

from pydantic import Field

from fda.specification.base import Specification
from fda.specification.modules.category import ModuleCategory


class Module(Specification):
    """
    Module specification containing metadata about a Python module, including its fully qualified name,
    file path, and category.
    """

    name: str = Field(description="Fully qualified module name, e.g. 'package.module'")
    package: Optional[str] = Field(default=None, description="Corresponding package name, e.g. 'package'")
    origin: Path = Field(description="Absolute file path to the module")
    submodule_search_locations: List[Path] = Field(
        default_factory=list,
        description="List of directories to search for submodules. Only for packages.",
    )

    @property
    def top_level_module(self) -> str:
        return self.package or self.name.split(".")[0]

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

        origin = Path(spec.origin).resolve()
        submodule_search_locations = [Path(location).resolve() for location in spec.submodule_search_locations or []]
        return cls(
            name=spec.name,
            package=package,
            origin=origin,
            submodule_search_locations=submodule_search_locations,
        )

    def get_category(self, project_root: Optional[Path] = None) -> ModuleCategory:
        """
        Determine module category.
        """
        if project_root and project_root in self.origin.parents:
            return ModuleCategory.INTERNAL

        if self.top_level_module in sys.stdlib_module_names:
            return ModuleCategory.STDLIB

        return ModuleCategory.EXTERNAL
