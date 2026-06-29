from __future__ import annotations

from pathlib import Path
from typing import Optional

from pda.config import ValidationOptions
from pda.exceptions import PDAImportPathError
from pda.resolution import ModuleResolutionService, TargetEnvironment
from pda.specification import CategorizedModule, ModuleCategory, UnavailableModule
from pda.tools.logger import logger


class ModuleCreator:
    """Compatibility adapter for creating categorized modules from names.

    New analyzer code should use ModuleResolutionService directly. This class
    remains for public callers and for no-project-root runtime collection.
    """

    _VALIDATION_OPTIONS = ValidationOptions(
        allow_missing_spec=True,
        validate_origin=True,
        expect_python=False,
        raise_error=False,
    )

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self._project_root = project_root
        self._resolver = (
            ModuleResolutionService(
                TargetEnvironment.create(
                    (project_root,),
                )
            )
            if project_root is not None
            else None
        )

    @property
    def validation_options(self) -> ValidationOptions:
        return self._VALIDATION_OPTIONS

    def create_module(
        self,
        name: str,
        containing_package: Optional[str] = None,
    ) -> CategorizedModule:
        """
        Create a CategorizedModule from a module name.

        Args:
            name: Module name to create.
            containing_package: Optional containing package for relative names.

        Returns:
            CategorizedModule instance, or unavailable module if error during creation.
        """
        try:
            if self._resolver is not None:
                resolution = self._resolver.resolve_project_name(name, containing_package=containing_package)
                return self._resolver.to_categorized_module(resolution)

            return CategorizedModule.create(
                name,
                project_root=self._project_root,
                containing_package=containing_package,
                validation_options=self._VALIDATION_OPTIONS,
            )

        except (AttributeError, KeyError, IndexError, PDAImportPathError) as error:
            logger.warning(
                "Module '%s' error:\n%s: [%s]",
                name,
                error.__class__.__name__,
                error,
            )

            return CategorizedModule(
                module=UnavailableModule(
                    name=name,
                    error=error,
                ),
                category=ModuleCategory.UNKNOWN,
            )
