from pathlib import Path
from typing import Self, override

import networkx as nx

from pda.graph.base import Graph
from pda.tools.paths import is_dir


class PathGraph(Graph[Path]):
    @override
    def label(self, node: Path) -> str:
        return node.name

    @override
    def group(self, node: Path) -> str:
        if is_dir(node):
            return "."

        return node.suffix

    @override
    def order(self, node: Path) -> int:
        if is_dir(node):
            return 0

        return 1

    @staticmethod
    def _remove_files_from_graph(graph: nx.DiGraph) -> nx.DiGraph:
        simplified_graph = graph.copy()
        for node in graph.nodes:
            if not is_dir(node):
                simplified_graph.remove_node(node)

        return simplified_graph

    def simplify(self) -> Self:
        """
        Hides files from the graph, only showing directories.
        """
        simplified_graph = self._remove_files_from_graph(self._graph)
        sorted_graph = self._sort_if_possible(simplified_graph)
        return self.__class__(graph=sorted_graph)
