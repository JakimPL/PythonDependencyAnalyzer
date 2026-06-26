import math
from typing import Dict, List, Tuple

from pda.config import LayoutConfig, RelaxationConfig, RingConfig
from pda.models import (
    ModuleGraph,
    ModuleNode,
    PackageRingLayout,
    module_layout_from_config,
    module_pyvis_converter,
)
from pda.specification import CategorizedModule, ModuleCategory, UnavailableModule
from pda.structures.graph import PyVisConverter
from pda.structures.graph.layout import GraphLayout, Position


def _node(name: str, category: ModuleCategory = ModuleCategory.LOCAL) -> ModuleNode:
    module = CategorizedModule(module=UnavailableModule(name=name), category=category)
    return ModuleNode(module, qualified_name=True)


def _build_graph(edges: List[Tuple[str, str]]) -> ModuleGraph:
    graph = ModuleGraph()
    nodes: Dict[str, ModuleNode] = {}
    for source, target in edges:
        nodes.setdefault(source, _node(source))
        nodes.setdefault(target, _node(target))
        graph.add_edge(nodes[source], nodes[target])

    return graph


def _config(**overrides: object) -> LayoutConfig:
    overrides.setdefault("ring", RingConfig(jitter=0.0))
    return LayoutConfig(mode="package_ring", **overrides)


def _positions_by_label(layout: PackageRingLayout, graph: ModuleGraph) -> Dict[str, Position]:
    result = layout.compute(graph)
    assert result is not None
    return {node.label: position for node, position in result.positions.items()}


def _radius(position: Position) -> float:
    return math.hypot(position[0], position[1])


def _angle(position: Position) -> float:
    return math.atan2(position[1], position[0]) % (2 * math.pi)


def _edge_length(layout: PackageRingLayout, graph: ModuleGraph) -> float:
    result = layout.compute(graph)
    assert result is not None
    positions = result.positions
    return sum(
        math.hypot(positions[source][0] - positions[target][0], positions[source][1] - positions[target][1])
        for source, target in graph.edges
    )


def _min_pairwise_distance(positions: Dict[str, Position]) -> float:
    points = list(positions.values())
    return min(
        math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1])
        for i in range(len(points))
        for j in range(i + 1, len(points))
    )


