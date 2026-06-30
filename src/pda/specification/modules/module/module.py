from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Self, Tuple

from pydantic import Field, model_validator

from pda.exceptions import PDAInvalidModuleOriginError, PDAMissingModuleNameError
from pda.specification.imports.origin import OriginType
from pda.specification.modules.module.base import BaseModule
from pda.specification.modules.module.kind import ModuleKind
from pda.specification.modules.module.namespace import NamespacePortion
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
    kind: ModuleKind = Field(description="Resolved module kind classified by the resolution layer.")
    submodule_search_locations: Tuple[Path, ...] = Field(
        default=(),
        description="Directories to search for submodules. Empty for non-packages.",
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
        return self.kind in (ModuleKind.REGULAR_PACKAGE, ModuleKind.NAMESPACE_PACKAGE)

    @property
    def is_namespace_package(self) -> bool:
        return self.kind == ModuleKind.NAMESPACE_PACKAGE

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
