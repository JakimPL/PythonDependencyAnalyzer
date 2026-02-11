import networkx as nx

from pydepgraph.config import ImportGraphNodeFormatEnum
from pydepgraph.graph import BaseGraph
from pydepgraph.specification import Module


class ImportGraph(BaseGraph[Module], graph_type=nx.DiGraph):
    def __call__(self, output_format: ImportGraphNodeFormatEnum) -> nx.DiGraph:
        return self._create_output_graph(output_format)

    def _create_output_graph(self, output_format: ImportGraphNodeFormatEnum) -> nx.DiGraph:
        match output_format:
            case ImportGraphNodeFormatEnum.FULL:
                return nx.DiGraph(self._graph)
            case ImportGraphNodeFormatEnum.NAME:
                return nx.relabel_nodes(
                    self._graph,
                    lambda module: module.name,
                    copy=True,
                )
            case ImportGraphNodeFormatEnum.TOP_LEVEL:
                return self._create_top_level_graph()

        raise ValueError(f"Unsupported output format: {output_format}")

    def _create_top_level_graph(self) -> nx.DiGraph:
        """
        Create a graph where nodes are identified by their top-level module name.
        Collapses all submodules into their parent top-level module.
        """

        def partition(module1: Module, module2: Module) -> bool:
            return module1.top_level_module == module2.top_level_module

        quotient = nx.quotient_graph(
            self._graph,
            partition,
            create_using=nx.DiGraph,
        )

        return nx.relabel_nodes(
            quotient,
            lambda node: next(iter(node)).top_level_module,
            copy=False,
        )
