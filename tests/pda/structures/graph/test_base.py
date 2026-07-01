from typing import Dict, List, Tuple

from pda.structures.graph.base import Graph
from pda.structures.node.base import Node


def _node(name: str) -> Node[str]:
    return Node(item=name, ordinal=0, label=name)


def _build_graph(edges: List[Tuple[str, str]]) -> Tuple[Graph[Node[str]], Dict[str, Node[str]]]:
    graph: Graph[Node[str]] = Graph()
    nodes: Dict[str, Node[str]] = {}
    for source, target in edges:
        nodes.setdefault(source, _node(source))
        nodes.setdefault(target, _node(target))
        graph.add_edge(nodes[source], nodes[target])

    return graph, nodes


class TestReaches:
    def test_direct_edge(self) -> None:
        graph, nodes = _build_graph([("a", "b")])

        assert graph.reaches(nodes["a"], nodes["b"]) is True

    def test_transitive(self) -> None:
        graph, nodes = _build_graph([("a", "b"), ("b", "c")])

        assert graph.reaches(nodes["a"], nodes["c"]) is True

    def test_no_reverse_path(self) -> None:
        graph, nodes = _build_graph([("a", "b")])

        assert graph.reaches(nodes["b"], nodes["a"]) is False

    def test_node_reaches_itself(self) -> None:
        graph, nodes = _build_graph([("a", "b")])

        assert graph.reaches(nodes["a"], nodes["a"]) is True

    def test_missing_node(self) -> None:
        graph, nodes = _build_graph([("a", "b")])

        assert graph.reaches(nodes["a"], _node("missing")) is False


class TestPath:
    def test_transitive_witness(self) -> None:
        graph, nodes = _build_graph([("a", "b"), ("b", "c")])

        result = graph.path(nodes["a"], nodes["c"])

        assert result == [nodes["a"], nodes["b"], nodes["c"]]

    def test_no_path_returns_none(self) -> None:
        graph, nodes = _build_graph([("a", "b"), ("c", "b")])

        assert graph.path(nodes["a"], nodes["c"]) is None

    def test_missing_node_returns_none(self) -> None:
        graph, nodes = _build_graph([("a", "b")])

        assert graph.path(nodes["a"], _node("missing")) is None
