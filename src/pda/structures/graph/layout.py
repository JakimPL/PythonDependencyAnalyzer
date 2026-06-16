from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, Optional, Tuple, TypeAlias

from pda.structures.graph.base import Graph
from pda.structures.node.types import NodeT

Position: TypeAlias = Tuple[float, float]


@dataclass
class LayoutResult(Generic[NodeT]):
    positions: Dict[NodeT, Position]
    node_options: Dict[NodeT, Dict[str, Any]] = field(default_factory=dict)
    vis_options_patch: Dict[str, Any] = field(default_factory=dict)


class GraphLayout(ABC, Generic[NodeT]):
    @abstractmethod
    def compute(self, graph: Graph[NodeT]) -> Optional[LayoutResult[NodeT]]: ...
