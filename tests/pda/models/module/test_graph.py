import json
from pathlib import Path
from typing import List, Set, Tuple

import networkx as nx

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


class TestReachability:
    def test_find_returns_node_by_qualified_name(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])

        found = graph.find("pkg.a")

        assert found is not None
        assert found.module.qualified_name == "pkg.a"

    def test_find_returns_none_for_unknown_name(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])

        assert graph.find("pkg.missing") is None

    def test_imports_direct_edge(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])

        assert graph.imports("pkg.a", "pkg.b") is True

    def test_imports_transitively(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.b", "pkg.c")])

        assert graph.imports("pkg.a", "pkg.c") is True

    def test_imports_false_when_no_path(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.c", "pkg.b")])

        assert graph.imports("pkg.a", "pkg.c") is False

    def test_imports_false_for_unknown_name(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])

        assert graph.imports("pkg.a", "pkg.missing") is False

    def test_import_path_returns_transitive_witness(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.b", "pkg.c")])

        assert graph.import_path("pkg.a", "pkg.c") == ["pkg.a", "pkg.b", "pkg.c"]

    def test_import_path_none_when_no_path(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.c", "pkg.b")])

        assert graph.import_path("pkg.a", "pkg.c") is None

    def test_import_path_none_for_unknown_name(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])

        assert graph.import_path("pkg.a", "pkg.missing") is None


class TestToDict:
    def test_node_link_structure(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.b", "other.c")])

        data = graph.to_dict()

        assert data["directed"] is True
        assert {node["id"] for node in data["nodes"]} == {"pkg.a", "pkg.b", "other.c"}
        links = {(link["source"], link["target"]) for link in data["links"]}
        assert links == {("pkg.a", "pkg.b"), ("pkg.b", "other.c")}

    def test_node_attributes(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])

        node = next(item for item in graph.to_dict()["nodes"] if item["id"] == "pkg.a")

        assert node["label"] == "pkg.a"
        assert node["category"] == ModuleCategory.LOCAL.value
        assert node["level"] == 0

    def test_importable_by_networkx(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.b", "other.c")])

        restored = nx.node_link_graph(graph.to_dict(), directed=True, multigraph=False, edges="links")

        assert restored.is_directed()
        assert set(restored.nodes) == {"pkg.a", "pkg.b", "other.c"}
        assert ("pkg.a", "pkg.b") in restored.edges


class TestSave:
    def test_save_writes_json_file(self, tmp_path: Path) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])
        filepath = tmp_path / "graph.json"

        graph.save(filepath)

        loaded = json.loads(filepath.read_text(encoding="utf-8"))
        assert {node["id"] for node in loaded["nodes"]} == {"pkg.a", "pkg.b"}
        assert loaded["links"] == [{"source": "pkg.a", "target": "pkg.b"}]
