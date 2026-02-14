import json
from typing import Any, Dict, Generic, Iterator, List, Optional, Self, Union

import networkx as nx
from pyvis.network import Network

from pda.graph.types import Edge, NodeT
from pda.nodes import BaseForest
from pda.tools import logger


class Graph(Generic[NodeT]):
    """
    Base graph class for Python Dependency Analyzer.
    """

    def __init__(self, graph: Optional[nx.DiGraph] = None) -> None:
        self._graph = self._sort_if_possible(graph or nx.DiGraph())

    def __iter__(self) -> Iterator[NodeT]:
        return iter(self._graph.nodes)

    def __len__(self) -> int:
        return int(self._graph.number_of_nodes())

    def clear(self) -> None:
        self._graph.clear()

    def copy(self) -> Self:
        cls = self.__class__
        return cls(graph=self._graph.copy())

    @property
    def nodes(self) -> List[NodeT]:
        return list(self._graph.nodes)

    @property
    def edges(self) -> List[Edge[NodeT]]:
        return list(self._graph.edges)

    def has_node(self, module: NodeT) -> bool:
        return bool(self._graph.has_node(module))

    def has_edge(self, from_module: NodeT, to_module: NodeT) -> bool:
        return bool(self._graph.has_edge(from_module, to_module))

    def add_node(self, module: NodeT, level: int = 0) -> None:
        if not self.has_node(module):
            self._graph.add_node(module, level=level)

    def add_edge(self, from_module: NodeT, to_module: NodeT) -> None:
        if from_module != to_module and not self.has_edge(from_module, to_module):
            self.add_node(from_module)
            self.add_node(to_module)
            self._graph.add_edge(from_module, to_module)

    def label(self, node: NodeT) -> str:
        return str(node)

    def level(self, node: NodeT) -> int:
        return int(self._graph.nodes[node].get("level", 0))

    def group(self, node: NodeT) -> Optional[str]:
        return None

    def edge_label(self, from_node: NodeT, to_node: NodeT) -> str:
        from_label = self.label(from_node)
        to_label = self.label(to_node)
        return f"{from_label} → {to_label}"

    @property
    def empty(self) -> bool:
        return len(self) == 0

    @property
    def has_cycles(self) -> bool:
        return not nx.is_directed_acyclic_graph(self._graph)

    def find_cycle(self) -> Optional[List[NodeT]]:
        try:
            cycle: List[Edge[NodeT]] = nx.find_cycle(self._graph)
            return [cycle[0][0]] + [edge[1] for edge in cycle]
        except nx.NetworkXNoCycle:
            return None

    def find_cycles(self) -> List[List[NodeT]]:
        if self.has_cycles:
            return [list(cycle) for cycle in nx.simple_cycles(self._graph)]

        return []

    def sort_if_possible(self) -> None:
        self._graph = self._sort_if_possible(self._graph)

    @classmethod
    def from_forest(cls, forest: BaseForest[Any, NodeT, Any]) -> Self:
        return cls(graph=forest.graph)

    def to_pyvis(
        self,
        *,
        options: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Network:
        self.sort_if_possible()
        pyvis_graph = Network(directed=True, **kwargs)
        node_map: Dict[NodeT, int] = {}
        for i, node in enumerate(self):
            node_map[node] = i
            label: str = self.label(node)
            group: Optional[str] = self.group(node)
            level: int = self.level(node)
            pyvis_graph.add_node(
                i,
                label=label,
                title=label,
                level=level,
                group=group,
            )

        for from_node, to_node in self.edges:
            pyvis_graph.add_edge(
                node_map[from_node],
                node_map[to_node],
                title=self.edge_label(from_node, to_node),
            )

        if options:
            if isinstance(options, dict):
                options = json.dumps(options)

            pyvis_graph.set_options(options)

        return pyvis_graph

    @staticmethod
    def _sort_if_possible(graph: nx.DiGraph) -> nx.DiGraph:
        if not nx.is_directed_acyclic_graph(graph):
            logger.debug("Graph has cycles, skipping topological sort")
            return graph

        return Graph._sort(graph)

    @staticmethod
    def _sort(graph: nx.DiGraph) -> nx.DiGraph:
        roots = [node for node in graph.nodes() if graph.in_degree(node) == 0]
        for node in nx.topological_sort(graph):
            if node in roots:
                graph.nodes[node]["level"] = 0
            else:
                graph.nodes[node]["level"] = (
                    max(graph.nodes[predecessor]["level"] for predecessor in graph.predecessors(node)) + 1
                )

        return graph
