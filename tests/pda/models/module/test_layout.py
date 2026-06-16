import math
from typing import Dict, List, Tuple

from pda.config import ClusterConfig, FlowConfig, LayoutConfig, RelaxationConfig
from pda.models import (
    ModuleGraph,
    ModuleNode,
    PackageCloudLayout,
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


def _positions_by_label(layout: PackageCloudLayout, graph: ModuleGraph) -> Dict[str, Position]:
    result = layout.compute(graph)
    assert result is not None
    return {node.label: position for node, position in result.positions.items()}


def _config(**overrides: object) -> LayoutConfig:
    overrides.setdefault("cluster", ClusterConfig(jitter=0.0))
    return LayoutConfig(mode="package_cloud", **overrides)


def _distance(first: Position, second: Position) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])


class TestPackageCloudLayout:
    def test_all_nodes_are_positioned(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.b", "other.x")])
        layout = PackageCloudLayout(_config())

        result = layout.compute(graph)

        assert result is not None
        assert set(result.positions.keys()) == set(graph.nodes)

    def test_flow_coordinate_increases_with_package_level(self) -> None:
        graph = _build_graph([("a.x", "b.y"), ("b.y", "c.z")])
        layout = PackageCloudLayout(_config())

        positions = _positions_by_label(layout, graph)

        assert positions["a.x"][0] < positions["b.y"][0] < positions["c.z"][0]

    def test_vertical_direction_flows_along_y(self) -> None:
        graph = _build_graph([("a.x", "b.y"), ("b.y", "c.z")])
        layout = PackageCloudLayout(_config(flow=FlowConfig(direction="UD")))

        positions = _positions_by_label(layout, graph)

        assert positions["a.x"][1] < positions["b.y"][1] < positions["c.z"][1]

    def test_modules_cluster_around_their_root(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.a", "other.x")])
        layout = PackageCloudLayout(_config())

        positions = _positions_by_label(layout, graph)

        intra = _distance(positions["pkg.a"], positions["pkg.b"])
        inter = min(
            _distance(positions["pkg.a"], positions["other.x"]),
            _distance(positions["pkg.b"], positions["other.x"]),
        )

        assert intra < inter

    def test_representative_sits_at_cluster_centre(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.a", "pkg.c")])
        layout = PackageCloudLayout(_config())

        positions = _positions_by_label(layout, graph)
        centre = positions["pkg.a"]
        radius = _config().cluster.min_radius

        assert math.isclose(_distance(centre, positions["pkg.b"]), radius, abs_tol=1e-6)
        assert math.isclose(_distance(centre, positions["pkg.c"]), radius, abs_tol=1e-6)

    def test_node_spacing_scales_intra_cloud_distance(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.a", "pkg.c"), ("pkg.a", "pkg.d"), ("pkg.a", "pkg.e")])

        tight = _positions_by_label(
            PackageCloudLayout(_config(cluster=ClusterConfig(jitter=0.0, node_spacing=80))), graph
        )
        loose = _positions_by_label(
            PackageCloudLayout(_config(cluster=ClusterConfig(jitter=0.0, node_spacing=400))), graph
        )

        def spread(positions: Dict[str, Position]) -> float:
            centre = positions["pkg.a"]
            return max(_distance(centre, positions[label]) for label in ("pkg.b", "pkg.c", "pkg.d", "pkg.e"))

        assert spread(loose) > spread(tight)

    def test_intra_and_inter_distances_are_independent(self) -> None:
        edges = [("pkg.a", "pkg.b"), ("pkg.a", "pkg.c"), ("pkg.a", "pkg.d"), ("pkg.a", "other.x")]
        graph = _build_graph(edges)
        band_gap = 60.0

        def gap_between_clouds(node_spacing: float) -> float:
            config = _config(
                flow=FlowConfig(level_separation=band_gap, band_spacing=band_gap),
                cluster=ClusterConfig(jitter=0.0, node_spacing=node_spacing),
            )
            positions = _positions_by_label(PackageCloudLayout(config), graph)
            centre_distance = _distance(positions["pkg.a"], positions["other.x"])
            pkg_radius = max(_distance(positions["pkg.a"], positions[label]) for label in ("pkg.b", "pkg.c", "pkg.d"))
            return centre_distance - pkg_radius

        assert math.isclose(gap_between_clouds(80), gap_between_clouds(400), abs_tol=1e-6)

    def test_layout_is_deterministic_for_fixed_seed(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.sub.c", "pkg.sub.d"), ("pkg.a", "other.x")])
        layout = PackageCloudLayout(LayoutConfig(mode="package_cloud"))

        first = layout.compute(graph)
        second = layout.compute(graph)

        assert first is not None and second is not None
        assert first.positions == second.positions

    def test_cyclic_graph_does_not_raise(self) -> None:
        graph = _build_graph([("pkg.a", "other.x"), ("other.x", "pkg.a")])
        layout = PackageCloudLayout(_config())

        result = layout.compute(graph)

        assert result is not None
        assert len(result.positions) == 2

    def test_empty_graph_returns_none(self) -> None:
        layout = PackageCloudLayout(_config())

        assert layout.compute(ModuleGraph()) is None


class TestVisOptionsPatch:
    def test_static_disables_hierarchical_and_physics(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b")])
        result = PackageCloudLayout(_config()).compute(graph)

        assert result is not None
        assert result.vis_options_patch["layout"]["hierarchical"]["enabled"] is False
        assert result.vis_options_patch["physics"]["enabled"] is False
        assert result.node_options == {}

    def test_relaxation_enables_physics_and_anchors_centres(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.a", "pkg.c")])
        config = _config(relaxation=RelaxationConfig(enabled=True, anchor_centers=True))
        result = PackageCloudLayout(config).compute(graph)

        assert result is not None
        physics = result.vis_options_patch["physics"]
        assert physics["enabled"] is True
        assert physics["solver"] == "forceAtlas2Based"

        anchored = {node.label for node, options in result.node_options.items() if "fixed" in options}
        assert anchored == {"pkg.a"}


class TestModuleLayoutFactory:
    def test_hierarchical_mode_yields_no_layout(self) -> None:
        assert module_layout_from_config(LayoutConfig()) is None

    def test_package_cloud_mode_yields_layout(self) -> None:
        layout = module_layout_from_config(LayoutConfig(mode="package_cloud"))

        assert isinstance(layout, GraphLayout)


class TestModulePyVisConverter:
    def test_helper_wires_layout_from_config(self) -> None:
        converter = module_pyvis_converter(theme="light")

        assert isinstance(converter, PyVisConverter)
        if converter.config.layout.mode == "package_cloud":
            assert isinstance(converter.layout, PackageCloudLayout)
        else:
            assert converter.layout is None

    def test_injected_layout_is_stored_and_used(self) -> None:
        graph = _build_graph([("pkg.a", "pkg.b"), ("pkg.a", "other.x")])
        layout = PackageCloudLayout(_config())
        converter: PyVisConverter[ModuleNode] = PyVisConverter(layout=layout)

        assert converter.layout is layout

        network = converter(graph)
        assert all("x" in node and "y" in node for node in network.nodes)
