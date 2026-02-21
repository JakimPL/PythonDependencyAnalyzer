from functools import cached_property
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Optional, Self

from pydantic import Field, model_validator

from pda.config import ValidationOptions
from pda.constants import DELIMITER
from pda.exceptions import (
    PDAMissingModuleNameError,
    PDAMissingModuleSpecError,
    PDAMissingTopLevelModuleError,
    PDASourceFileOutsideProjectError,
)
from pda.parser import validate_python_file
from pda.specification.base import Specification
from pda.specification.imports.path import ImportPath
from pda.specification.modules.module import Module
from pda.specification.modules.spec.spec import find_module_spec
from pda.tools.paths import is_dir


class ModuleSource(Specification):
    """
    A wrapper for a module path within a project.

    Allows to provide fully qualified module names based on file paths,
    base path, and Python module naming conventions.

    Assumes that the project follows standard Python packaging structure,
    here the top-level project directory contains a package directory,
    and modules are organized in subdirectories with __init__.py files.
    """

    origin: Path = Field(description="Absolute file path to the module")
    base_path: Path = Field(description="Absolute path to the top-level project directory")
    package: str = Field(description="Package name corresponding to the base path")
    validation_options: ValidationOptions = Field(
        default_factory=ValidationOptions.strict,
        description="Options for validating the module source",
    )

    @model_validator(mode="after")
    def validate_paths(self) -> Self:
        validate_python_file(self.origin)

        if not is_dir(self.base_path):
            raise NotADirectoryError(f"Base path '{self.base_path}' is not a valid directory")

        if DELIMITER in self.top_level:
            raise ValueError(f"Top-level module name cannot contain delimiters '{DELIMITER}'")

        _ = self.relative
        _ = self.top_level
        _ = self.module
        return self

    @cached_property
    def relative(self) -> ImportPath:
        relative = ImportPath.from_path(self.origin, self.base_path)
        if relative is None:
            raise PDASourceFileOutsideProjectError(f"File '{self.origin}' is outside the project: '{self.base_path}'")

        return relative

    @cached_property
    def top_level(self) -> str:
        module = self.relative.module
        if not module:
            raise PDAMissingTopLevelModuleError(
                f"Cannot determine top-level module name for '{self.origin}' relative to '{self.base_path}'"
            )

        return module.split(DELIMITER)[0]

    @property
    def module(self) -> Module:
        spec = self.get_spec(self.relative)
        if not spec:
            raise PDAMissingModuleSpecError(f"Module spec not found for '{self.origin}' relative to '{self.base_path}'")

        return Module.from_spec(spec, package=self.package)

    def get_package_spec(
        self,
        path: ImportPath,
    ) -> Optional[ModuleSpec]:
        """
        Resolve the package containing the module specified by the import path.
        Returns the ModuleSpec of the package if found, or None if the package cannot be resolved.
        """
        spec: Optional[ModuleSpec] = self.get_spec(path)
        if spec is None:
            return None

        if bool(spec.submodule_search_locations):
            return spec

        is_package = False
        while not is_package:
            path = path.get_parent()
            if not path.module:
                return None

            spec = self.get_spec(path)
            if spec is None:
                return None

            is_package = bool(spec.submodule_search_locations)

        return spec

    def get_spec(
        self,
        path: Optional[ImportPath] = None,
    ) -> Optional[ModuleSpec]:
        """
        Resolve the import path to a ModuleSpec.
        """
        if not path:
            return None

        path = path.get_module_path()
        module_name: Optional[str] = None
        if path.level > 0:
            parent = self.relative.get_parent(path.level)
            module_name = (parent / path.module).path
        else:
            module_name = path.module

        if module_name is None:
            raise PDAMissingModuleNameError(f"Import path '{path}' does not specify a module name")

        spec: Optional[ModuleSpec] = find_module_spec(
            module_name,
            self.package,
            **self.validation_options.model_dump(),
        )

        return spec
