from typing import Dict, FrozenSet, Self, override

import networkx as nx

from pda.graph.base import Graph
from pda.specification import CategorizedModule
from pda.specification.modules.spec import find_module_spec


class ModuleGraph(Graph[CategorizedModule]):
    @override
    def label(self, node: CategorizedModule) -> str:
        return node.name

    @override
    def group(self, node: CategorizedModule) -> str:
        return node.category.value

    def _quotient_graph(self) -> nx.DiGraph:
        def partition(module1: CategorizedModule, module2: CategorizedModule) -> bool:
            return module1.top_level_module == module2.top_level_module

        return nx.quotient_graph(
            self._graph,
            partition,
            create_using=nx.DiGraph,
        )

    @staticmethod
    def _relabel_quotient_graph(quotient: nx.DiGraph) -> nx.DiGraph:
        representatives: Dict[FrozenSet[CategorizedModule], CategorizedModule] = {}
        for equivalence_class in quotient.nodes():
            first_module: CategorizedModule = next(iter(equivalence_class))
            category = first_module.category
            spec = find_module_spec(first_module.top_level_module, expect_python=False)
            representative = CategorizedModule.from_spec(spec, category=category)
            representatives[equivalence_class] = representative

        return nx.relabel_nodes(quotient, representatives)

    def simplify(self) -> Self:
        """
        Create a graph where nodes are identified by their top-level module name.
        Collapses all submodules into their parent top-level module.
        """
        quotient = self._quotient_graph()
        simplified_graph = self._relabel_quotient_graph(quotient)
        sorted_graph = self._sort_if_possible(simplified_graph)
        return self.__class__(graph=sorted_graph)
