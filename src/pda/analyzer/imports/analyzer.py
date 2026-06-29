from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import (
    Deque,
    FrozenSet,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
    overload,
    override,
)

from pda.analyzer.base import BaseAnalyzer, register_search_path
from pda.analyzer.depth import CategoryContext, CategoryDepthPolicy
from pda.analyzer.imports.parser import ImportStatementParser
from pda.analyzer.imports.report import build_cycle_report, format_cycle_report
from pda.analyzer.imports.resolver import ImportResolver
from pda.analyzer.lazy import lazy_execution
from pda.analyzer.target import AnalysisTarget
from pda.config import ModuleImportsAnalyzerConfig
from pda.exceptions import PDADependencyCycleError
from pda.models import ModuleGraph, ModuleNode, gather_python_files
from pda.resolution import ProjectResolutionContext
from pda.specification import (
    CategorizedModule,
    CategorizedModuleDict,
    ImportPath,
    ImportScope,
    ImportStatement,
    ModuleCategory,
    ModulesCollection,
    ModuleSource,
    OriginType,
)
from pda.structures import OrderedSet
from pda.tools.logger import logger
from pda.types import Pathlike


class PendingNode(NamedTuple):
    """A node awaiting traversal in the import graph BFS, with its accumulated state."""

    node: ModuleNode
    depth: int
    context: CategoryContext


