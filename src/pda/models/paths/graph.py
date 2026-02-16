from typing import Self

import networkx as nx

from pda.models.paths.node import PathNode
from pda.structures import Graph
from pda.tools.paths import is_dir


class PathGraph(Graph[PathNode]):
    @staticmethod
    def _remove_files_from_graph(graph: nx.DiGraph) -> nx.DiGraph:
        simplified_graph = graph.copy()

        node: PathNode
        for node in graph.nodes:
            if not is_dir(node.filepath):
                simplified_graph.remove_node(node)

        return simplified_graph

    def simplify(self) -> Self:
        """
        Hides files from the graph, only showing directories.
        """
        simplified_graph = self._remove_files_from_graph(self._graph)
        sorted_graph = self._sort(simplified_graph)
        return self.__class__(graph=sorted_graph)
