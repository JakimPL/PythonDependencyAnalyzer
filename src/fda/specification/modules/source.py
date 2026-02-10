from functools import cached_property
from importlib.machinery import ModuleSpec
from importlib.util import find_spec
from pathlib import Path
from typing import Optional, Self

from pydantic import Field, model_validator

from fda.constants import DELIMITER
from fda.exceptions import FDAMissingModuleNameError, FDASourceFileOutsideProjectError
from fda.parser import validate_python_file
from fda.specification.base import Specification
from fda.specification.imports.path import ImportPath
from fda.specification.modules.module import Module
from fda.specification.modules.spec import validate_spec


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

    @model_validator(mode="after")
    def validate_paths(self) -> Self:
        validate_python_file(self.origin)

        if not self.base_path.is_dir():
            raise NotADirectoryError(f"Base path '{self.base_path}' is not a valid directory")

        if DELIMITER in self.top_level:
            raise ValueError(f"Top-level module name cannot contain delimiters '{DELIMITER}'")

        self.relative
        self.top_level
        self.module
        return self

    @cached_property
    def relative(self) -> ImportPath:
        relative = ImportPath.from_path(self.origin, self.base_path)
        if relative is None:
            raise FDASourceFileOutsideProjectError(f"File '{self.origin}' is outside the project: '{self.base_path}'")

        return relative

    @cached_property
    def top_level(self) -> str:
        module = self.relative.module
        if not module:
            raise FDAMissingModuleNameError(
                f"Cannot determine top-level module name for '{self.origin}' relative to '{self.base_path}'"
            )

        return module.split(DELIMITER)[0]

    @property
    def module(self) -> Module:
        spec = self.get_spec(self.relative)
        return Module.from_spec(spec, package=self.package)

    def get_package_spec(self, path: ImportPath) -> Optional[ModuleSpec]:
        """
        Resolve the package containing the module specified by the import path.
        Returns the ModuleSpec of the package if found, or None if the package cannot be resolved.

        Raises:
            ImportError: If relative import is attempted without a package or beyond the top-level package.
            ModuleNotFoundError: If the module cannot be found.
            ValueError: If the module has no origin path.
        """
        is_package = False
        spec: ModuleSpec = self.get_spec(path, validate_origin=False)
        if bool(spec.submodule_search_locations):
            return spec

        while not is_package:
            path = path.get_parent()
            if not path.module:
                return None

            spec = self.get_spec(path, validate_origin=False)
            is_package = bool(spec.submodule_search_locations)

        return spec

    def get_spec(
        self,
        path: Optional[ImportPath] = None,
        validate_origin: bool = True,
    ) -> ModuleSpec:
        """
        Resolve the import path to a ModuleSpec.

        If path is not specified, it defaults to the module's
        own relative import path.
        """
        path = path or self.relative
        path = path.get_module_path()
        module_name: Optional[str] = None
        if path.level > 0:
            parent = self.relative.get_parent(path.level)
            module_name = (parent / path.module).path
        else:
            module_name = path.module

        if module_name is None:
            raise FDAMissingModuleNameError(f"Import path '{path}' does not specify a module name")

        file_spec = find_spec(module_name, self.package)
        return validate_spec(file_spec, validate_origin=validate_origin)
