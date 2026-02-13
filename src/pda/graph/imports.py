import networkx as nx

from pda.config import ImportGraphNodeFormatEnum
from pda.graph import BaseGraph
from pda.specification import CategorizedModule


class ImportGraph(BaseGraph[CategorizedModule], graph_type=nx.DiGraph):
    def __call__(self, output_format: ImportGraphNodeFormatEnum) -> nx.DiGraph:
        return self._create_output_graph(output_format)

    def label(self, node: CategorizedModule) -> str:
        return node.name

    def _create_output_graph(self, output_format: ImportGraphNodeFormatEnum) -> nx.DiGraph:
        match output_format:
            case ImportGraphNodeFormatEnum.FULL:
                graph = nx.DiGraph(self._graph)
            case ImportGraphNodeFormatEnum.TOP_LEVEL:
                graph = self._create_top_level_graph()
            case _:
                raise ValueError(f"Unsupported output format: {output_format}")

        return graph

    def _create_top_level_graph(self) -> nx.DiGraph:
        """
        Create a graph where nodes are identified by their top-level module name.
        Collapses all submodules into their parent top-level module.
        """

        def partition(module1: CategorizedModule, module2: CategorizedModule) -> bool:
            return module1.module.top_level_module == module2.module.top_level_module

        return nx.quotient_graph(
            self._graph,
            partition,
            create_using=nx.DiGraph,
        )
