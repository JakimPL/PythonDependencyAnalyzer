import warnings
from pathlib import Path
from typing import Optional, Tuple, Union, overload

from pda.analyzer.base import BaseAnalyzer, register_search_path
from pda.analyzer.depth import CategoryContext, CategoryDepthPolicy
from pda.analyzer.lazy import lazy_execution
from pda.analyzer.modules.lookup import (
    ModuleLookup,
    ProjectModuleLookup,
    RuntimeModuleLookup,
)
from pda.analyzer.modules.pkg import PkgModuleScanner
from pda.analyzer.modules.scanner import FileSystemScanner
from pda.analyzer.target import AnalysisTarget, AnalysisTargetResolver
from pda.config import ModulesCollectorConfig
from pda.exceptions import PDACategoryDisabledWarning
from pda.models import ModuleGraph, ModuleNode
from pda.resolution import ProjectResolutionContext
from pda.resolution.paths import longest_containing_root, module_base_path_from_search_location
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
        root_module_name: Optional[str] = None,
        *,
        source_roots: Optional[Tuple[Pathlike, ...]] = None,
        local_boundary: Optional[Pathlike] = None,
    ) -> None:
        analysis_target = AnalysisTarget(root_module_name=root_module_name) if root_module_name is not None else None
        super().__init__(config=config, project_root=project_root, analysis_target=analysis_target)

        self._collection: ModulesCollection = ModulesCollection(allow_unavailable=False)
        self._graph: ModuleGraph = ModuleGraph()
        self._project_context: Optional[ProjectResolutionContext] = None

        self._source_roots, self._module_lookup = self._create_source_roots_and_lookup(
            source_roots=source_roots,
            local_boundary=local_boundary,
        )
        self._pkg_scanner: PkgModuleScanner = PkgModuleScanner(config=self.config.module_scan)
        self._fs_scanner: FileSystemScanner = FileSystemScanner(
            project_root=self._project_root,
            source_roots=self._source_roots or None,
        )
        self._depth_policy: CategoryDepthPolicy = CategoryDepthPolicy(
            self.config.stdlib_depth,
            self.config.external_depth,
        )

    def _create_source_roots_and_lookup(
        self,
        *,
        source_roots: Optional[Tuple[Pathlike, ...]],
        local_boundary: Optional[Pathlike],
    ) -> Tuple[Tuple[Path, ...], ModuleLookup]:
        if self._project_root is None:
            if source_roots is not None or local_boundary is not None:
                raise ValueError("source_roots and local_boundary require a project_root")

            return (), RuntimeModuleLookup.create()

        if self._analysis_target is None:
            raise ValueError("root_module_name is required when project_root is provided")

        context = ProjectResolutionContext.create(
            self._project_root,
            source_roots=source_roots,
            local_boundary=local_boundary,
        )
        self._project_context = context
        for source_root in context.source_roots:
            register_search_path(source_root)

        return context.source_roots, ProjectModuleLookup.create(context)

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

    def get_category(
        self,
        module: Union[str, Module, CategorizedModule],
    ) -> ModuleCategory:
        if isinstance(module, str):
            module = self[module]

        elif not isinstance(module, (Module, CategorizedModule)):
            raise TypeError(f"Unsupported module type: {type(module)}, expected str, Module, or CategorizedModule")

        if isinstance(module, CategorizedModule):
            return module.category

        return self._module_lookup.category(module)

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
                containing_package=module_info.containing_package,
                parent_context=CategoryContext.root(),
            )

    def _collect_local_modules(self) -> None:
        if not self._source_roots:
            return

        assert self._analysis_target is not None
        assert self._project_context is not None
        resolved_target = AnalysisTargetResolver(self._project_context).resolve(self._analysis_target)
        self._add_module(
            name=resolved_target.target.root_module_name,
            base_path=None,
            containing_package=None,
            parent_context=CategoryContext.root(),
        )

    def _add_submodules_from_files(
        self,
        location: Pathlike,
        base_path: Path,
        *,
        parent: Optional[ModuleNode] = None,
        containing_package: Optional[str] = None,
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
            import_path = self._fs_scanner.path_to_import_path(
                filepath,
                base_path,
            )
            if import_path is None:
                continue

            self._add_module(
                import_path,
                base_path,
                origin=filepath,
                containing_package=containing_package,
                parent=parent,
                level=level,
                parent_context=parent_context,
            )

    def _add_module(
        self,
        name: Union[str, ImportPath],
        base_path: Optional[Path],
        *,
        containing_package: Optional[str] = None,
        parent: Optional[ModuleNode] = None,
        level: int = 0,
        origin: Optional[Pathlike] = None,
        parent_context: CategoryContext,
    ) -> None:
        name = str(name)
        module = self._get_module(
            name,
            containing_package=containing_package,
            origin=origin,
        )

        if not module:
            return

        if self.config.hide_unavailable and not module.available:
            return

        context = self._depth_policy.descend(parent_context, module.category)
        if not self._depth_policy.should_include(context):
            return

        if self.config.hide_private and module.is_private:
            return

        node = ModuleNode(
            module,
            level=level,
            qualified_name=self.config.qualified_names,
        )
        self._add(node, parent)
        if self._depth_policy.should_recurse(context):
            module_base_path = base_path or module.base_path
            if module_base_path is None:
                return

            self._add_submodules(
                node,
                fallback_base_path=module_base_path,
                containing_package=name,
                level=level + 1,
                parent_context=context,
            )

    def _add(
        self,
        node: ModuleNode,
        parent: Optional[ModuleNode] = None,
    ) -> None:
        self._graph.add_node(node)
        self._collection.add(node.module)
        if parent is not None:
            self._graph.add_edge(parent, node)

    def _add_submodules(
        self,
        node: ModuleNode,
        *,
        fallback_base_path: Path,
        containing_package: Optional[str] = None,
        level: int = 0,
        parent_context: CategoryContext,
    ) -> None:
        locations = node.module.submodule_search_locations
        if not locations:
            return

        for location in locations:
            if not self._should_scan_package_location(node.module, location):
                continue

            base_path = module_base_path_from_search_location(node.module.name, location) or fallback_base_path
            self._add_submodules_from_files(
                location,
                base_path=base_path,
                parent=node,
                containing_package=containing_package,
                level=level,
                parent_context=parent_context,
            )

    def _get_module(
        self,
        name: str,
        containing_package: Optional[str] = None,
        origin: Optional[Pathlike] = None,
    ) -> Optional[CategorizedModule]:
        if name in self._collection:
            return None

        if origin is not None:
            module = self._module_lookup.filesystem_module(origin)
        else:
            module = self._module_lookup.discovered_module(
                name,
                containing_package=containing_package,
            )

        category = module.category
        if name in self._collection[category]:
            return None

        return module

    def _should_scan_package_location(
        self,
        module: CategorizedModule,
        location: Path,
    ) -> bool:
        if module.category != ModuleCategory.LOCAL:
            return True

        return longest_containing_root(location, self._source_roots) is not None

    @classmethod
    def default_config(cls) -> ModulesCollectorConfig:
        return ModulesCollectorConfig()
