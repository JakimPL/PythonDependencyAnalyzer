from collections.abc import Iterable
from pathlib import Path
from typing import Optional, Set, TypeAlias, Union, override

from anytree import PostOrderIter

from pda.models.paths.builder import build_path_tree
from pda.models.paths.graph import PathGraph
from pda.models.paths.node import PathNode
from pda.structures import Forest
from pda.tools.paths import filter_subdirectories
from pda.types import Pathlike

Paths: TypeAlias = Union[
    Iterable[Pathlike],
    Iterable[PathNode],
]


class PathForest(Forest[Pathlike, PathNode]):
    """
    Wraps a filesystem structure as a tree of PathNodes
    for Python package file structure analysis.
    """

    def __init__(self, nodes: Paths) -> None:
        super().__init__(self._to_nodes(nodes))
        self._populate_package_info()

    @override
    def __getitem__(self, path: Pathlike) -> PathNode:
        path = Path(path).resolve()
        return self._mapping[path]

    def _to_nodes(self, items: Paths) -> Set[PathNode]:
        if all(isinstance(item, PathNode) for item in items):
            return {item for item in items if item.is_dir}  # type: ignore[misc,union-attr]

        if not all(isinstance(item, (str, Path)) for item in items):
            raise TypeError("All items must be either str or Path instances, or all must be PathNode instances")

        nodes: Set[PathNode] = set()
        paths = filter_subdirectories(items)
        for path in paths:
            root = build_path_tree(path)
            if root is not None:
                nodes.add(root)

        return nodes

    @override
    def get(self, item: Pathlike) -> Optional[PathNode]:
        path = Path(item).resolve()
        return self._mapping.get(path)

    def get_python_files(self) -> Set[Path]:
        files: Set[Path] = set()
        for root in self._roots:
            self._collect_python_files(root, files)

        return files

    def _collect_python_files(self, node: PathNode, files: Set[Path]) -> None:
        if node.is_python_file:
            files.add(node.filepath)

        child: PathNode
        for child in node.children:
            self._collect_python_files(child, files)

    def _populate_package_info(self) -> None:
        node: PathNode
        for root in self._roots:
            for node in PostOrderIter(root):
                if node.is_dir:
                    node.mark_as_package_if_applicable()

    @property
    def graph(self) -> PathGraph:
        return PathGraph(self.nx)
