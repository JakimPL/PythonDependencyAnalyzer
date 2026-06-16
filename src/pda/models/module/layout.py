import math
from collections import defaultdict
from pathlib import Path
from random import Random
from typing import Any, Dict, Final, List, Optional, Set, Tuple

from pda.config import PyVisConfig, Theme
from pda.config.pyvis.layout import LayoutConfig
from pda.constants import DELIMITER
from pda.models.module.graph import ModuleGraph
from pda.models.module.node import ModuleNode
from pda.structures.graph.base import Graph
from pda.structures.graph.converter import PyVisConverter
from pda.structures.graph.layout import GraphLayout, LayoutResult, Position

_ANGLE_JITTER_SCALE: Final[float] = 0.25


class PackageCloudLayout(GraphLayout[ModuleNode]):
    def __init__(self, config: LayoutConfig) -> None:
        self._config = config

    def compute(self, graph: Graph[ModuleNode]) -> Optional[LayoutResult[ModuleNode]]:
        if graph.empty or not isinstance(graph, ModuleGraph):
            return None

        group_level = self._config.group_level
        clusters = self._clusters(graph, group_level)
        levels, predecessors = self._package_structure(graph, group_level)

        rng = Random(self._config.cluster.seed)
        offsets = {prefix: self._cluster_offsets(clusters[prefix], group_level, rng) for prefix in sorted(clusters)}
        radii = {prefix: self._bounding_radius(member_offsets) for prefix, member_offsets in offsets.items()}
        centers = self._package_centers(levels, predecessors, radii)

        positions: Dict[ModuleNode, Position] = {}
        anchors: Set[ModuleNode] = set()
        for prefix, member_offsets in offsets.items():
            center_x, center_y = centers[prefix]
            for node, (offset_x, offset_y) in member_offsets.items():
                positions[node] = (center_x + offset_x, center_y + offset_y)

            anchors.add(clusters[prefix][0])

        return LayoutResult(
            positions=positions,
            node_options=self._node_options(anchors),
            vis_options_patch=self._vis_patch(),
        )

    def _clusters(self, graph: ModuleGraph, group_level: int) -> Dict[str, List[ModuleNode]]:
        clusters: Dict[str, List[ModuleNode]] = defaultdict(list)
        for node in graph.nodes:
            clusters[node.module.prefix(group_level)].append(node)

        for members in clusters.values():
            members.sort(key=lambda node: node.module.qualified_name)

        return clusters

    def _package_structure(
        self,
        graph: ModuleGraph,
        group_level: int,
    ) -> Tuple[Dict[str, int], Dict[str, List[str]]]:
        package_graph = graph.simplify(group_level, sort_method="auto")
        levels: Dict[str, int] = {}
        for representative in package_graph.nodes:
            levels[representative.module.prefix(group_level)] = representative.level

        predecessors: Dict[str, List[str]] = defaultdict(list)
        for source, target in package_graph.edges:
            predecessors[target.module.prefix(group_level)].append(source.module.prefix(group_level))

        return levels, predecessors

    def _package_centers(
        self,
        levels: Dict[str, int],
        predecessors: Dict[str, List[str]],
        radii: Dict[str, float],
    ) -> Dict[str, Position]:
        level_gap = self._config.flow.level_separation
        band_gap = self._config.flow.band_spacing

        by_level: Dict[int, List[str]] = defaultdict(list)
        for prefix, level in levels.items():
            by_level[level].append(prefix)

        order = self._order_levels(by_level, predecessors)

        centers: Dict[str, Position] = {}
        flow = 0.0
        previous_reach = 0.0
        for index, level in enumerate(sorted(order)):
            prefixes = order[level]
            reach = max((radii[prefix] for prefix in prefixes), default=0.0)
            flow = reach if index == 0 else flow + previous_reach + reach + level_gap
            previous_reach = reach
            self._place_band(prefixes, radii, band_gap, flow, centers)

        return centers

    def _place_band(
        self,
        prefixes: List[str],
        radii: Dict[str, float],
        band_gap: float,
        flow: float,
        centers: Dict[str, Position],
    ) -> None:
        bands: List[float] = []
        cursor = 0.0
        previous_radius = 0.0
        for index, prefix in enumerate(prefixes):
            radius = radii[prefix]
            cursor = radius if index == 0 else cursor + previous_radius + radius + band_gap
            bands.append(cursor)
            previous_radius = radius

        midpoint = (bands[0] + bands[-1]) / 2 if bands else 0.0
        for prefix, band in zip(prefixes, bands):
            centers[prefix] = self._project(flow, band - midpoint)

    def _order_levels(
        self,
        by_level: Dict[int, List[str]],
        predecessors: Dict[str, List[str]],
    ) -> Dict[int, List[str]]:
        order: Dict[int, List[str]] = {level: sorted(prefixes) for level, prefixes in by_level.items()}
        if not self._config.flow.crossing_reduction:
            return order

        levels_sorted = sorted(order.keys())
        for _ in range(self._config.flow.crossing_iterations):
            for level in levels_sorted[1:]:
                previous_index = {prefix: index for index, prefix in enumerate(order.get(level - 1, []))}
                decorated: List[Tuple[float, int, str]] = []
                for index, prefix in enumerate(order[level]):
                    barycenter = self._barycenter(prefix, predecessors, previous_index)
                    decorated.append((barycenter if barycenter is not None else float(index), index, prefix))

                decorated.sort()
                order[level] = [prefix for _, _, prefix in decorated]

        return order

    @staticmethod
    def _barycenter(
        prefix: str,
        predecessors: Dict[str, List[str]],
        previous_index: Dict[str, int],
    ) -> Optional[float]:
        ranks = [previous_index[parent] for parent in predecessors.get(prefix, []) if parent in previous_index]
        if not ranks:
            return None

        return sum(ranks) / len(ranks)

    def _cluster_offsets(
        self,
        members: List[ModuleNode],
        group_level: int,
        rng: Random,
    ) -> Dict[ModuleNode, Position]:
        offsets: Dict[ModuleNode, Position] = {members[0]: (0.0, 0.0)}
        others = members[1:]
        if not others:
            return offsets

        subgroups: Dict[str, List[ModuleNode]] = defaultdict(list)
        for node in others:
            subgroups[node.module.prefix(group_level + 1)].append(node)

        total = len(others)
        node_spacing = self._config.cluster.node_spacing
        ring_spacing = self._config.cluster.ring_spacing
        jitter = self._config.cluster.jitter

        cursor = 0.0
        for subkey in sorted(subgroups):
            siblings = subgroups[subkey]
            width = 2 * math.pi * len(siblings) / total
            by_depth: Dict[int, List[ModuleNode]] = defaultdict(list)
            for node in siblings:
                by_depth[max(1, self._sub_depth(node, group_level))].append(node)

            for depth in sorted(by_depth):
                ring = by_depth[depth]
                count = len(ring)
                spacing_radius = count * node_spacing / width if width > 0 else 0.0
                radius = max(self._ring_radius(depth), spacing_radius)
                for index, node in enumerate(ring):
                    angle = cursor + (index + 0.5) / count * width
                    angle += rng.uniform(-jitter, jitter) * width * _ANGLE_JITTER_SCALE / count
                    distance = radius + rng.uniform(-jitter, jitter) * ring_spacing
                    offsets[node] = (distance * math.cos(angle), distance * math.sin(angle))

            cursor += width

        return offsets

    @staticmethod
    def _bounding_radius(offsets: Dict[ModuleNode, Position]) -> float:
        return max((math.hypot(offset_x, offset_y) for offset_x, offset_y in offsets.values()), default=0.0)

    def _node_options(self, anchors: Set[ModuleNode]) -> Dict[ModuleNode, Dict[str, Any]]:
        options: Dict[ModuleNode, Dict[str, Any]] = {}
        if self._config.relaxation.enabled and self._config.relaxation.anchor_centers:
            for node in anchors:
                options[node] = {"fixed": {"x": True, "y": True}}

        return options

    def _vis_patch(self) -> Dict[str, Any]:
        layout: Dict[str, Any] = {"hierarchical": {"enabled": False}}
        patch: Dict[str, Any] = {"layout": layout}

        relaxation = self._config.relaxation
        if not relaxation.enabled:
            patch["physics"] = {"enabled": False}
            return patch

        layout["randomSeed"] = self._config.cluster.seed
        patch["physics"] = {
            "enabled": True,
            "solver": relaxation.solver,
            "stabilization": {
                "enabled": True,
                "iterations": relaxation.stabilization_iterations,
            },
            relaxation.solver: {
                "gravitationalConstant": relaxation.gravity,
                "centralGravity": relaxation.central_gravity,
                "springLength": relaxation.spring_length,
                "springConstant": relaxation.spring_constant,
                "damping": relaxation.damping,
            },
        }
        return patch

    def _project(self, flow: float, band: float) -> Position:
        match self._config.flow.direction:
            case "LR":
                return (flow, band)
            case "RL":
                return (-flow, band)
            case "UD":
                return (band, flow)
            case "DU":
                return (band, -flow)
            case _:
                return (flow, band)

    @staticmethod
    def _sub_depth(node: ModuleNode, group_level: int) -> int:
        parts = node.module.qualified_name.split(DELIMITER)
        return max(0, len(parts) - (group_level + 1))

    def _ring_radius(self, depth: int) -> float:
        return self._config.cluster.min_radius + self._config.cluster.ring_spacing * (depth - 1)


def module_layout_from_config(config: LayoutConfig) -> Optional[GraphLayout[ModuleNode]]:
    match config.mode:
        case "package_cloud":
            return PackageCloudLayout(config)
        case _:
            return None


def module_pyvis_converter(
    *,
    config_path: Path = PyVisConfig.default_path(),
    theme: Theme = "light",
    network_kwargs: Optional[Dict[str, Any]] = None,
    vis_options: Optional[Dict[str, Dict[str, Any]]] = None,
) -> PyVisConverter[ModuleNode]:
    converter: PyVisConverter[ModuleNode] = PyVisConverter(
        config_path=config_path,
        theme=theme,
        network_kwargs=network_kwargs,
        vis_options=vis_options,
    )
    converter.layout = module_layout_from_config(converter.config.layout)
    return converter
