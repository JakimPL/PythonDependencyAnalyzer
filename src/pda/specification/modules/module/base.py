from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Self, Tuple

from pydantic import Field, model_validator

from pda.constants import DELIMITER
from pda.specification.base import Specification
from pda.specification.imports.path import ImportPath
from pda.specification.modules.module.category import ModuleCategory


class BaseModule(Specification, ABC):
    """
    Base class for module specifications, containing common attributes and methods for all module types.
    This class is not meant to be instantiated directly, but rather serves as a foundation for more specific
    module specifications such as Module or UnavailableModule.
    """

    name: str = Field(description="Fully qualified module name, e.g. 'package.module'")

    @model_validator(mode="after")
    @abstractmethod
    def validate_module(self) -> Self: ...

    @property
    def parts(self) -> Tuple[str, ...]:
        return tuple(self.name.split(DELIMITER))

    @property
    def module_name(self) -> str:
        return self.name.removesuffix(".__init__").split(DELIMITER)[-1]

    @property
    def qualified_name(self) -> str:
        return self.name.removesuffix(".__init__")

    def prefix(self, level: int) -> str:
        """
        Dotted-name prefix of the qualified name up to the given absolute level,
        counted from the package root (level 0 = top-level package). Levels beyond
        the number of components are clamped to the full qualified name.
        """
        parts = self.qualified_name.split(DELIMITER)
        return DELIMITER.join(parts[: level + 1])

    @property
    def top_level_module(self) -> str:
        return self.name.split(DELIMITER)[0]

    @property
    def is_top_level(self) -> bool:
        return self.name == self.top_level_module

    @property
    def is_private(self) -> bool:
        return any(part.startswith("_") and not part.startswith("__") for part in self.parts)

    @property
    def import_path(self) -> ImportPath:
        return ImportPath.from_string(self.name)

    @property
    @abstractmethod
    def base_path(self) -> Optional[Path]: ...

    @abstractmethod
    def get_category(self, base_path: Optional[Path] = None) -> ModuleCategory: ...
