from typing import Any, Tuple, TypeAlias, TypeVar

from pda.structures.node.any import AnyNode
from pda.structures.node.base import Node

NodeT = TypeVar("NodeT", bound=Node[Any])
Edge: TypeAlias = Tuple[NodeT, NodeT]

AnyNodeT = TypeVar("AnyNodeT", bound=AnyNode[Any])
