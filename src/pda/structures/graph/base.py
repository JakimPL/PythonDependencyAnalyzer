from typing import Any, Generic, Iterator, List, Optional, Self

import networkx as nx
from networkx.classes.reportviews import NodeView, OutEdgeView

from pda.structures.node.types import Edge, NodeT


class Graph(Generic[NodeT]):
    """
    Base graph class for Python Dependency Analyzer.
    """

    def __init__(self, graph: Optional[nx.DiGraph] = None) -> None:
        self._graph = self._sort(graph or nx.DiGraph())

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
    def nodes(self) -> NodeView[NodeT]:
        return self._graph.nodes

    @property
    def edges(self) -> OutEdgeView[NodeT]:
        return self._graph.edges

    def has_node(self, module: NodeT) -> bool:
        return bool(self._graph.has_node(module))

    def has_edge(self, from_module: NodeT, to_module: NodeT) -> bool:
        return bool(self._graph.has_edge(from_module, to_module))

    def add_node(self, module: NodeT) -> None:
        if not self.has_node(module):
            self._graph.add_node(module)

    def add_edge(self, from_module: NodeT, to_module: NodeT) -> None:
        if from_module != to_module and not self.has_edge(from_module, to_module):
            self.add_node(from_module)
            self.add_node(to_module)
            self._graph.add_edge(from_module, to_module)

    def update_node(self, module: NodeT, **attributes: Any) -> None:
        if self.has_node(module):
            self._graph.nodes[module].update(attributes)

    def edge_label(self, from_node: NodeT, to_node: NodeT) -> str:
        from_label = from_node.label
        to_label = to_node.label
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

    def sort(self) -> None:
        self._graph = self._sort(self._graph)

    @staticmethod
    def _sort(graph: nx.DiGraph) -> nx.DiGraph:
        if nx.is_directed_acyclic_graph(graph):
            return Graph._sort_topologically(graph)

        return Graph._sort_by_levels(graph)

    @staticmethod
    def _sort_by_levels(graph: nx.DiGraph) -> nx.DiGraph:
        sorted_nodes = sorted(graph.nodes())
        graph = graph.copy()
        for node in sorted_nodes:
            if graph.in_degree(node) == 0:
                node.level = 0
            else:
                predecessor_levels = [pred.level for pred in graph.predecessors(node) if hasattr(pred, "level")]
                node.level = max(predecessor_levels) + 1 if predecessor_levels else 0

        return graph

    @staticmethod
    def _sort_topologically(graph: nx.DiGraph) -> nx.DiGraph:
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("Graph contains cycles, cannot perform topological sort.")

        roots = [node for node in graph.nodes() if graph.in_degree(node) == 0]
        node: NodeT
        for node in nx.topological_sort(graph):
            if node in roots:
                node.level = 0
            else:
                node.level = max(predecessor.level for predecessor in graph.predecessors(node)) + 1

        return graph