class ModuleImportsAnalyzer(BaseAnalyzer[ModuleImportsAnalyzerConfig, ModuleGraph]):
    config: ModuleImportsAnalyzerConfig

    def __init__(
        self,
        config: ModuleImportsAnalyzerConfig,
        project_root: Pathlike,
        root_module_name: str,
        *,
        source_roots: Optional[Tuple[Pathlike, ...]] = None,
        local_boundary: Optional[Pathlike] = None,
    ) -> None:
        analysis_target = AnalysisTarget(root_module_name=root_module_name)
        super().__init__(
            config=config,
            project_root=project_root,
            analysis_target=analysis_target,
        )

        if not self._project_root:
            raise ValueError("Project root must be provided")

        self._project_context = ProjectResolutionContext.create(
            self._project_root,
            source_roots=source_roots,
            local_boundary=local_boundary,
        )
        for source_root in self._project_context.source_roots:
            register_search_path(source_root)

        self._files: Optional[List[Path]] = None
        self._root_origins: FrozenSet[Optional[Path]] = frozenset()
        self._collection: ModulesCollection = ModulesCollection(allow_unavailable=True)
        self._graph: ModuleGraph = ModuleGraph()
        self._parser: ImportStatementParser = ImportStatementParser()
        self._resolver: ImportResolver = ImportResolver(
            project_context=self._project_context,
            analysis_target=analysis_target,
            config=config,
        )
        self._depth_policy: CategoryDepthPolicy = CategoryDepthPolicy(
            self.config.stdlib_depth,
            self.config.external_depth,
        )

        self._counter = 0

    def __bool__(self) -> bool:
        return not self._graph.empty

    @override
    def __call__(
        self,
        paths: Union[Pathlike, Iterable[Pathlike], None] = None,
        *,
        refresh: bool = False,
    ) -> ModuleGraph:
        result = self._analyze_if_needed(paths=paths, refresh=refresh)
        self._check_graph()
        return result

    @overload
    def __getitem__(self, key: ModuleCategory) -> CategorizedModuleDict: ...

    @overload
    def __getitem__(self, key: str) -> CategorizedModule: ...

    def __getitem__(self, key: Union[str, ModuleCategory]) -> Union[CategorizedModule, CategorizedModuleDict]:
        return self._collection[key]

    def clear(self) -> None:
        self._files = None
        self._root_origins = frozenset()
        self._collection.clear()
        self._graph.clear()
        self._counter = 0

    @property
    def filepaths(self) -> List[Path]:
        return list(self._files) if self._files is not None else []

    @property
    def source_roots(self) -> Tuple[Path, ...]:
        return self._project_context.source_roots

    @property
    @lazy_execution
    def modules(self) -> CategorizedModuleDict:
        return self._collection.modules

    @property
    @lazy_execution
    def graph(self) -> ModuleGraph:
        return self._graph.copy()

    def _analyze_if_needed(
        self,
        paths: Union[Pathlike, Iterable[Pathlike], None] = None,
        *,
        refresh: bool = False,
    ) -> ModuleGraph:
        files = gather_python_files(paths) if paths is not None else self._files
        if not files:
            raise ValueError("No modules have been analyzed yet")

        if refresh or not self or self._files != files:
            self._create_graph(files)

        return self._graph

    def _create_graph(self, paths: List[Path]) -> None:
        self.clear()
        self._files = paths

        roots = [self._resolver.create_root(path) for path in paths]
        self._root_origins = frozenset(root.module.origin for root in roots)

        processed: Set[Optional[Path]] = {None}
        new_nodes: Deque[PendingNode] = deque()
        for root in roots:
            self._add(root)
            new_nodes.append(PendingNode(root, 0, CategoryContext.root()))

        while new_nodes:
            node, depth, context = new_nodes.pop()
            is_root = node.module.origin in self._root_origins
            module = node.module
            if self._check_if_should_process_module(
                module,
                processed=processed,
                depth=depth,
            ):
                self._collect_new_modules(
                    node,
                    new_nodes,
                    processed=processed,
                    is_root=is_root,
                    depth=depth,
                    context=context,
                )

        if self.config.collapse_level is not None:
            self._graph = self._graph.simplify(
                self.config.collapse_level,
                qualified_name=self.config.qualified_names,
                sort_method=self.config.sort_method,
            )
        else:
            self._graph.sort(method=self.config.sort_method)

        self._graph.annotate_cycles()

    def _check_graph(self) -> None:
        if self._graph.empty:
            logger.warning("The dependency graph is empty")
            return

        if not self._graph.has_cycles:
            return

        report = build_cycle_report(
            self._graph,
            length_bound=self.config.cycle_length_bound,
            max_examples=self.config.cycle_examples,
        )
        summary = format_cycle_report(report)
        if self.config.fail_on_cycle:
            raise PDADependencyCycleError(summary)

        logger.warning("%s", summary)

    def _add(self, node: ModuleNode, parent: Optional[ModuleNode] = None) -> None:
        self._graph.add_node(node)
        self._collection.add(node.module)
        if parent is not None:
            self._graph.add_edge(parent, node)

    def analyze_file(
        self,
        filepath: Path,
        base_path: Path,
        *,
        is_root: bool = False,
    ) -> CategorizedModuleDict:
        """
        Analyze a Python file to extract all imported module paths,
        and return their corresponding file paths.
        """
        module_source = ModuleSource(
            origin=filepath,
            base_path=base_path,
        )

        import_paths = self._collect_imports(module_source, is_root=is_root)
        return self._resolver.resolve_batch(module_source, import_paths)

    def analyze_module(
        self,
        module: CategorizedModule,
        *,
        processed: Optional[Set[Optional[Path]]] = None,
        is_root: bool = False,
        context: Optional[CategoryContext] = None,
    ) -> CategorizedModuleDict:
        """
        Analyze a module to extract all imported module paths,
        and return their corresponding file paths.
        """
        if not self._check_if_should_scan(module, processed=processed, context=context):
            return {}

        if module.base_path is None:
            return {}

        assert module.origin is not None
        return self.analyze_file(
            module.origin,
            module.base_path,
            is_root=is_root,
        )

    def _check_if_should_process_module(
        self,
        module: CategorizedModule,
        processed: Set[Optional[Path]],
        depth: int,
    ) -> bool:
        if module.origin in processed:
            return False

        max_depth = self.config.max_depth
        if max_depth is not None and depth > max_depth:
            return False

        return True

    def _check_if_should_scan(
        self,
        module: CategorizedModule,
        processed: Optional[Set[Optional[Path]]] = None,
        context: Optional[CategoryContext] = None,
    ) -> bool:
        if module.origin_type != OriginType.PYTHON:
            return False

        if not module.available:
            return False

        context = context or CategoryContext.root()
        if not self._depth_policy.should_recurse(context):
            return False

        if self.config.hide_private and module.is_private:
            return False

        assert module.origin is not None
        processed = processed or set()
        if module.origin in processed:
            return False

        return True

    def _collect_imports(
        self,
        module_source: ModuleSource,
        is_root: bool = False,
    ) -> List[ImportPath]:
        import_statements = self._collect_import_statements(module_source.origin)
        import_paths = self._filter_runtime_import_paths(import_statements, is_root=is_root)
        return self._resolve_import_paths(module_source, import_paths)

    def _collect_import_statements(
        self,
        origin: Path,
    ) -> List[ImportStatement]:
        return self._parser(origin)

    def _filter_runtime_import_paths(
        self,
        import_statements: List[ImportStatement],
        *,
        is_root: bool = False,
    ) -> List[ImportPath]:
        import_paths: OrderedSet[ImportPath] = OrderedSet()

        for statement in import_statements:
            if statement.in_scope(ImportScope.MAIN) and not is_root:
                continue

            if statement.in_scope(ImportScope.TYPE_CHECKING):
                continue

            if not self.config.follow_conditional:
                if statement.in_scope(ImportScope.ERROR_HANDLING):
                    continue

            if statement.in_scope(ImportScope.FUNCTION) and not statement.in_scope(ImportScope.DECORATED_FUNCTION):
                continue

            import_paths.add(statement.path.get_module_path())

        return list(import_paths)

    def _collect_new_modules(
        self,
        node: ModuleNode,
        new_nodes: Deque[PendingNode],
        *,
        processed: Set[Optional[Path]],
        is_root: bool = False,
        depth: int = 0,
        context: Optional[CategoryContext] = None,
    ) -> None:
        context = context or CategoryContext.root()
        imported_modules = self.analyze_module(
            node.module,
            processed=processed,
            is_root=is_root,
            context=context,
        )

        processed.add(node.module.origin)
        for imported_module in imported_modules.values():
            child_context = self._depth_policy.descend(
                context,
                imported_module.category,
            )
            if (
                (self.config.hide_private and imported_module.is_private)
                or (self.config.hide_unavailable and not imported_module.available)
                or (not self._depth_policy.should_include(child_context))
                or (node.module.name == imported_module.name)
            ):
                continue

            level = depth + 1
            child = ModuleNode(
                imported_module,
                level=level,
                ordinal=self._ordinal(),
                qualified_name=self.config.qualified_names,
            )
            self._add(child, parent=node)

            if self.config.unify_nodes and imported_module.origin in processed:
                continue

            new_nodes.append(
                PendingNode(
                    child,
                    level,
                    child_context,
                )
            )

    def _resolve_import_paths(
        self,
        module_source: ModuleSource,
        import_paths: List[ImportPath],
    ) -> List[ImportPath]:
        return [
            path
            for import_path in import_paths
            if (path := self._resolver.resolve_import_path(module_source, import_path)) is not None
        ]

    def _ordinal(self) -> int:
        if self.config.unify_nodes:
            return 0

        self._counter += 1
        return self._counter

    @classmethod
    def default_config(cls) -> ModuleImportsAnalyzerConfig:
        return ModuleImportsAnalyzerConfig()
