import pkgutil
from importlib.machinery import ModuleSpec
from typing import Dict, Optional, Tuple, Union, overload

import networkx as nx

from pydepgraph.analyzer import BaseAnalyzer
from pydepgraph.config import ModulesCollectorConfig
from pydepgraph.graph import ImportGraph
from pydepgraph.specification import (
    ImportPath,
    Module,
    ModuleCategory,
    ModuleDict,
    ModulesCollection,
    ModuleWrapper,
    OriginType,
    find_module_spec,
)
from pydepgraph.tools import logger
from pydepgraph.tools.utils import resolve_path
from pydepgraph.types import Pathlike


class ModulesCollector(BaseAnalyzer[ModulesCollectorConfig, nx.DiGraph]):
    def __init__(
        self,
        config: Optional[ModulesCollectorConfig] = None,
        project_root: Optional[Pathlike] = None,
        package: Optional[str] = None,
    ) -> None:
        super().__init__(config=config, project_root=project_root, package=package)

        self._modules: ModulesCollection = self._initialize_modules_collection()
        self._pkg_modules: Dict[str, pkgutil.ModuleInfo] = self._collect_pkg_modules()
        self._graph: ImportGraph = ImportGraph()

    def __call__(self, refresh: bool = False) -> nx.DiGraph:
        self._collect_modules_if_needed(refresh=refresh)
        return self._graph(self.config.node_format)

    def __bool__(self) -> bool:
        return any(modules for modules in self._modules.values())

    @overload
    def __getitem__(self, name_or_category: ModuleCategory) -> ModuleDict: ...

    @overload
    def __getitem__(self, name_or_category: str) -> Module: ...

    def __getitem__(self, name_or_category: Union[str, ModuleCategory]) -> Union[ModuleDict, Module]:
        if isinstance(name_or_category, ModuleCategory):
            if name_or_category == ModuleCategory.UNAVAILABLE:
                raise ValueError("Unavailable modules are not stored in this registry.")

            return self._modules[name_or_category]

        for category in self.categories:
            if name_or_category in self._modules[category]:
                return self._modules[category][name_or_category]

        raise KeyError(f"Module '{name_or_category}' not found.")

    def __len__(self) -> int:
        return sum(len(modules) for modules in self._modules.values())

    def _collect_modules_if_needed(self, refresh: bool = False) -> None:
        if refresh or not self:
            self._collect_modules()

    @property
    def categories(self) -> Tuple[ModuleCategory, ...]:
        return tuple(category for category in ModuleCategory if category != ModuleCategory.UNAVAILABLE)

    @property
    def modules(self) -> ModulesCollection:
        self._collect_modules_if_needed()
        return self._modules.copy()

    @property
    def graph(self) -> ImportGraph:
        self._collect_modules_if_needed()
        return self._graph.copy()

    @property
    def stdlib(self) -> ModuleDict:
        self._collect_modules_if_needed()
        return self._modules[ModuleCategory.STDLIB].copy()

    @property
    def external(self) -> ModuleDict:
        self._collect_modules_if_needed()
        return self._modules[ModuleCategory.EXTERNAL].copy()

    @property
    def internal(self) -> ModuleDict:
        self._collect_modules_if_needed()
        return self._modules[ModuleCategory.INTERNAL].copy()

    @classmethod
    def default_config(cls) -> ModulesCollectorConfig:
        return ModulesCollectorConfig()

    def clear(self) -> None:
        self._graph.clear()
        self._initialize_modules_collection()

    def get_category(self, module: Union[str, ModuleSpec, Module]) -> ModuleCategory:
        if isinstance(module, ModuleSpec):
            module = module.name

        if isinstance(module, str):
            module = self[module]

        elif not isinstance(module, Module):
            raise TypeError(f"Unsupported module type: {type(module)}")

        return module.get_category(self._project_root)

    def _initialize_modules_collection(self) -> ModulesCollection:
        return {category: {} for category in self.categories}

    def _collect_pkg_modules(self) -> Dict[str, pkgutil.ModuleInfo]:
        return {module.name: module for module in pkgutil.iter_modules()}

    def _update_graph(self, module: Module, parent: Optional[Module] = None) -> None:
        self._graph.add_node(module)
        if parent:
            self._graph.add_edge(parent, module)

    def _add_module(
        self,
        name: str,
        package: Optional[str] = None,
        parent: Optional[Module] = None,
    ) -> None:
        module_wrapper = self._get_module(name, package=package)
        if not module_wrapper:
            return

        _, module, category = module_wrapper
        self._modules[category][name] = module
        self._update_graph(module, parent)
        self._add_submodules(module_wrapper, package=name)

    def _add_submodules(
        self,
        wrapper: ModuleWrapper,
        package: Optional[str] = None,
    ) -> None:
        spec, parent, _ = wrapper
        if not spec.submodule_search_locations:
            return

        for location in spec.submodule_search_locations:
            self._add_submodules_from_files(location, parent, package=package)

    def _add_submodules_from_files(
        self,
        location: str,
        parent: Module,
        package: Optional[str] = None,
    ) -> None:
        origin = resolve_path(location)
        files = list(origin.glob("*.py"))
        for path in files:
            import_path = ImportPath.from_path(path, origin.parent)
            if import_path is None:
                logger.warning("Could not determine import path for %s", path)
                continue

            self._add_submodule_from_file(import_path, parent, package=package)

    def _add_submodule_from_file(self, import_path: ImportPath, parent: Module, package: Optional[str] = None) -> None:
        name = str(import_path)
        self._add_module(name, package=package, parent=parent)

    def _get_module(self, name: str, package: Optional[str] = None) -> Optional[ModuleWrapper]:
        spec = find_module_spec(name, package=package)
        if not spec:
            logger.warning("Module '%s' not found", name)
            return None

        if not spec.origin:
            raise FileNotFoundError(f"Module '{name}' has no origin path")

        if spec.origin == OriginType.FROZEN:
            logger.debug("Skipping frozen module: %s", name)
            return None

        if spec.origin == OriginType.BUILT_IN:
            logger.debug("Skipping built-in module: %s", name)
            return None

        origin = resolve_path(spec.origin)
        if origin.suffix.lower() != ".py":
            logger.debug("Module %s has non-Python origin: %s", name, origin)

        module = Module.from_spec(spec, package=package)
        category = module.get_category(self._project_root)
        if name in self._modules[category]:
            return None

        return ModuleWrapper(spec, module, category)

    def _collect_modules(self) -> None:
        self.clear()
        self._collect_external_modules()
        self._collect_internal_modules()

    def _collect_external_modules(self) -> None:
        for pkg_module in self._pkg_modules.values():
            name = pkg_module.name
            is_package = pkg_module.ispkg
            package = name if is_package else None
            self._add_module(name, package=package)

    def _collect_internal_modules(self) -> None:
        if not self._project_root:
            return

        for path in self._project_root.rglob("*.py"):
            import_path = ImportPath.from_path(path, self._project_root)
            if import_path is None:
                logger.warning("Could not determine import path for %s", path)
                continue

            self._add_module(str(import_path), package=self._package)
