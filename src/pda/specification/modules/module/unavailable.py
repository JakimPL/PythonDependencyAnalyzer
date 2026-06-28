from pathlib import Path
from typing import Optional, Self

from pydantic import Field, model_validator

from pda.exceptions import PDAMissingModuleNameError
from pda.specification.modules.module.base import BaseModule
from pda.specification.modules.module.category import ModuleCategory


class UnavailableModule(BaseModule):
    """
    Represents a module that is unavailable for analysis. This can occur when the module cannot be imported or accessed
    during the analysis process. The UnavailableModule specification allows us to handle such cases gracefully and
    provide information about the unavailable module in the dependency graph.
    """

    error: Optional[Exception] = Field(
        default=None, description="The exception that caused the module to be unavailable, if any."
    )

    @model_validator(mode="after")
    def validate_module(self) -> Self:
        if not self.name:
            raise PDAMissingModuleNameError("Module name cannot be empty")

        if self.package is not None and not self.package:
            raise PDAMissingModuleNameError("Package name cannot be empty if provided")

        return self

    @property
    def spec(self) -> None:
        return None

    @property
    def base_path(self) -> None:
        return None

    def get_category(self, base_path: Optional[Path] = None) -> ModuleCategory:
        return ModuleCategory.UNKNOWN
