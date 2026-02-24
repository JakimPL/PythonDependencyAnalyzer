from abc import ABC
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Dict, Generic, Optional, Set

import networkx as nx
from anytree import LevelOrderIter

from pda.structures.node.types import AnyNodeT
from pda.types import HashableT

if TYPE_CHECKING:
    from pda.structures.graph.base import Graph


class Forest(ABC, Generic[HashableT, AnyNodeT]):
    def __init__(
        self,
        nodes: Iterable[AnyNodeT],
        *,
        detach_from_parents: bool = True,
    ) -> None:
        self._roots: Set[AnyNodeT] = self._find_top_level_nodes(nodes)
        if detach_from_parents:
            self._detach_roots_from_parents()

        self._mapping: Dict[HashableT, AnyNodeT] = self._get_node_mapping()

    @staticmethod
    def _find_top_level_nodes(nodes: Iterable[AnyNodeT]) -> Set[AnyNodeT]:
        return {node for node in set(nodes) if not any(ancestor in nodes for ancestor in node.ancestors)}

    def _get_node_mapping(self) -> Dict[HashableT, AnyNodeT]:
        return {node.item: node for node in self}

    def _detach_roots_from_parents(self) -> None:
        for root in self._roots:
            root.parent = None

    def __bool__(self) -> bool:
        return bool(self._roots)

    def __iter__(self) -> Iterator[AnyNodeT]:
        for root in self._roots:
            yield from LevelOrderIter(root)

    def __contains__(self, item: HashableT) -> bool:
        return item in self._mapping

    def __getitem__(self, item: HashableT) -> AnyNodeT:
        return self._mapping[item]

    def __len__(self) -> int:
        return sum(root.size for root in self._roots)

    def get(self, item: HashableT) -> Optional[AnyNodeT]:
        return self._mapping.get(item)

    @property
    def roots(self) -> Set[AnyNodeT]:
        return self._roots.copy()

    @property
    def nx(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for node in self:
            label: str = node.label
            level: int = node.depth
            graph.add_node(node, label=label, rank=level, level=level)
            if node.parent is not None:
                edge_label = self.edge_label(node.parent, node)
                graph.add_edge(node.parent, node, label=edge_label)

        return graph

    @property
    def graph(self) -> Graph[AnyNodeT]:
        from pda.structures.graph.base import Graph

        return Graph(graph=self.nx)

    def edge_label(self, from_node: AnyNodeT, to_node: AnyNodeT) -> str:
        from_label = from_node.label
        to_label = to_node.label
        return f"{from_label} → {to_label}"
