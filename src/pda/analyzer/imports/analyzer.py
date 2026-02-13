from __future__ import annotations

import ast
from copy import copy
from pathlib import Path
from typing import List, Optional, Set

import networkx as nx
from anytree import PreOrderIter

from pda.analyzer.base import BaseAnalyzer
from pda.config import ModuleImportsAnalyzerConfig, ValidationOptions
from pda.exceptions import PDAImportPathError, PDAMissingModuleSpecError
from pda.graph import ImportGraph
from pda.nodes import ASTForest
from pda.specification import (
    CategorizedModule,
    CategorizedModuleDict,
    ImportPath,
    ModuleCategory,
    ModulesCollection,
    ModuleSource,
    OriginType,
    SysPaths,
    is_namespace_package,
    validate_spec_origin,
)
from pda.tools import OrderedSet
from pda.tools.logger import logger
from pda.types import Pathlike


class ModuleImportsAnalyzer(BaseAnalyzer[ModuleImportsAnalyzerConfig, nx.DiGraph]):
    config: ModuleImportsAnalyzerConfig

    def __init__(
        self,
        config: ModuleImportsAnalyzerConfig,
        project_root: Pathlike,
        package: str,
    ) -> None:
        super().__init__(config=config, project_root=project_root, package=package)

        self._filepath: Optional[Path] = None
        self._collection: ModulesCollection = ModulesCollection(allow_unavailable=True)
        self._graph: ImportGraph = ImportGraph()

        self._root_validation_options = ValidationOptions.root()
        self._module_validation_options = ValidationOptions(
            allow_missing_spec=True,
            validate_origin=True,
            expect_python=False,
            raise_error=False,
        )

    def __bool__(self) -> bool:
        return not self._graph.empty

    def __call__(self, filepath: Path, refresh: bool = False) -> nx.DiGraph:
        self._create_graph_if_needed(filepath, refresh=refresh)
        return self._graph(self.config.node_format)

    def clear(self) -> None:
        self._filepath = None
        self._collection.clear()
        self._graph.clear()

    @property
    def filepath(self) -> Optional[Path]:
        return copy(self._filepath)

    @property
    def modules(self) -> CategorizedModuleDict:
        self._create_graph_if_needed()
        return self._collection.modules

    @property
    def graph(self) -> ImportGraph:
        self._create_graph_if_needed()
        return self._graph.copy()

    @classmethod
    def default_config(cls) -> ModuleImportsAnalyzerConfig:
        return ModuleImportsAnalyzerConfig()

    def _create_graph_if_needed(
        self,
        filepath: Optional[Path] = None,
        refresh: bool = False,
    ) -> None:
        filepath = filepath or self._filepath
        if not filepath:
            raise ValueError("No module has been analyzed yet")

        if refresh or not self or self._filepath != filepath:
            self._create_graph(filepath)

    def _create_graph(self, filepath: Path) -> None:
        self.clear()

        self._filepath = filepath
        root = self._create_root(filepath)
        self._graph.add_node(root)

        processed: Set[Optional[Path]] = {None}
        new_modules: OrderedSet[CategorizedModule] = OrderedSet([root])

        while new_modules:
            module = new_modules.pop()
            if module.origin in processed:
                continue

            if module.is_namespace_package:
                continue

            self._collect_new_modules(
                module,
                new_modules,
                processed,
            )

    def _check_graph(self) -> None:
        if self._graph.empty:
            logger.warning("The dependency graph is empty")

        cycle = self._graph.find_cycle()
        if cycle is not None:
            logger.warning(
                "The dependency graph has a cycle. Example cycle:\n : %s",
                "\n-> ".join(module.name for module in cycle),
            )

    def analyze_file(
        self,
        filepath: Path,
        base_path: Path,
        package: str,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> CategorizedModuleDict:
        """
        Analyze a Python file to extract all imported module paths,
        and return their corresponding file paths.
        """
        tree = ASTForest([filepath])
        module_source = ModuleSource(
            origin=filepath,
            base_path=base_path,
            package=package,
            validation_options=self._module_validation_options,
        )

        import_paths = self._collect_imports(module_source, tree, processed=processed)
        return self._collect_modules(module_source, import_paths)

    def analyze_module(
        self,
        module: CategorizedModule,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> CategorizedModuleDict:
        """
        Analyze a module to extract all imported module paths,
        and return their corresponding file paths.
        """
        if not self._check_if_should_scan(module, processed=processed):
            return {}

        assert module.origin is not None
        return self.analyze_file(
            module.origin,
            module.base_path,
            module.top_level_module,
            processed=processed,
        )

    def _check_if_should_scan(
        self,
        module: CategorizedModule,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> bool:
        if module.origin_type != OriginType.PYTHON:
            return False

        category = module.category
        if not self.config.scan_stdlib and category == ModuleCategory.STDLIB:
            return False

        if not self.config.scan_external and category == ModuleCategory.EXTERNAL:
            return False

        assert module.origin is not None
        processed = processed or set()
        if module.origin in processed:
            return False

        return True

    def _collect_imports(
        self,
        module_source: ModuleSource,
        tree: ASTForest,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> List[ImportPath]:
        module_paths: OrderedSet[ImportPath] = OrderedSet()
        import_paths = self._collect_import_paths(tree)
        for import_path in import_paths:
            module_path = self._resolve(module_source, import_path, processed)
            if module_path is not None:
                module_paths.add(module_path)

        return list(module_paths)

    def _collect_import_paths(
        self,
        tree: ASTForest,
    ) -> List[ImportPath]:
        import_paths: OrderedSet[ImportPath] = OrderedSet()
        nodes = [
            node
            for root in tree.roots
            for node in PreOrderIter(root)
            if node.type
            in (
                ast.Import,
                ast.ImportFrom,
            )
        ]

        for node in nodes:
            import_node = node.ast
            new_paths = [import_path.get_module_path() for import_path in ImportPath.from_ast(import_node)]
            import_paths.update(new_paths)

        return list(import_paths)

    def _collect_modules(
        self,
        module_source: ModuleSource,
        module_paths: List[ImportPath],
    ) -> CategorizedModuleDict:
        modules: CategorizedModuleDict = {}
        for module_path in module_paths:
            module = self._get_module_from_import_path(module_source, module_path)
            if module is not None:
                modules[module.name] = module

        return modules

    def _get_module_from_import_path(
        self,
        module_source: ModuleSource,
        module_path: ImportPath,
    ) -> Optional[CategorizedModule]:
        spec = module_source.get_spec(module_path)
        package_spec = module_source.get_package_spec(module_path)
        if spec is None:
            logger.debug(
                "Module spec not found for import path '%s' (package: '%s')",
                module_path,
                package_spec.name if package_spec is not None else None,
            )
            return None

        if is_namespace_package(spec):
            return None

        package = package_spec.name if package_spec is not None else None
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
            return None
        except PDAImportPathError as import_error:
            logger.debug(
                "Module '%s' import path error:\n%s: [%s]",
                spec.name,
                import_error.__class__.__name__,
                import_error,
            )
            return None

    def _create_root(self, filepath: Path) -> CategorizedModule:
        if self._project_root is None or self._package is None:
            raise ValueError("Project root and package must be set to create the root module")

        root_source = ModuleSource(
            origin=filepath,
            base_path=self._project_root,
            package=self._package,
        )

        module = CategorizedModule.create(
            name=root_source.module.name,
            project_root=self._project_root,
            package=self._package,
            validation_options=self._root_validation_options,
        )

        if module is None:
            raise PDAMissingModuleSpecError(f"Could not create root module for {filepath}")

        return module

    def _collect_new_modules(
        self,
        module: CategorizedModule,
        new_modules: OrderedSet[CategorizedModule],
        processed: Set[Optional[Path]],
    ) -> None:
        processed.add(module.origin)
        imported_modules = self.analyze_module(module)
        for imported_module_name, imported_module in imported_modules.items():
            if imported_module_name not in self._collection:
                self._collection.add(imported_module)

            target_module = self._collection[imported_module_name]
            self._graph.add_edge(module, target_module)
            new_modules.add(target_module)

    def _resolve(
        self,
        module_source: ModuleSource,
        path: ImportPath,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> Optional[ImportPath]:
        processed = processed or set()
        spec = module_source.get_spec(path)
        if spec is None:
            logger.debug("Module spec not found for import path '%s'", path)
            return None

        if is_namespace_package(spec):
            return None

        origin = validate_spec_origin(spec, expect_python=self._module_validation_options.expect_python)
        if origin in processed:
            return None

        return SysPaths.resolve(
            origin,
            base_path=module_source.base_path,
            validation_options=self._module_validation_options,
        )
