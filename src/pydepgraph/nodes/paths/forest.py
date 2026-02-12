from pathlib import Path
from typing import Optional, Set

from pydepgraph.nodes.base import BaseForest
from pydepgraph.nodes.paths.node import PathNode
from pydepgraph.tools.paths import is_dir, iterdir


class PathForest(BaseForest[Path, Path, PathNode]):
    """
    Wraps a filesystem structure as a tree of PathNodes
    for Python package file structure analysis.
    """

    def _build_tree(
        self,
        item: Path,
        parent: Optional[PathNode] = None,
    ) -> None:
        node = self._add_node(item, parent=parent)
        if node is None:
            return

        if parent is None:
            self._roots.add(node)

        if is_dir(item):
            return

        paths = iterdir(item)
        for path in paths:
            if path.name.startswith(".") or path.name == "__pycache__":
                continue

            self._build_tree(path, parent=node)

    def _create_node(
        self,
        item: Path,
        parent: Optional[PathNode] = None,
    ) -> PathNode:
        return PathNode(item, parent=parent)

    def _prepare_input(self, inp: Path) -> Path:
        return inp.resolve()

    def is_package(self, path: Path) -> bool:
        node = self.get(path)
        return node.is_package() if node else False

    def get_python_files(self, root: Path) -> Set[Path]:
        node = self.get(root)
        if not node:
            return set()

        files: Set[Path] = set()
        self._collect_python_files(node, files)
        return files

    def _collect_python_files(self, node: PathNode, files: Set[Path]) -> None:
        if node.is_python_file:
            files.add(node.path)

        for child in node.children:
            self._collect_python_files(child, files)
