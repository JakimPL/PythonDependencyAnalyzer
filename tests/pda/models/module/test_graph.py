from typing import List, Set, Tuple

from pda.models import ModuleGraph, ModuleNode
from pda.specification import CategorizedModule, ModuleCategory, UnavailableModule


def _node(name: str, category: ModuleCategory = ModuleCategory.LOCAL) -> ModuleNode:
    module = CategorizedModule(module=UnavailableModule(name=name), category=category)
    return ModuleNode(module, qualified_name=True)


def _build_graph(edges: List[Tuple[str, str]]) -> ModuleGraph:
    graph = ModuleGraph()
    nodes = {}
    for source, target in edges:
        nodes.setdefault(source, _node(source))
        nodes.setdefault(target, _node(target))
        graph.add_edge(nodes[source], nodes[target])

    return graph


def _labels(graph: ModuleGraph) -> Set[str]:
    return {node.label for node in graph}


def _edges(graph: ModuleGraph) -> Set[Tuple[str, str]]:
    return {(source.label, target.label) for source, target in graph.edges}


class TestSimplifyLevel:
    def test_level_zero_collapses_to_top_level(self) -> None:
        graph = _build_graph(
            [
                ("pkg.a", "pkg.b"),
                ("pkg.b", "pkg.sub.c"),
                ("pkg.a", "other.x"),
            ]
        )

        collapsed = graph.simplify(0)

        assert _labels(collapsed) == {"pkg", "other"}
        assert _edges(collapsed) == {("pkg", "other")}

    def test_level_one_keeps_two_components(self) -> None:
        graph = _build_graph(
            [
                ("pkg.a", "pkg.b"),
                ("pkg.b", "pkg.sub.c"),
                ("pkg.sub.c", "pkg.sub.d"),
            ]
        )

        collapsed = graph.simplify(1)

        # pkg.sub.c and pkg.sub.d share the prefix 'pkg.sub' and merge.
        assert _labels(collapsed) == {"pkg.a", "pkg.b", "pkg.sub"}
        assert ("pkg.b", "pkg.sub") in _edges(collapsed)

    def test_level_beyond_depth_is_no_op(self) -> None:
        edges = [("pkg.a", "pkg.b"), ("pkg.b", "pkg.sub.c")]
        graph = _build_graph(edges)

        collapsed = graph.simplify(5)

        assert _labels(collapsed) == {"pkg.a", "pkg.b", "pkg.sub.c"}
        assert len(collapsed) == 3

    def test_qualified_name_false_uses_leaf_of_prefix(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.sub.c"), ("pkg.sub.c", "pkg.sub.d")])

        collapsed = graph.simplify(1, qualified_name=False)

        assert _labels(collapsed) == {"a", "sub"}

    def test_self_loops_removed_after_merge(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])

        collapsed = graph.simplify(0)

        assert _labels(collapsed) == {"pkg"}
        assert _edges(collapsed) == set()

    def test_cyclic_collapse_does_not_raise(self) -> None:
        graph = _build_graph([("pkg.a", "other.x"), ("other.x", "pkg.a")])

        collapsed = graph.simplify(0, sort_method="condensation")

        assert _labels(collapsed) == {"pkg", "other"}
