from __future__ import annotations

from pathlib import Path
from typing import Optional

from pda.config import ValidationOptions
from pda.specification import CategorizedModule
from pda.specification.modules.module.category import ModuleCategory
from pda.specification.modules.module.unavailable import UnavailableModule
from pda.tools.logger import logger


class ModuleCreator:
    """Handles creation of CategorizedModule instances from module names."""

    _VALIDATION_OPTIONS = ValidationOptions(
        allow_missing_spec=True,
        validate_origin=True,
        expect_python=False,
        raise_error=False,
    )

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._project_root = project_root

    @property
    def validation_options(self) -> ValidationOptions:
        return self._VALIDATION_OPTIONS

    def create_module(
        self,
        name: str,
        package: Optional[str] = None,
    ) -> CategorizedModule:
        """
        Create a CategorizedModule from a module name.

        Args:
            name: Module name to create
            package: Optional package name

        Returns:
            CategorizedModule if successful, None if error during creation
        """
        try:
            return CategorizedModule.create(
                name,
                project_root=self._project_root,
                package=package,
                validation_options=self._VALIDATION_OPTIONS,
            )

        except (AttributeError, KeyError, IndexError) as error:
            logger.warning(
                "Module '%s' error:\n%s: [%s]",
                name,
                error.__class__.__name__,
                error,
            )

            return CategorizedModule(
                module=UnavailableModule(
                    name=name,
                    package=package,
                    error=error,
                ),
                category=ModuleCategory.UNAVAILABLE,
            )
