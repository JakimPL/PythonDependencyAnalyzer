from __future__ import annotations

import ast
from copy import copy
from pathlib import Path
from typing import List, Optional, Set

import networkx as nx
from anytree import PreOrderIter

from pda.analyzer import BaseAnalyzer
from pda.config import ModuleImportsAnalyzerConfig
from pda.exceptions import PDAImportError
from pda.graph import ImportGraph
from pda.nodes import ASTForest
from pda.specification import (
    ImportPath,
    Module,
    ModuleCategory,
    ModuleDict,
    ModuleSource,
    OriginType,
    SysPaths,
    is_spec_origin_valid,
)
from pda.tools import OrderedSet, logger
from pda.types import Pathlike


class ModuleImportsAnalyzer(BaseAnalyzer[ModuleImportsAnalyzerConfig, nx.DiGraph]):
    def __init__(
        self,
        config: ModuleImportsAnalyzerConfig,
        project_root: Pathlike,
        package: str,
    ) -> None:
        super().__init__(config=config, project_root=project_root, package=package)

        self._filepath: Optional[Path] = None
        self._modules: ModuleDict = {}  # TODO: change to ModulesCollection
        self._graph: ImportGraph = ImportGraph()

    def __bool__(self) -> bool:
        return not self._graph.empty

    def __call__(self, filepath: Path, refresh: bool = False) -> nx.DiGraph:
        self._create_graph_if_needed(filepath, refresh=refresh)
        return self._graph(self.config.node_format)

    def clear(self) -> None:
        self._filepath = None
        self._modules.clear()
        self._graph.clear()

    @property
    def filepath(self) -> Optional[Path]:
        return copy(self._filepath)

    @property
    def modules(self) -> ModuleDict:
        self._create_graph_if_needed()
        return self._modules.copy()

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
        self._modules = {root.name: root}
        new_modules: OrderedSet[Module] = OrderedSet([root])

        while new_modules:
            module = new_modules.pop()
            if module.origin in processed:
                continue

            self._collect_new_modules(
                module,
                new_modules,
                processed,
            )

    def _check_graph(self) -> None:
        if self._graph.empty:
            logger.warning("The dependency graph is empty.")

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
    ) -> ModuleDict:
        """
        Analyze a Python file to extract all imported module paths,
        and return their corresponding file paths.
        """
        tree = ASTForest(filepath)
        module_source = ModuleSource(origin=filepath, base_path=base_path, package=package)
        import_paths = self._collect_imports(module_source, tree, processed=processed)
        return self._collect_modules(module_source, import_paths)

    def analyze_module(
        self,
        module: Module,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> ModuleDict:
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
        module: Module,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> bool:
        if module.origin_type != OriginType.PYTHON:
            return False

        category = module.get_category(self._project_root)
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
    ) -> ModuleDict:
        modules: ModuleDict = {}
        for module_path in module_paths:
            module = self._get_module_from_import_path(
                module_source,
                module_path,
            )
            if module is not None:
                modules[module.name] = module

        return modules

    def _get_module_from_import_path(
        self,
        module_source: ModuleSource,
        module_path: ImportPath,
    ) -> Optional[Module]:
        try:
            spec = module_source.get_spec(module_path)
            package_spec = module_source.get_package_spec(module_path)
        except (ImportError, ModuleNotFoundError, ValueError) as error:
            logger.warning(
                "Could not resolve import path '%s' in module '%s': %s",
                module_path,
                module_source.module.name,
                error,
            )
            return None

        try:
            package = package_spec.name if package_spec is not None else None
            return Module.from_spec(spec, package=package)
        except PDAImportError as import_error:
            logger.debug(
                "%s: %s [%s]",
                import_error.__class__.__name__,
                spec.name,
                import_error,
            )
            return None

    def _create_root(self, filepath: Path) -> Module:
        if self._project_root is None or self._package is None:
            raise ValueError("Project root and package must be set to create the root module")

        root_source = ModuleSource(
            origin=filepath,
            base_path=self._project_root,
            package=self._package,
        )

        return root_source.module

    def _collect_new_modules(
        self,
        module: Module,
        new_modules: OrderedSet[Module],
        processed: Set[Optional[Path]],
    ) -> None:
        processed.add(module.origin)
        imported_modules = self.analyze_module(module)
        for imported_module_name, imported_module in imported_modules.items():
            if imported_module_name not in self._modules:
                self._modules[imported_module_name] = imported_module

            target_module = self._modules[imported_module_name]
            self._graph.add_edge(module, target_module)
            new_modules.add(target_module)

    def _resolve(
        self,
        module_source: ModuleSource,
        path: ImportPath,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> Optional[ImportPath]:
        processed = processed or set()
        try:
            spec = module_source.get_spec(path, validate_origin=True)
            if not is_spec_origin_valid(spec.origin):
                return None
        except (ImportError, ModuleNotFoundError, ValueError, PDAImportError) as error:
            logger.debug(
                "%s: %s",
                error.__class__.__name__,
                error,
            )
            return None

        origin = Path(spec.origin) if spec.origin is not None else None
        if origin is None or origin in processed:
            return None

        return SysPaths.resolve(spec, base_path=module_source.base_path)
