from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Optional, Set

import networkx as nx
from anytree import PreOrderIter

from fda.exceptions import FDAImportError
from fda.importer.config import ImportConfig
from fda.node import AST
from fda.specification import ImportPath, Module, ModuleSource, OriginType
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

    def __call__(self, filepath: Path) -> nx.DiGraph:
        dependency_graph = nx.DiGraph()

        root_source = ModuleSource(
            origin=filepath,
            base_path=self.project_root,
            package=self.package,
        )

        root = root_source.module
        dependency_graph.add_node(root)

        processed: Set[str] = set()
        modules: Dict[str, Module] = {root.name: root}
        new_modules: Set[Module] = {root}

        while new_modules:
            module = new_modules.pop()
            if module.name in processed:
                continue

            processed.add(module.name)
            imported_modules = self.analyze_module(module)
            for module_name, module in imported_modules.items():
                if module_name not in modules:
                    modules[module_name] = module
                    dependency_graph.add_node(module)

                target_module = modules[module_name]
                dependency_graph.add_edge(module, target_module)
                new_modules.add(target_module)

        return dependency_graph

    def analyze_file(
        self,
        filepath: Path,
        base_path: Path,
        package: str,
    ) -> Dict[str, Module]:
        """
        Analyze a Python file to extract all imported module paths,
        and return their corresponding file paths.
        """
        tree = AST(filepath)
        module_source = ModuleSource(origin=filepath, base_path=base_path, package=package)
        import_paths = self._collect_imports(module_source, tree)
        return self._collect_modules(module_source, import_paths)

    def analyze_module(
        self,
        module: Module,
    ) -> Dict[str, Module]:
        """
        Analyze a module to extract all imported module paths,
        and return their corresponding file paths.
        """
        if module.origin_type != OriginType.PYTHON:
            return {}

        assert module.origin is not None
        return self.analyze_file(
            module.origin,
            module.base_path,
            module.top_level_module,
        )

    def _collect_imports(
        self,
        module_source: ModuleSource,
        tree: AST,
    ) -> Dict[ImportPath, None]:
        module_paths: Dict[ImportPath, None] = {}
        import_paths = self._collect_import_paths(tree)
        for import_path in import_paths:
            module_path = module_source.resolve(import_path)
            if module_path is not None:
                module_paths[module_path] = None

        return module_paths

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
        module_paths: Dict[ImportPath, None],
    ) -> Dict[str, Module]:
        modules: Dict[str, Module] = {}
        for module_path in module_paths:
            module = self._get_module_from_import_path(module_source, module_path)
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
        except (ImportError, ModuleNotFoundError, ValueError):
            logger.warning("Could not resolve import path '%s' in module '%s'", module_path, module_source.module.name)
            return None

        try:
            package = package_spec.name if package_spec is not None else None
            return Module.from_spec(spec, package=package)
        except FDAImportError:
            logger.warning(
                "Could not create module from spec for import path '%s' in module '%s'",
                module_path,
                module_source.module.name,
            )
            return None
