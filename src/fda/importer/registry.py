from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Optional, Set

import networkx as nx
from anytree import PreOrderIter

from fda.exceptions import FDAImportError
from fda.importer.config import ImportConfig
from fda.importer.graph import ImportGraphEnum
from fda.node import AST
from fda.specification import (
    ImportPath,
    Module,
    ModuleCategory,
    ModuleSource,
    OriginType,
    SysPaths,
    is_spec_origin_valid,
)
from fda.tools import logger
from fda.types import Pathlike


class ModuleRegistry:
    def __init__(
        self,
        import_config: ImportConfig,
        project_root: Pathlike,
        package: str,
    ) -> None:
        self.import_config = import_config
        self.project_root = Path(project_root).resolve()
        self.package = package
        self.modules: Dict[str, Module] = {}
        self.graph: Optional[nx.DiGraph] = None
        self.filepath: Optional[Path] = None

    def __call__(self, filepath: Path) -> nx.DiGraph:
        if self.graph is None or self.filepath != filepath:
            self._create_graph(filepath)

        return self._create_output_graph()

    def _create_graph(self, filepath: Path) -> None:
        self.graph = nx.DiGraph()
        self.filepath = filepath

        root = self._create_root(filepath)
        self.graph.add_node(root)

        processed: Set[Optional[Path]] = {None}
        self.modules = {root.name: root}
        new_modules: Set[Module] = {root}

        while new_modules:
            module = new_modules.pop()
            if module.origin in processed:
                continue

            self._collect_new_modules(
                module,
                new_modules,
                processed,
            )

    def _create_output_graph(self) -> nx.DiGraph:
        if self.graph is None:
            raise ValueError("Graph has not been created yet")

        output_type = self.import_config.output
        match output_type:
            case ImportGraphEnum.FULL:
                return nx.DiGraph(self.graph)
            case ImportGraphEnum.NAMES:
                return nx.relabel_nodes(
                    self.graph,
                    lambda module: module.name,
                    copy=True,
                )
            case ImportGraphEnum.TOP_LEVEL:
                return self._create_top_level_graph()

        raise ValueError(f"Unsupported output type: {output_type}")

    def _create_top_level_graph(self) -> nx.DiGraph:
        """
        Create a graph where nodes are identified by their top-level module name.
        Collapses all submodules into their parent top-level module.
        """
        if self.graph is None:
            raise ValueError("Graph has not been created yet")

        def partition(module1: Module, module2: Module) -> bool:
            return module1.top_level_module == module2.top_level_module

        quotient = nx.quotient_graph(
            self.graph,
            partition,
            create_using=nx.DiGraph,
        )

        return nx.relabel_nodes(
            quotient,
            lambda node: next(iter(node)).top_level_module,
            copy=False,
        )

    def analyze_file(
        self,
        filepath: Path,
        base_path: Path,
        package: str,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> Dict[str, Module]:
        """
        Analyze a Python file to extract all imported module paths,
        and return their corresponding file paths.
        """
        tree = AST(filepath)
        module_source = ModuleSource(origin=filepath, base_path=base_path, package=package)
        import_paths = self._collect_imports(module_source, tree, processed=processed)
        return self._collect_modules(module_source, import_paths)

    def analyze_module(
        self,
        module: Module,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> Dict[str, Module]:
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

        category = module.get_category(self.project_root)
        if not self.import_config.scan_stdlib and category == ModuleCategory.STDLIB:
            return False

        if not self.import_config.scan_external and category == ModuleCategory.EXTERNAL:
            return False

        assert module.origin is not None
        processed = processed or set()
        if module.origin in processed:
            return False

        return True

    def _collect_imports(
        self,
        module_source: ModuleSource,
        tree: AST,
        processed: Optional[Set[Optional[Path]]] = None,
    ) -> List[ImportPath]:
        module_paths: Dict[ImportPath, None] = {}
        import_paths = self._collect_import_paths(tree)
        for import_path in import_paths:
            module_path = self._resolve(module_source, import_path, processed)
            if module_path is not None:
                module_paths[module_path] = None

        return list(module_paths.keys())

    def _collect_import_paths(
        self,
        tree: AST,
    ) -> List[ImportPath]:
        import_paths: Dict[ImportPath, None] = {}
        for node in PreOrderIter(tree.root):
            if node.type in (ast.Import, ast.ImportFrom):
                import_node = node.ast
                new_paths = {import_path.get_module_path() for import_path in ImportPath.from_ast(import_node)}
                import_paths.update({path: None for path in new_paths})

        return list(import_paths.keys())

    def _collect_modules(
        self,
        module_source: ModuleSource,
        module_paths: List[ImportPath],
    ) -> Dict[str, Module]:
        modules: Dict[str, Module] = {}
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
        except FDAImportError as import_error:
            logger.debug(
                "%s: %s [%s]",
                import_error.__class__.__name__,
                spec.name,
                import_error,
            )
            return None

    def _create_root(self, filepath: Path) -> Module:
        root_source = ModuleSource(
            origin=filepath,
            base_path=self.project_root,
            package=self.package,
        )

        return root_source.module

    def _collect_new_modules(
        self,
        module: Module,
        new_modules: Set[Module],
        processed: Set[Optional[Path]],
    ) -> None:
        processed.add(module.origin)
        imported_modules = self.analyze_module(module)
        for imported_module_name, imported_module in imported_modules.items():
            self._add_node(module)
            if imported_module_name not in self.modules:
                self.modules[imported_module_name] = imported_module

            target_module = self.modules[imported_module_name]
            self._add_edge(module, target_module)
            new_modules.add(target_module)

    def _add_node(self, module: Module) -> None:
        if self.graph is None:
            raise ValueError("Graph has not been created yet")

        if not self.graph.has_node(module):
            self.graph.add_node(module)

    def _add_edge(self, from_module: Module, to_module: Module) -> None:
        if self.graph is None:
            raise ValueError("Graph has not been created yet")

        if from_module != to_module and not self.graph.has_edge(from_module, to_module):
            self._add_node(from_module)
            self._add_node(to_module)
            self.graph.add_edge(from_module, to_module)

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
        except (ImportError, ModuleNotFoundError, ValueError, FDAImportError) as error:
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
