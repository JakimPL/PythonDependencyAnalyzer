from typing import Dict, FrozenSet, List, Optional, Self

import networkx as nx

from pda.config import GraphSortMethod
from pda.constants import DELIMITER
from pda.models.module.node import ModuleNode
from pda.structures.graph.base import Graph


class ModuleGraph(Graph[ModuleNode]):
    def find(self, name: str) -> Optional[ModuleNode]:
        for node in self:
            if node.module.qualified_name == name:
                return node

        return None

    def imports(self, source: str, target: str) -> bool:
        source_node = self.find(source)
        target_node = self.find(target)
        if source_node is None or target_node is None:
            return False

        return self.reaches(source_node, target_node)

    def import_path(self, source: str, target: str) -> Optional[List[str]]:
        source_node = self.find(source)
        target_node = self.find(target)
        if source_node is None or target_node is None:
            return None

        nodes = self.path(source_node, target_node)
        if nodes is None:
            return None

        return [node.module.qualified_name for node in nodes]

    def _quotient_graph(self, level: int) -> nx.DiGraph:
        def partition(node1: ModuleNode, node2: ModuleNode) -> bool:
            return node1.module.prefix(level) == node2.module.prefix(level)

        return nx.quotient_graph(
            self._graph,
            partition,
            create_using=nx.DiGraph,
        )

    @staticmethod
    def _relabel_quotient_graph(
        quotient: nx.DiGraph,
        level: int,
        *,
        qualified_name: bool = True,
    ) -> nx.DiGraph:
        representatives: Dict[FrozenSet[ModuleNode], ModuleNode] = {}
        for equivalence_class in quotient.nodes():
            representative = min(equivalence_class, key=lambda node: node.module.qualified_name)
            prefix = representative.module.prefix(level)
            label = prefix if qualified_name else prefix.split(DELIMITER)[-1]
            representatives[equivalence_class] = ModuleNode(representative.module, label=label)

        return nx.relabel_nodes(quotient, representatives)

    def simplify(
        self,
        level: int = 0,
        *,
        qualified_name: bool = True,
        sort_method: GraphSortMethod = "topological",
    ) -> Self:
        """
        Collapse the graph by absolute dotted-name level (counted from the package root).
        Nodes sharing the same prefix up to `level` are merged into a single representative
        node. ``level=0`` collapses all submodules into their top-level package.
        """
        quotient = self._quotient_graph(level)
        collapsed = self._relabel_quotient_graph(quotient, level, qualified_name=qualified_name)
        collapsed.remove_edges_from(nx.selfloop_edges(collapsed))
        sorted_graph = self._sort(collapsed, method=sort_method)
        return self.__class__(graph=sorted_graph)
