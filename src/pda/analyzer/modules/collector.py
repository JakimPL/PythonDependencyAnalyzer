import pkgutil
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, overload

import networkx as nx

from pda.analyzer.base import BaseAnalyzer
from pda.config import ModulesCollectorConfig, ValidationOptions
from pda.graph import ImportGraph
from pda.nodes import PathForest, PathNode
from pda.specification import (
    CategorizedModule,
    CategorizedModuleDict,
    ImportPath,
    Module,
    ModuleCategory,
    ModulesCollection,
    SysPaths,
)
from pda.tools.logger import logger
from pda.tools.paths import filter_subdirectories, resolve_path
from pda.types import Pathlike


class ModulesCollector(BaseAnalyzer[ModulesCollectorConfig, nx.DiGraph]):
    config: ModulesCollectorConfig

    def __init__(
        self,
        config: ModulesCollectorConfig,
        project_root: Optional[Pathlike] = None,
        package: Optional[str] = None,
    ) -> None:
        super().__init__(config=config, project_root=project_root, package=package)

        self._collection: ModulesCollection = ModulesCollection(allow_unavailable=False)
        self._pkg_modules: Dict[str, pkgutil.ModuleInfo] = self._collect_pkg_modules()
        self._graph: ImportGraph = ImportGraph()
        self._path_forest: PathForest = self._initialize_forest()

        self._module_validation_options = ValidationOptions.permissive()

    def __call__(self, refresh: bool = False) -> nx.DiGraph:
        self._collect_modules_if_needed(refresh=refresh)
        return self._graph(self.config.node_format)

    def __bool__(self) -> bool:
        return bool(self._collection)

    @overload
    def __getitem__(self, name_or_category: ModuleCategory) -> CategorizedModuleDict: ...

    @overload
    def __getitem__(self, name_or_category: str) -> CategorizedModule: ...

    def __getitem__(
        self, name_or_category: Union[str, ModuleCategory]
    ) -> Union[CategorizedModule, CategorizedModuleDict]:
        return self._collection[name_or_category]

    def _collect_modules_if_needed(self, refresh: bool = False) -> None:
        if refresh or not self:
            self._collect_modules()

    @property
    def collection(self) -> ModulesCollection:
        self._collect_modules_if_needed()
        return self._collection.copy()

    @property
    def categories(self) -> Tuple[ModuleCategory, ...]:
        return self._collection.categories

    @property
    def modules(self) -> CategorizedModuleDict:
        self._collect_modules_if_needed()
        return self._collection.modules

    @property
    def graph(self) -> ImportGraph:
        self._collect_modules_if_needed()
        return self._graph.copy()

    @property
    def stdlib(self) -> CategorizedModuleDict:
        self._collect_modules_if_needed()
        return self._collection.stdlib

    @property
    def external(self) -> CategorizedModuleDict:
        self._collect_modules_if_needed()
        return self._collection.external

    @property
    def internal(self) -> CategorizedModuleDict:
        self._collect_modules_if_needed()
        return self._collection.internal

    @classmethod
    def default_config(cls) -> ModulesCollectorConfig:
        return ModulesCollectorConfig()

    def clear(self) -> None:
        self._graph.clear()
        self._collection.clear()

    def get_category(self, module: Union[str, ModuleSpec, Module, CategorizedModule]) -> ModuleCategory:
        if isinstance(module, ModuleSpec):
            module = module.name

        if isinstance(module, str):
            module = self[module]

        elif not isinstance(module, (Module, CategorizedModule)):
            raise TypeError(
                f"Unsupported module type: {type(module)}, expected str, ModuleSpec, Module, or CategorizedModule"
            )

        if isinstance(module, CategorizedModule):
            return module.category

        return module.get_category(self._project_root)

    def _initialize_forest(self) -> PathForest:
        paths: List[Path] = SysPaths.get_candidates(base_path=self._project_root)
        root_paths = filter_subdirectories(paths)
        return PathForest(root_paths)

    def _collect_pkg_modules(self) -> Dict[str, pkgutil.ModuleInfo]:
        return {module.name: module for module in pkgutil.iter_modules()}

    def _update_graph(self, module: CategorizedModule, parent: Optional[CategorizedModule] = None) -> None:
        self._graph.add_node(module)
        if parent:
            self._graph.add_edge(parent, module)

    def _collect_modules(self) -> None:
        self.clear()
        self._collect_external_modules()
        self._collect_internal_modules()
        if not self:
            logger.warning("No modules collected. Check your configuration and project structure")

    def _collect_external_modules(self) -> None:
        for pkg_module in self._pkg_modules.values():
            name = pkg_module.name
            if name in sys.stdlib_module_names:
                if not self.config.scan_stdlib:
                    continue
            elif not self.config.scan_external:
                continue

            is_package = pkg_module.ispkg
            package = name if is_package else None
            base_path = Path(pkg_module.module_finder.path)  # type: ignore[union-attr]
            self._add_module(name, base_path, package=package)

    def _collect_internal_modules(self) -> None:
        if not self._project_root:
            return

        self._add_submodules_from_files(
            location=self._project_root,
            base_path=self._project_root,
            package=self._package,
        )

    def _add_submodules_from_files(
        self,
        location: Pathlike,
        base_path: Path,
        parent: Optional[CategorizedModule] = None,
        package: Optional[str] = None,
    ) -> None:
        origin = resolve_path(location)
        if not origin:
            return

        files = self._get_submodule_paths(origin)
        import_paths = self._get_import_paths(files, base_path)
        for import_path in import_paths:
            self._add_module(
                import_path,
                base_path,
                package=package,
                parent=parent,
            )

    def _get_import_paths(self, files: List[Path], base_path: Path) -> List[ImportPath]:
        import_paths: List[ImportPath] = []
        for path in files:
            import_path = self._get_import_path(path, base_path)
            if import_path is not None:
                import_paths.append(import_path)

        return import_paths

    def _get_import_path(self, path: Path, base_path: Path) -> Optional[ImportPath]:
        import_path = ImportPath.from_path(path, base_path)
        if import_path is None:
            logger.warning(
                "Could not determine import path for '%s' relative to '%s'",
                path,
                base_path,
            )

        return import_path

    def _add_module(
        self,
        name: Union[str, ImportPath],
        base_path: Path,
        package: Optional[str] = None,
        parent: Optional[CategorizedModule] = None,
    ) -> None:
        name = str(name)
        try:
            module = self._get_module(name, package=package)
        except (AttributeError, KeyError, IndexError) as error:
            logger.warning(
                "Module '%s' error:\n%s: [%s]",
                name,
                error.__class__.__name__,
                error,
            )
            return

        if not module:
            return

        self._collection.add(module)
        self._update_graph(module, parent)
        self._add_submodules(module, base_path, package=name)

    def _add_submodules(
        self,
        module: CategorizedModule,
        base_path: Path,
        package: Optional[str] = None,
    ) -> None:
        if not module.spec.submodule_search_locations:
            return

        for location in module.spec.submodule_search_locations:
            self._add_submodules_from_files(
                location,
                base_path=base_path,
                parent=module,
                package=package,
            )

    def _get_module(
        self,
        name: str,
        package: Optional[str] = None,
    ) -> Optional[CategorizedModule]:
        module = CategorizedModule.create(
            name,
            project_root=self._project_root,
            package=package,
            validation_options=self._module_validation_options,
        )

        if module is None:
            return None

        category = module.category
        if name in self._collection[category]:
            return None

        return module

    def _get_submodule_paths(self, origin: Optional[Path]) -> List[Path]:
        if origin is None:
            return []

        origin_node = self._path_forest.get(origin)
        if origin_node is None:
            return []

        child: PathNode
        paths: List[Path] = []
        for child in origin_node.children:
            if (child.is_python_file and not child.is_init) or (child.is_dir and child.is_package):
                paths.append(child.filepath)

        return sorted(paths)
