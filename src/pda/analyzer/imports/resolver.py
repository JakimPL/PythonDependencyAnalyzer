from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Set

from pda.config import ModuleImportsAnalyzerConfig, ValidationOptions
from pda.exceptions import PDAFindSpecError, PDAImportPathError
from pda.models import ModuleNode
from pda.specification import (
    CategorizedModule,
    CategorizedModuleDict,
    ImportPath,
    ModuleCategory,
    ModuleSource,
    SysPaths,
    UnavailableModule,
    is_namespace_package,
    validate_spec_origin,
)
from pda.tools.logger import logger


class ModuleResolver:
    _ROOT_VALIDATION_OPTIONS = ValidationOptions.strict()
    _MODULE_VALIDATION_OPTIONS = ValidationOptions(
        allow_missing_spec=True,
        validate_origin=True,
        expect_python=False,
        raise_error=False,
    )

    def __init__(
        self,
        project_root: Path,
        package: str,
        config: ModuleImportsAnalyzerConfig,
    ) -> None:
        self._project_root = project_root.resolve()
        self._package = package
        self._config = config

    @property
    def module_validation_options(self) -> ValidationOptions:
        return self._MODULE_VALIDATION_OPTIONS

    def create_root(self, filepath: Path) -> ModuleNode:
        root_source = ModuleSource(
            origin=filepath,
            base_path=self._project_root,
            package=self._package,
        )

        module = CategorizedModule.create(
            name=root_source.module.name,
            project_root=self._project_root,
            package=self._package,
            validation_options=self._ROOT_VALIDATION_OPTIONS,
        )

        return ModuleNode(module, qualified_name=self._config.qualified_names)

    def resolve_import_path(
        self,
        module_source: ModuleSource,
        import_path: ImportPath,
        processed: Set[Optional[Path]],
    ) -> Optional[ImportPath]:
        spec = module_source.get_spec(import_path)
        if spec is None:
            logger.debug("Module spec not found for import path '%s'", import_path)
            return None

        if is_namespace_package(spec):
            return None

        origin = validate_spec_origin(spec, expect_python=self._MODULE_VALIDATION_OPTIONS.expect_python)
        if origin in processed:
            return None

        return SysPaths.resolve(
            origin,
            base_path=module_source.base_path,
            validation_options=self._MODULE_VALIDATION_OPTIONS,
        )

    def resolve_to_module(
        self,
        module_source: ModuleSource,
        import_path: ImportPath,
    ) -> CategorizedModule:
        spec = module_source.get_spec(import_path)
        package_spec = module_source.get_package_spec(import_path)
        package = package_spec.name if package_spec is not None else None

        def create_unavailable_module(error: Exception) -> CategorizedModule:
            return CategorizedModule(
                module=UnavailableModule(
                    name=import_path.module if import_path.module else "<unknown>",
                    package=package,
                    error=error,
                ),
                category=ModuleCategory.UNAVAILABLE,
            )

        if spec is None:
            logger.debug(
                "Module spec not found for import path '%s' (package: '%s')",
                import_path,
                package_spec.name if package_spec is not None else None,
            )

            return create_unavailable_module(PDAFindSpecError(import_path))

        try:
            return CategorizedModule.from_spec(
                spec,
                project_root=self._project_root,
                package=package,
            )
        except (AttributeError, KeyError, IndexError) as error:
            logger.warning(
                "Module '%s' error:\n%s: [%s]",
                spec.name,
                error.__class__.__name__,
                error,
            )
            unavailable_module = create_unavailable_module(error)
        except PDAImportPathError as import_error:
            logger.debug(
                "Module '%s' import path error:\n%s: [%s]",
                spec.name,
                import_error.__class__.__name__,
                import_error,
            )
            unavailable_module = create_unavailable_module(import_error)

        return unavailable_module

    def resolve_batch(
        self,
        module_source: ModuleSource,
        import_paths: List[ImportPath],
    ) -> CategorizedModuleDict:
        modules: CategorizedModuleDict = {}
        for import_path in import_paths:
            module = self.resolve_to_module(module_source, import_path)
            modules[module.name] = module

        return modules
