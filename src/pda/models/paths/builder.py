from pathlib import Path
from typing import Optional

from pda.models.paths.node import PathNode
from pda.tools.paths import is_dir, iterdir
from pda.types import Pathlike


def to_path_node(path: Pathlike, parent: Optional[PathNode] = None) -> PathNode:
    return PathNode(Path(path).resolve(), parent=parent)


def build_path_tree(path: Pathlike, parent: Optional[PathNode] = None) -> Optional[PathNode]:
    node = to_path_node(path, parent=parent)
    if node is None:
        return None

    if not is_dir(node.filepath):
        return node

    children = iterdir(node.filepath)
    for child in children:
        build_path_tree(child, parent=node)

    return node
