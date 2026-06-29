import warnings
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Optional, Tuple, Union, overload

from pda.analyzer.base import BaseAnalyzer
from pda.analyzer.depth import CategoryContext, CategoryDepthPolicy
from pda.analyzer.lazy import lazy_execution
from pda.analyzer.modules.creator import ModuleCreator
from pda.analyzer.modules.pkg import PkgModuleScanner
from pda.analyzer.modules.scanner import FileSystemScanner
from pda.config import ModulesCollectorConfig
from pda.exceptions import PDACategoryDisabledWarning
from pda.models import ModuleGraph, ModuleNode
from pda.resolution import ModuleResolutionService, TargetEnvironment
from pda.specification import (
    CategorizedModule,
    CategorizedModuleDict,
    ImportPath,
    Module,
    ModuleCategory,
    ModulesCollection,
)
from pda.tools.logger import logger
from pda.tools.paths import resolve_path
from pda.types import Pathlike


class ModulesCollector(BaseAnalyzer[ModulesCollectorConfig, ModuleGraph]):
    config: ModulesCollectorConfig

    def __init__(
        self,
        config: ModulesCollectorConfig,
        project_root: Optional[Pathlike] = None,
        package: Optional[str] = None,
    ) -> None:
        super().__init__(config=config, project_root=project_root, package=package)

        self._collection: ModulesCollection = ModulesCollection(allow_unavailable=False)
        self._graph: ModuleGraph = ModuleGraph()

        self._creator: ModuleCreator = ModuleCreator(project_root=self._project_root)
        self._pkg_scanner: PkgModuleScanner = PkgModuleScanner(config=self.config.module_scan)
        self._fs_scanner: FileSystemScanner = FileSystemScanner(project_root=self._project_root)
        self._resolver: Optional[ModuleResolutionService] = (
            ModuleResolutionService(TargetEnvironment.create((self._project_root,)))
            if self._project_root is not None
            else None
        )
        self._depth_policy: CategoryDepthPolicy = CategoryDepthPolicy(
            self.config.stdlib_depth,
            self.config.external_depth,
        )

    def __bool__(self) -> bool:
        return bool(self._collection)

    @overload
    def __getitem__(self, key: ModuleCategory) -> CategorizedModuleDict: ...

    @overload
    def __getitem__(self, key: str) -> CategorizedModule: ...

    def __getitem__(self, key: Union[str, ModuleCategory]) -> Union[CategorizedModule, CategorizedModuleDict]:
        return self._collection[key]

    def _analyze_if_needed(self, *, refresh: bool = False) -> ModuleGraph:
        if refresh or not self:
            self._collect_modules()

        return self._graph

    @property
    @lazy_execution
    def collection(self) -> ModulesCollection:
        return self._collection.copy()

    @property
    def categories(self) -> Tuple[ModuleCategory, ...]:
        return self._collection.categories

    @property
    @lazy_execution
    def modules(self) -> CategorizedModuleDict:
        return self._collection.modules

    @property
    @lazy_execution
    def graph(self) -> ModuleGraph:
        return self._graph.copy()

    @property
    @lazy_execution
    def stdlib(self) -> CategorizedModuleDict:
        if self.config.stdlib_depth == 0:
            warnings.warn(
                "Accessing 'stdlib' category while 'stdlib_depth' is 0. This category will be empty.",
                PDACategoryDisabledWarning,
            )

        return self._collection.stdlib

    @property
    @lazy_execution
    def external(self) -> CategorizedModuleDict:
        if self.config.external_depth == 0:
            warnings.warn(
                "Accessing 'external' category while 'external_depth' is 0. This category will be empty.",
                PDACategoryDisabledWarning,
            )

        return self._collection.external

    @property
    @lazy_execution
    def local(self) -> CategorizedModuleDict:
        if self.project_root is None:
            warnings.warn(
                "Accessing 'local' category while 'project_root' is None. This category will be empty.",
                PDACategoryDisabledWarning,
            )

        return self._collection.local

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

    def _collect_modules(self) -> None:
        self.clear()
        self._collect_local_modules()
        self._collect_external_modules()
        if self.config.collapse_level is not None:
            self._graph = self._graph.simplify(
                self.config.collapse_level,
                qualified_name=self.config.qualified_names,
                sort_method="auto",
            )
        if not self:
            logger.warning("No modules collected. Check your configuration and project structure")

    def _collect_external_modules(self) -> None:
        discovered_modules = self._pkg_scanner.discover()
        for module_info in discovered_modules:
            self._add_module(
                name=module_info.name,
                base_path=module_info.base_path,
                package=module_info.package,
                parent_context=CategoryContext.root(),
            )

    def _collect_local_modules(self) -> None:
        if not self._project_root:
            return

        self._add_submodules_from_files(
            location=self._project_root,
            base_path=self._project_root,
            package=self._package,
            parent_context=CategoryContext.root(),
        )

    def _add_submodules_from_files(
        self,
        location: Pathlike,
        base_path: Path,
        *,
        parent: Optional[ModuleNode] = None,
        package: Optional[str] = None,
        level: int = 0,
        parent_context: CategoryContext,
    ) -> None:
        max_depth = self.config.max_depth
        if max_depth is not None and level > max_depth:
            return

        origin = resolve_path(location)
        if not origin:
            return

        for filepath in self._fs_scanner.get_submodule_paths(origin):
            import_path = self._fs_scanner.path_to_import_path(filepath, base_path)
            if import_path is None:
                continue

            self._add_module(
                import_path,
                base_path,
                origin=filepath,
                package=package,
                parent=parent,
                level=level,
                parent_context=parent_context,
            )

    def _add_module(
        self,
        name: Union[str, ImportPath],
        base_path: Path,
        *,
        package: Optional[str] = None,
        parent: Optional[ModuleNode] = None,
        level: int = 0,
        origin: Optional[Pathlike] = None,
        parent_context: CategoryContext,
    ) -> None:
        name = str(name)
        module = self._get_module(name, package=package, origin=origin)

        if not module:
            return

        if self.config.hide_unavailable and not module.available:
            return

        context = self._depth_policy.descend(parent_context, module.category)
        if not self._depth_policy.should_include(context):
            return

        if self.config.hide_private and module.is_private:
            return

        node = ModuleNode(module, level=level, qualified_name=self.config.qualified_names)
        self._add(node, parent)
        if self._depth_policy.should_recurse(context):
            self._add_submodules(
                node,
                base_path,
                package=name,
                level=level + 1,
                parent_context=context,
            )

    def _add(self, node: ModuleNode, parent: Optional[ModuleNode] = None) -> None:
        self._graph.add_node(node)
        self._collection.add(node.module)
        if parent is not None:
            self._graph.add_edge(parent, node)

    def _add_submodules(
        self,
        node: ModuleNode,
        base_path: Path,
        *,
        package: Optional[str] = None,
        level: int = 0,
        parent_context: CategoryContext,
    ) -> None:
        spec = node.module.spec
        if not spec or not spec.submodule_search_locations:
            return

        for location in spec.submodule_search_locations:
            self._add_submodules_from_files(
                location,
                base_path=base_path,
                parent=node,
                package=package,
                level=level,
                parent_context=parent_context,
            )

    def _get_module(
        self,
        name: str,
        package: Optional[str] = None,
        origin: Optional[Pathlike] = None,
    ) -> Optional[CategorizedModule]:
        if name in self._collection:
            return None

        if origin is not None and self._resolver is not None:
            resolution = self._resolver.resolve_filesystem_path(origin, source_root=self._project_root)
            module = self._resolver.to_categorized_module(resolution, package=package)
        else:
            module = self._creator.create_module(name, package=package)

        category = module.category
        if name in self._collection[category]:
            return None

        return module

    @classmethod
    def default_config(cls) -> ModulesCollectorConfig:
        return ModulesCollectorConfig()
