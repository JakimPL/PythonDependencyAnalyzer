import warnings
from collections import defaultdict
from typing import Any, Dict, Generic, Iterator, List, Optional, Self, get_args

import networkx as nx
from networkx.classes.reportviews import NodeView, OutEdgeView

from pda.config import GraphSortMethod
from pda.exceptions import PDAGraphLayoutWarning
from pda.structures.node.types import Edge, NodeT
from pda.tools import logger


class Graph(Generic[NodeT]):
    """
    Base graph class for Python Dependency Analyzer.
    """

    def __init__(self, graph: Optional[nx.DiGraph] = None) -> None:
        self._graph = graph or nx.DiGraph()

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

    def sort(self, method: GraphSortMethod = "auto") -> None:
        self._graph = self._sort(self._graph, method=method)

    @staticmethod
    def _sort(graph: nx.DiGraph, method: GraphSortMethod = "auto") -> nx.DiGraph:
        if not graph:
            return graph

        if method not in get_args(GraphSortMethod):
            warnings.warn(f"Unknown sorting method '{method}', defaulting to 'auto'", PDAGraphLayoutWarning)

        is_acyclic: bool = nx.is_directed_acyclic_graph(graph)
        auto: bool = method == "auto" and is_acyclic

        if method == "topological" and not is_acyclic:
            warnings.warn(
                "Graph contains cycles, cannot perform topological sort. Falling back to 'condensation' sorting.",
                PDAGraphLayoutWarning,
            )
            method = "condensation"

        if method == "topological" or auto:
            return Graph._sort_topologically(graph)

        if method in ("auto", "condensation"):
            return Graph._sort_by_condensation(graph)

        return Graph._sort_by_levels(graph)

    @staticmethod
    def _sort_by_levels(graph: nx.DiGraph) -> nx.DiGraph:
        logger.info("Sorting graph by levels")
        sorted_nodes = sorted(graph.nodes())
        node_map: Dict[NodeT, NodeT] = {}
        for node in sorted_nodes:
            node.level = 0
            node_map[node] = node

        graph = graph.copy()
        for sorted_node in sorted_nodes:
            node = node_map[sorted_node]

            if graph.in_degree(sorted_node) > 0:
                predecessors = [node_map[pred] for pred in graph.predecessors(sorted_node)]
                node.level = max(pred.level for pred in predecessors) + 1

        return graph

    @staticmethod
    def _sort_by_condensation(graph: nx.DiGraph) -> nx.DiGraph:
        logger.info("Sorting graph by condensation")

        graph = graph.copy()
        condensed = nx.condensation(graph)
        mapping = condensed.graph["mapping"]

        components = defaultdict(list)
        for node, component_id in mapping.items():
            components[component_id].append(node)

        sorted_component_ids = list(nx.topological_sort(condensed))
        final_order: List[NodeT] = []

        for component_id in sorted_component_ids:
            component_nodes: List[NodeT] = sorted(components[component_id])
            external_preds = [
                predecessor
                for node in component_nodes
                for predecessor in graph.predecessors(node)
                if mapping[predecessor] != component_id
            ]

            if external_preds:
                base_level = max(predecessor.level for predecessor in external_preds) + 1
            else:
                base_level = 0

            for node in component_nodes:
                node.level = base_level
                final_order.append(node)

        sorted_graph = nx.DiGraph()
        sorted_graph.add_nodes_from(final_order)
        sorted_graph.add_edges_from(graph.edges())

        return sorted_graph

    @staticmethod
    def _sort_topologically(graph: nx.DiGraph) -> nx.DiGraph:
        logger.info("Sorting graph topologically")
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("Graph contains cycles, cannot perform topological sort.")

        graph = graph.copy()
        roots: List[NodeT] = []
        node_map: Dict[NodeT, NodeT] = {}
        for node in graph.nodes():
            node.level = 0
            node_map[node] = node
            if graph.in_degree(node) == 0:
                roots.append(node)

        for sorted_node in nx.topological_sort(graph):
            node = node_map[sorted_node]
            if node in roots:
                continue

            predecessors = list(graph.predecessors(sorted_node))
            node.level = max(pred.level for pred in predecessors) + 1

        return graph
