from typing import Dict, FrozenSet, Self

import networkx as nx

from pda.models.module.node import ModuleNode
from pda.specification import CategorizedModule, find_module_spec
from pda.structures.graph.base import Graph


class ModuleGraph(Graph[ModuleNode]):
    def _quotient_graph(self) -> nx.DiGraph:
        def partition(node1: ModuleNode, node2: ModuleNode) -> bool:
            return node1.module.top_level_module == node2.module.top_level_module

        return nx.quotient_graph(
            self._graph,
            partition,
            create_using=nx.DiGraph,
        )

    @staticmethod
    def _relabel_quotient_graph(quotient: nx.DiGraph) -> nx.DiGraph:
        representatives: Dict[FrozenSet[ModuleNode], ModuleNode] = {}
        for equivalence_class in quotient.nodes():
            first_module: CategorizedModule = next(iter(equivalence_class)).module
            category = first_module.category
            spec = find_module_spec(first_module.top_level_module, expect_python=False)
            representative = CategorizedModule.from_spec(spec, category=category)
            representatives[equivalence_class] = ModuleNode(representative)

        return nx.relabel_nodes(quotient, representatives)

    def simplify(self) -> Self:
        """
        Create a graph where nodes are identified by their top-level module name.
        Collapses all submodules into their parent top-level module.
        """
        quotient = self._quotient_graph()
        simplified_graph = self._relabel_quotient_graph(quotient)
        sorted_graph = self._sort(simplified_graph)
        return self.__class__(graph=sorted_graph)
