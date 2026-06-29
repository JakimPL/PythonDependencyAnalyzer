from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pda.config import ModuleImportsAnalyzerConfig
from pda.models import ModuleNode
from pda.resolution import (
    ModuleResolutionService,
    ResolvedModuleKind,
    SourceModuleContext,
    TargetEnvironment,
)
from pda.specification import (
    CategorizedModule,
    CategorizedModuleDict,
    ImportPath,
    ModuleSource,
)
from pda.tools.logger import logger


class ImportResolver:
    def __init__(
        self,
        project_root: Path,
        package: str,
        config: ModuleImportsAnalyzerConfig,
    ) -> None:
        self._project_root = project_root.resolve()
        self._package = package
        self._config = config
        self._resolution = ModuleResolutionService(TargetEnvironment.create((self._project_root,)))

    def create_root(self, filepath: Path) -> ModuleNode:
        resolution = self._resolution.resolve_filesystem_path(filepath, source_root=self._project_root)
        module = self._resolution.to_categorized_module(resolution, package=self._package)

        return ModuleNode(module, qualified_name=self._config.qualified_names)

    def resolve_import_path(
        self,
        module_source: ModuleSource,
        import_path: ImportPath,
    ) -> Optional[ImportPath]:
        context = self._source_context(module_source)
        if context is None:
            logger.debug("Module spec not found for import path '%s'; keeping it for categorization", import_path)
            return import_path

        resolution = self._resolution.resolve_import_path(context, import_path)
        if not resolution.resolved or resolution.identity is None:
            logger.debug("Module spec not found for import path '%s'; keeping it for categorization", import_path)
            return import_path

        if resolution.kind == ResolvedModuleKind.NAMESPACE_PACKAGE:
            return None

        return ImportPath.from_string(resolution.identity.name)

    def resolve_to_module(
        self,
        module_source: ModuleSource,
        import_path: ImportPath,
    ) -> CategorizedModule:
        context = self._source_context(module_source)
        if context is None:
            logger.debug(
                "Source context not found while resolving import path '%s'",
                import_path,
            )
            resolution = self._resolution.resolve_project_name(import_path.module or "<unknown>")
        else:
            resolution = self._resolution.resolve_import_path(context, import_path)

        package = resolution.identity.parent_name if resolution.identity is not None else None
        return self._resolution.to_categorized_module(resolution, package=package)

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

    def _source_context(self, module_source: ModuleSource) -> Optional[SourceModuleContext]:
        return self._resolution.source_context(module_source.origin, source_root=module_source.base_path)