class TestPackageRingLayout:
    def test_all_nodes_are_positioned(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.b", "other.x")])
        layout = PackageRingLayout(_config())

        result = layout.compute(graph)

        assert result is not None
        assert set(result.positions.keys()) == set(graph.nodes)

    def test_empty_graph_returns_none(self) -> None:
        assert PackageRingLayout(_config()).compute(ModuleGraph()) is None

    def test_single_node_is_positioned(self) -> None:
        graph = ModuleGraph()
        graph.add_node(_node("pkg"))

        result = PackageRingLayout(_config()).compute(graph)

        assert result is not None
        assert len(result.positions) == 1

    def test_cyclic_graph_does_not_raise(self) -> None:
        graph = _build_graph([("pkg.a", "other.x"), ("other.x", "pkg.a")])

        result = PackageRingLayout(_config()).compute(graph)

        assert result is not None
        assert len(result.positions) == 2

    def test_radius_increases_with_containment_depth(self) -> None:
        graph = _build_graph([("pkg", "pkg.a"), ("pkg.a", "pkg.a.b")])
        positions = _positions_by_label(PackageRingLayout(_config()), graph)

        assert _radius(positions["pkg"]) < _radius(positions["pkg.a"]) < _radius(positions["pkg.a.b"])

    def test_same_depth_is_equiradial_without_blend(self) -> None:
        graph = _build_graph([("pkg", "pkg.a"), ("pkg", "pkg.b"), ("pkg", "pkg.c")])
        layout = PackageRingLayout(_config(ring=RingConfig(jitter=0.0, dependency_blend=0.0)))

        positions = _positions_by_label(layout, graph)

        radii = [_radius(positions[label]) for label in ("pkg.a", "pkg.b", "pkg.c")]
        assert math.isclose(radii[0], radii[1], abs_tol=1e-6)
        assert math.isclose(radii[1], radii[2], abs_tol=1e-6)

    def test_min_radius_sets_planet_orbit_independent_of_ring_spacing(self) -> None:
        graph = _build_graph([("pkg", "pkg.a"), ("pkg.a", "pkg.a.b")])
        settings = dict(jitter=0.0, dependency_blend=0.0, node_spacing=10.0, ring_spacing=250.0)

        near = _positions_by_label(PackageRingLayout(_config(ring=RingConfig(min_radius=100.0, **settings))), graph)
        far = _positions_by_label(PackageRingLayout(_config(ring=RingConfig(min_radius=700.0, **settings))), graph)

        assert math.isclose(_radius(near["pkg.a"]), 100.0, rel_tol=1e-6)
        assert math.isclose(_radius(far["pkg.a"]), 700.0, rel_tol=1e-6)
        assert math.isclose(_radius(far["pkg.a.b"]) - _radius(far["pkg.a"]), 250.0, rel_tol=1e-6)

    def test_dependency_blend_separates_levels_within_a_ring(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])
        nodes = {node.label: node for node in graph.nodes}
        nodes["pkg.a"].level = 0
        nodes["pkg.b"].level = 1

        layout = PackageRingLayout(_config(ring=RingConfig(jitter=0.0, dependency_blend=0.6)))
        positions = _positions_by_label(layout, graph)

        assert not math.isclose(_radius(positions["pkg.a"]), _radius(positions["pkg.b"]), abs_tol=1e-6)
        assert _radius(positions["pkg.a"]) < _radius(positions["pkg.b"])

    def test_crowded_ring_is_pushed_outward(self) -> None:
        children = [f"pkg.m{index}" for index in range(12)]
        graph = _build_graph([("pkg", child) for child in children])
        node_spacing = 400.0
        layout = PackageRingLayout(
            _config(ring=RingConfig(jitter=0.0, dependency_blend=0.0, node_spacing=node_spacing))
        )

        positions = _positions_by_label(layout, graph)

        arc_fit = len(children) * node_spacing / (2 * math.pi)
        assert math.isclose(_radius(positions[children[0]]), arc_fit, rel_tol=1e-6)

    def test_packages_stay_contiguous(self) -> None:
        edges = [
            ("pkg.a", "pkg.b"),
            ("pkg.b", "pkg.c"),
            ("pkg.a", "other.x"),
            ("other.x", "other.y"),
            ("pkg.c", "other.y"),
        ]
        graph = _build_graph(edges)
        result = PackageRingLayout(_config()).compute(graph)
        assert result is not None

        ordered = sorted(result.positions.items(), key=lambda item: _angle(item[1]))
        packages = [node.module.prefix(0) for node, _ in ordered]
        boundaries = sum(1 for index in range(len(packages)) if packages[index] != packages[index - 1])

        assert boundaries == len({package for package in packages})

    def test_layout_is_deterministic_for_fixed_seed(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.sub.c", "pkg.sub.d"), ("pkg.a", "other.x")])
        layout = PackageRingLayout(LayoutConfig(mode="package_ring"))

        first = layout.compute(graph)
        second = layout.compute(graph)

        assert first is not None and second is not None
        assert first.positions == second.positions

    def test_edge_pull_does_not_increase_edge_length(self) -> None:
        edges = [
            ("pkg.a.x", "other.deep.z"),
            ("pkg.a.y", "pkg.a.x"),
            ("other.deep.z", "other.deep.w"),
            ("pkg.b", "other.deep.w"),
        ]
        graph = _build_graph(edges)

        structure = _edge_length(PackageRingLayout(_config(ring=RingConfig(jitter=0.0, edge_pull=0.0))), graph)
        balanced = _edge_length(PackageRingLayout(_config(ring=RingConfig(jitter=0.0, edge_pull=0.5))), graph)

        assert balanced <= structure + 1e-6

    def test_repulsion_separates_overlapping_nodes(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.a.b"), ("pkg.z", "pkg.z.y"), ("pkg.a", "pkg.z")])
        levels = {"pkg.a": 0, "pkg.z": 1, "pkg.a.b": 1, "pkg.z.y": 0}
        for node in graph.nodes:
            node.level = levels[node.label]

        node_spacing = 120.0
        settings = dict(jitter=0.0, dependency_blend=1.0, edge_pull=0.0, node_spacing=node_spacing, ring_spacing=150.0)
        crowded = _positions_by_label(PackageRingLayout(_config(ring=RingConfig(repulsion=0.0, **settings))), graph)
        spread = PackageRingLayout(_config(ring=RingConfig(repulsion=1.0, repulsion_iterations=80, **settings)))
        separated = _positions_by_label(spread, graph)

        assert _min_pairwise_distance(crowded) < node_spacing
        assert _min_pairwise_distance(separated) >= _min_pairwise_distance(crowded)
        assert _min_pairwise_distance(separated) > 0.9 * node_spacing

    def test_isolated_nodes_in_a_confined_wedge_do_not_overlap(self) -> None:
        edges = [("pkg", "pkg.crowded"), ("pkg", "pkg.deep")]
        graph = _build_graph(edges)
        for index in range(20):
            graph.add_node(_node(f"pkg.crowded.iso{index}"))
        for index in range(80):
            graph.add_node(_node(f"pkg.deep.sub.m{index}"))

        node_spacing = 50.0
        layout = PackageRingLayout(
            _config(ring=RingConfig(jitter=0.0, node_spacing=node_spacing, ring_spacing=200.0, min_radius=400.0))
        )
        positions = _positions_by_label(layout, graph)

        assert _min_pairwise_distance(positions) > 0.95 * node_spacing

    def test_repulsion_is_deterministic(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.a.b"), ("pkg.z", "pkg.z.y"), ("pkg.a", "pkg.z")])
        layout = PackageRingLayout(_config(ring=RingConfig(jitter=0.0, dependency_blend=1.0, repulsion=1.0)))

        first = layout.compute(graph)
        second = layout.compute(graph)

        assert first is not None and second is not None
        assert first.positions == second.positions

    def test_repulsion_keeps_radius_within_band(self) -> None:
        graph = _build_graph([("pkg", "pkg.a"), ("pkg", "pkg.b"), ("pkg", "pkg.c")])
        layout = PackageRingLayout(_config(ring=RingConfig(jitter=0.0, dependency_blend=0.0, repulsion=1.0)))

        positions = _positions_by_label(layout, graph)

        radii = [_radius(positions[label]) for label in ("pkg.a", "pkg.b", "pkg.c")]
        assert math.isclose(radii[0], radii[1], abs_tol=1e-6)
        assert math.isclose(radii[1], radii[2], abs_tol=1e-6)


class TestVisOptionsPatch:
    def test_static_disables_hierarchical_and_physics(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])
        result = PackageRingLayout(_config()).compute(graph)

        assert result is not None
        assert result.vis_options_patch["layout"]["hierarchical"]["enabled"] is False
        assert result.vis_options_patch["physics"]["enabled"] is False
        assert result.node_options == {}

    def test_relaxation_enables_physics_and_anchors_centre(self) -> None:
        graph = _build_graph([("pkg", "pkg.a"), ("pkg", "pkg.b")])
        config = _config(relaxation=RelaxationConfig(enabled=True, anchor_centers=True))
        result = PackageRingLayout(config).compute(graph)

        assert result is not None
        physics = result.vis_options_patch["physics"]
        assert physics["enabled"] is True
        assert physics["solver"] == "forceAtlas2Based"

        anchored = {node.label for node, options in result.node_options.items() if "fixed" in options}
        assert anchored == {"pkg"}


class TestModuleLayoutFactory:
    def test_hierarchical_mode_yields_no_layout(self) -> None:
        assert module_layout_from_config(LayoutConfig()) is None

    def test_package_ring_mode_yields_layout(self) -> None:
        layout = module_layout_from_config(LayoutConfig(mode="package_ring"))

        assert isinstance(layout, GraphLayout)


class TestModulePyVisConverter:
    def test_helper_wires_layout_from_config(self) -> None:
        converter = module_pyvis_converter(theme="light")

        assert isinstance(converter, PyVisConverter)
        if converter.config.layout.mode == "package_ring":
            assert isinstance(converter.layout, PackageRingLayout)
        else:
            assert converter.layout is None

    def test_injected_layout_is_stored_and_used(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.a", "other.x")])
        layout = PackageRingLayout(_config())
        converter: PyVisConverter[ModuleNode] = PyVisConverter(layout=layout)

        assert converter.layout is layout

        network = converter(graph)
        assert all("x" in node and "y" in node for node in network.nodes)
