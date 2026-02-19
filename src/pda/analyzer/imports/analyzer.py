from __future__ import annotations

import warnings
from collections import deque
from copy import copy
from enum import Enum, auto
from pathlib import Path
from typing import Deque, Dict, List, Optional, Set, Tuple, Union, overload, override

from pda.analyzer.base import BaseAnalyzer
from pda.analyzer.imports.parser import ImportStatementParser
from pda.analyzer.lazy import lazy_execution
from pda.config import ModuleImportsAnalyzerConfig, ValidationOptions
from pda.exceptions import PDADependencyCycleWarning, PDAImportPathError, PDAMissingModuleSpecError
from pda.exceptions.analyzer import PDADependencyCycleError
from pda.models import ModuleGraph, ModuleNode
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
    SysPaths,
    UnavailableModule,
    is_namespace_package,
    validate_spec_origin,
)
from pda.structures import OrderedSet
from pda.tools.logger import logger
from pda.types import Pathlike


class NodeState(Enum):
    UNVISITED = auto()
    VISITING = auto()
    VISITED = auto()


class ModuleImportsAnalyzer(BaseAnalyzer[ModuleImportsAnalyzerConfig, ModuleGraph]):
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
        self._graph: ModuleGraph = ModuleGraph()
        self._parser: ImportStatementParser = ImportStatementParser()

        self._root_validation_options = ValidationOptions.strict()
        self._module_validation_options = ValidationOptions(
            allow_missing_spec=True,
            validate_origin=True,
            expect_python=False,
            raise_error=False,
        )

        self._counter = 0

        self._node_states: Dict[Optional[Path], NodeState] = {}
        self._cycle_detected: bool = False
        self._cycle_path: List[Path] = []

    def __bool__(self) -> bool:
        return not self._graph.empty

    @override
    def __call__(
        self,
        filepath: Optional[Path] = None,
        *,
        refresh: bool = False,
    ) -> ModuleGraph:
        result = self._analyze_if_needed(filepath=filepath, refresh=refresh)
        self._check_graph()
        return result

    @overload
    def __getitem__(self, key: ModuleCategory) -> CategorizedModuleDict: ...

    @overload
    def __getitem__(self, key: str) -> CategorizedModule: ...

    def __getitem__(self, key: Union[str, ModuleCategory]) -> Union[CategorizedModule, CategorizedModuleDict]:
        return self._collection[key]

    def clear(self) -> None:
        self._filepath = None
        self._collection.clear()
        self._graph.clear()
        self._counter = 0
        self._node_states.clear()
        self._cycle_detected = False
        self._cycle_path.clear()

    @property
    def filepath(self) -> Optional[Path]:
        return copy(self._filepath)

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
        filepath: Optional[Path] = None,
        *,
        refresh: bool = False,
    ) -> ModuleGraph:
        filepath = filepath or self._filepath
        if not filepath:
            raise ValueError("No module has been analyzed yet")

        if refresh or not self or self._filepath != filepath:
            self._create_graph(filepath)

        return self._graph

    def _create_graph(self, filepath: Path) -> None:
        self.clear()

        self._filepath = filepath
        root = self._create_root(filepath)
        self._add(root)

        processed: Set[Optional[Path]] = {None}
        new_nodes: Deque[Tuple[ModuleNode, int, List[Path]]] = deque([(root, 0, [])])
        self._node_states[root.module.origin] = NodeState.VISITING

        while new_nodes:
            node, depth, path = new_nodes.pop()
            is_root = node.module.origin == self._filepath
            module = node.module
            if self._check_if_should_process_module(
                module,
                processed=processed,
                depth=depth,
            ):
                current_path = path + [module.origin] if module.origin else path
                self._collect_new_modules(
                    node,
                    new_nodes,
                    processed=processed,
                    is_root=is_root,
                    depth=depth,
                    path=current_path,
                )

            self._node_states[module.origin] = NodeState.VISITED

        self._graph.sort(method=self.config.sort_method)

    def _detect_cycle_in_path(self, path: List[Path]) -> bool:
        if len(path) != len(set(path)):
            return True

        return False

    def _show_detected_cycle(self) -> None:
        paths = "\n-> ".join(str(path) for path in self._cycle_path)
        if not self.config.ignore_cycles:
            raise PDADependencyCycleError(f"Dependency cycle detected in path:\n{paths}")

        logger.warning("Cycle detected: %s", paths)

    def _check_graph(self) -> None:
        if self._graph.empty:
            logger.warning("The dependency graph is empty")

        if self._cycle_detected:
            message = "Import cycle detected during analysis:\n-> {}".format(
                "\n-> ".join(str(path) for path in self._cycle_path),
            )
            warnings.warn(message, PDADependencyCycleWarning)

    def _add(self, node: ModuleNode, parent: Optional[ModuleNode] = None) -> None:
        self._graph.add_node(node)
        self._collection.add(node.module)
        if parent is not None:
            self._graph.add_edge(parent, node)

    def analyze_file(
        self,
        filepath: Path,
        base_path: Path,
        package: str,
        *,
        processed: Optional[Set[Optional[Path]]] = None,
        is_root: bool = False,
    ) -> CategorizedModuleDict:
        """
        Analyze a Python file to extract all imported module paths,
        and return their corresponding file paths.
        """
        module_source = ModuleSource(
            origin=filepath,
            base_path=base_path,
            package=package,
            validation_options=self._module_validation_options,
        )

        import_paths = self._collect_imports(module_source, processed=processed, is_root=is_root)
        return self._collect_modules(module_source, import_paths)

    def analyze_module(
        self,
        module: CategorizedModule,
        *,
        processed: Optional[Set[Optional[Path]]] = None,
        is_root: bool = False,
    ) -> CategorizedModuleDict:
        """
        Analyze a module to extract all imported module paths,
        and return their corresponding file paths.
        """
        if not self._check_if_should_scan(module, processed=processed):
            return {}

        if module.base_path is None:
            return {}

        assert module.origin is not None
        return self.analyze_file(
            module.origin,
            module.base_path,
            module.top_level_module,
            processed=processed,
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
    ) -> bool:
        if module.origin_type != OriginType.PYTHON:
            return False

        category = module.category
        if not self.config.scan_stdlib and category == ModuleCategory.STDLIB:
            return False

        if not self.config.scan_external and category == ModuleCategory.EXTERNAL:
            return False

        if self.config.hide_unavailable and category == ModuleCategory.UNAVAILABLE:
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
        processed: Optional[Set[Optional[Path]]] = None,
        is_root: bool = False,
    ) -> List[ImportPath]:
        module_paths: OrderedSet[ImportPath] = OrderedSet()
        import_statements = self._collect_import_statements(module_source.origin)
        import_paths = self._filter_runtime_import_paths(import_statements, is_root=is_root)
        for import_path in import_paths:
            module_path = self._resolve(module_source, import_path, processed)
            if module_path is not None:
                module_paths.add(module_path)

        return list(module_paths)

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

    def _collect_modules(
        self,
        module_source: ModuleSource,
        module_paths: List[ImportPath],
    ) -> CategorizedModuleDict:
        modules: CategorizedModuleDict = {}
        for module_path in module_paths:
            module = self._get_module_from_import_path(module_source, module_path)
            modules[module.name] = module

        return modules

    def _get_module_from_import_path(
        self,
        module_source: ModuleSource,
        module_path: ImportPath,
    ) -> CategorizedModule:
        spec = module_source.get_spec(module_path)
        package_spec = module_source.get_package_spec(module_path)
        package = package_spec.name if package_spec is not None else None
        unavailable_module = CategorizedModule(
            module=UnavailableModule(
                name=module_path.module if module_path.module else "<unknown>",
                package=package,
            ),
            category=ModuleCategory.UNAVAILABLE,
        )

        if spec is None:
            logger.debug(
                "Module spec not found for import path '%s' (package: '%s')",
                module_path,
                package_spec.name if package_spec is not None else None,
            )
            return unavailable_module

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
        except PDAImportPathError as import_error:
            logger.debug(
                "Module '%s' import path error:\n%s: [%s]",
                spec.name,
                import_error.__class__.__name__,
                import_error,
            )

        return unavailable_module

    def _create_root(self, filepath: Path) -> ModuleNode:
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

        return ModuleNode(module, qualified_name=self.config.qualified_names)

    def _collect_new_modules(
        self,
        node: ModuleNode,
        new_nodes: Deque[Tuple[ModuleNode, int, List[Path]]],
        *,
        processed: Set[Optional[Path]],
        is_root: bool = False,
        depth: int = 0,
        path: Optional[List[Path]] = None,
    ) -> None:
        path = path or []
        imported_modules = self.analyze_module(
            node.module,
            processed=processed,
            is_root=is_root,
        )

        processed.add(node.module.origin)
        for imported_module in imported_modules.values():
            if (
                (self.config.unify_nodes and imported_module.origin in processed)
                or (self.config.hide_private and imported_module.is_private)
                or (self.config.hide_unavailable and imported_module.category == ModuleCategory.UNAVAILABLE)
                or (node.module.name == imported_module.name)
            ):
                continue

            if imported_module.origin in path:
                self._cycle_detected = True
                self._cycle_path = path + [imported_module.origin]
                self._show_detected_cycle()
                continue

            level = depth + 1
            child = ModuleNode(
                imported_module,
                level=level,
                ordinal=self._ordinal(),
                qualified_name=self.config.qualified_names,
            )

            current_path = path + [imported_module.origin] if imported_module.origin else path
            self._add(child, parent=node)
            self._node_states[imported_module.origin] = NodeState.VISITING
            new_nodes.append((child, level, current_path))

    def _ordinal(self) -> int:
        if self.config.unify_nodes:
            return 0

        self._counter += 1
        return self._counter

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

    @classmethod
    def default_config(cls) -> ModuleImportsAnalyzerConfig:
        return ModuleImportsAnalyzerConfig()
