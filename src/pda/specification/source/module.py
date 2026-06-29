from functools import cached_property
from pathlib import Path
from typing import Self

from pydantic import Field, model_validator

from pda.constants import DELIMITER
from pda.exceptions import (
    PDAMissingTopLevelModuleError,
    PDASourceFileOutsideProjectError,
)
from pda.parser import validate_python_file
from pda.specification.base import Specification
from pda.specification.imports.path import ImportPath
from pda.tools.paths import is_dir


class ModuleSource(Specification):
    """
    A wrapper for a module path within a project.

    Allows to provide fully qualified module names based on file paths,
    base path, and Python module naming conventions.

    This object stores filesystem context for a source file. Import-system
    resolution is handled by the module resolver, not by this model's
    validation.
    """

    origin: Path = Field(description="Absolute file path to the module")
    base_path: Path = Field(description="Absolute path to the top-level project directory")

    @model_validator(mode="after")
    def validate_paths(self) -> Self:
        validate_python_file(self.origin)

        if not is_dir(self.base_path):
            raise NotADirectoryError(f"Base path '{self.base_path}' is not a valid directory")

        if DELIMITER in self.top_level:
            raise ValueError(f"Top-level module name cannot contain delimiters '{DELIMITER}'")

        _ = self.relative
        _ = self.top_level
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
