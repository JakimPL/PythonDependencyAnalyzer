import math
from collections import defaultdict
from dataclasses import dataclass, field
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

_VIRTUAL_ROOT: Final[str] = ""
_TWO_PI: Final[float] = 2.0 * math.pi
_EPSILON: Final[float] = 1e-9


@dataclass
class _TreeNode:
    prefix: str
    depth: int
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    modules: List[ModuleNode] = field(default_factory=list)
    leaf_count: int = 1
    wedge_start: float = 0.0
    wedge_end: float = _TWO_PI


class PackageRingLayout(GraphLayout[ModuleNode]):
    def __init__(self, config: LayoutConfig) -> None:
        self._config = config

    def compute(self, graph: Graph[ModuleNode]) -> Optional[LayoutResult[ModuleNode]]:
        if graph.empty or not isinstance(graph, ModuleGraph):
            return None

        tree = self._build_tree(graph)
        root, root_depth = self._root(tree)
        subtree_modules = self._subtree_modules(tree, root)
        subtree_sets: Dict[str, Set[ModuleNode]] = {prefix: set(modules) for prefix, modules in subtree_modules.items()}
        self._leaf_counts(tree, root, subtree_modules)
        neighbours = self._neighbours(graph)

        node_angle = self._order(tree, root, subtree_modules, subtree_sets, neighbours)
        node_radius, node_band, node_ring = self._radii(tree, root_depth, node_angle)
        node_angle = self._nudge(tree, node_angle, node_radius, neighbours)
        node_wedge = self._node_wedges(tree, self._config.ring.wedge_margin)
        node_angle, node_radius = self._separate(node_angle, node_radius, node_band, node_wedge, node_ring)

        rng = Random(self._config.ring.seed)
        positions = self._positions(node_angle, node_radius, rng)

        return LayoutResult(
            positions=positions,
            node_options=self._node_options(tree, root),
            vis_options_patch=self._vis_patch(),
        )

    def _build_tree(self, graph: ModuleGraph) -> Dict[str, _TreeNode]:
        tree: Dict[str, _TreeNode] = {}
        for node in graph.nodes:
            parts = node.module.qualified_name.split(DELIMITER)
            for depth in range(len(parts)):
                prefix = DELIMITER.join(parts[: depth + 1])
                if prefix not in tree:
                    tree[prefix] = _TreeNode(prefix=prefix, depth=depth)

                if depth > 0:
                    parent = DELIMITER.join(parts[:depth])
                    child = tree[prefix]
                    if child.parent is None:
                        child.parent = parent
                        tree[parent].children.append(prefix)

            tree[node.module.qualified_name].modules.append(node)

        for branch in tree.values():
            branch.children.sort()

        return tree

    def _root(self, tree: Dict[str, _TreeNode]) -> Tuple[str, int]:
        roots = sorted(prefix for prefix, branch in tree.items() if branch.depth == 0)
        if len(roots) == 1:
            return roots[0], 0

        virtual = _TreeNode(prefix=_VIRTUAL_ROOT, depth=-1, children=roots)
        tree[_VIRTUAL_ROOT] = virtual
        for prefix in roots:
            tree[prefix].parent = _VIRTUAL_ROOT

        return _VIRTUAL_ROOT, -1

    def _subtree_modules(self, tree: Dict[str, _TreeNode], root: str) -> Dict[str, List[ModuleNode]]:
        modules: Dict[str, List[ModuleNode]] = {}

        def collect(prefix: str) -> List[ModuleNode]:
            branch = tree[prefix]
            gathered = list(branch.modules)
            for child in branch.children:
                gathered.extend(collect(child))

            modules[prefix] = gathered
            return gathered

        collect(root)
        return modules

    def _leaf_counts(
        self,
        tree: Dict[str, _TreeNode],
        root: str,
        subtree_modules: Dict[str, List[ModuleNode]],
    ) -> None:
        def assign(prefix: str) -> int:
            branch = tree[prefix]
            if not branch.children:
                branch.leaf_count = max(1, len(branch.modules))
                return branch.leaf_count

            branch.leaf_count = max(1, sum(assign(child) for child in branch.children))
            return branch.leaf_count

        assign(root)

    @staticmethod
    def _neighbours(graph: ModuleGraph) -> Dict[ModuleNode, List[ModuleNode]]:
        neighbours: Dict[ModuleNode, List[ModuleNode]] = defaultdict(list)
        for source, target in graph.edges:
            neighbours[source].append(target)
            neighbours[target].append(source)

        return neighbours

    def _order(
        self,
        tree: Dict[str, _TreeNode],
        root: str,
        subtree_modules: Dict[str, List[ModuleNode]],
        subtree_sets: Dict[str, Set[ModuleNode]],
        neighbours: Dict[ModuleNode, List[ModuleNode]],
    ) -> Dict[ModuleNode, float]:
        node_angle = self._assign_wedges(tree, root)
        for _ in range(self._config.ring.order_iterations):
            for branch in tree.values():
                if len(branch.children) < 2:
                    continue

                mid = (branch.wedge_start + branch.wedge_end) / 2
                branch.children.sort(
                    key=lambda child: self._order_key(
                        child,
                        mid,
                        tree,
                        subtree_modules,
                        subtree_sets,
                        neighbours,
                        node_angle,
                    )
                )

            node_angle = self._assign_wedges(tree, root)

        return self._spread_modules(tree)

    def _order_key(
        self,
        child: str,
        mid: float,
        tree: Dict[str, _TreeNode],
        subtree_modules: Dict[str, List[ModuleNode]],
        subtree_sets: Dict[str, Set[ModuleNode]],
        neighbours: Dict[ModuleNode, List[ModuleNode]],
        node_angle: Dict[ModuleNode, float],
    ) -> Tuple[float, str]:
        barycenter = self._subtree_barycenter(child, subtree_modules, subtree_sets, neighbours, node_angle)
        if barycenter is None:
            branch = tree[child]
            barycenter = (branch.wedge_start + branch.wedge_end) / 2

        relative = ((barycenter - mid + math.pi) % _TWO_PI) - math.pi
        return (relative, child)

    def _subtree_barycenter(
        self,
        prefix: str,
        subtree_modules: Dict[str, List[ModuleNode]],
        subtree_sets: Dict[str, Set[ModuleNode]],
        neighbours: Dict[ModuleNode, List[ModuleNode]],
        node_angle: Dict[ModuleNode, float],
    ) -> Optional[float]:
        members = subtree_sets[prefix]
        sum_cos = 0.0
        sum_sin = 0.0
        for module in subtree_modules[prefix]:
            for neighbour in neighbours.get(module, ()):
                if neighbour in members:
                    continue

                angle = node_angle.get(neighbour)
                if angle is None:
                    continue

                sum_cos += math.cos(angle)
                sum_sin += math.sin(angle)

        return self._circular_mean(sum_cos, sum_sin)

    def _assign_wedges(self, tree: Dict[str, _TreeNode], root: str) -> Dict[ModuleNode, float]:
        node_angle: Dict[ModuleNode, float] = {}

        def place(prefix: str, start: float, end: float) -> None:
            branch = tree[prefix]
            branch.wedge_start = start
            branch.wedge_end = end
            angle = (start + end) / 2
            for module in branch.modules:
                node_angle[module] = angle

            if not branch.children:
                return

            total = sum(tree[child].leaf_count for child in branch.children)
            cursor = start
            for child in branch.children:
                fraction = tree[child].leaf_count / total if total > 0 else 1.0 / len(branch.children)
                child_end = cursor + fraction * (end - start)
                place(child, cursor, child_end)
                cursor = child_end

        place(root, 0.0, _TWO_PI)
        return node_angle

    def _spread_modules(self, tree: Dict[str, _TreeNode]) -> Dict[ModuleNode, float]:
        node_angle: Dict[ModuleNode, float] = {}
        for branch in tree.values():
            if not branch.modules:
                continue

            mid = (branch.wedge_start + branch.wedge_end) / 2
            modules = sorted(branch.modules, key=lambda node: (node.module.qualified_name, node.ordinal))
            if len(modules) == 1:
                node_angle[modules[0]] = mid
                continue

            span = (branch.wedge_end - branch.wedge_start) / 4
            for index, module in enumerate(modules):
                node_angle[module] = mid - span + (index + 0.5) / len(modules) * 2 * span

        return node_angle

    def _radii(
        self,
        tree: Dict[str, _TreeNode],
        root_depth: int,
        node_angle: Dict[ModuleNode, float],
    ) -> Tuple[Dict[ModuleNode, float], Dict[ModuleNode, Tuple[float, float]], Dict[ModuleNode, int]]:
        ring_members: Dict[int, List[ModuleNode]] = defaultdict(list)
        node_ring: Dict[ModuleNode, int] = {}
        for branch in tree.values():
            for module in branch.modules:
                ring = branch.depth - root_depth
                ring_members[ring].append(module)
                node_ring[module] = ring

        schedule = self._radius_schedule(ring_members, self._min_angular_gaps(ring_members, node_angle))
        blend = self._config.ring.dependency_blend
        ring_spacing = self._config.ring.ring_spacing

        node_radius: Dict[ModuleNode, float] = {}
        node_band: Dict[ModuleNode, Tuple[float, float]] = {}
        for ring, members in ring_members.items():
            if ring == 0:
                for module in members:
                    node_radius[module] = 0.0
                    node_band[module] = (0.0, 0.0)
                continue

            center = schedule[ring]
            inner_gap = center - schedule[ring - 1]
            outer_gap = schedule[ring + 1] - center if (ring + 1) in schedule else inner_gap
            half_band = min(0.5 * blend * ring_spacing, 0.5 * min(inner_gap, outer_gap))

            levels = [module.level for module in members]
            low, high = min(levels), max(levels)
            for module in members:
                position = (module.level - low) / (high - low) if high > low else 0.5
                node_radius[module] = center + (position - 0.5) * 2 * half_band
                node_band[module] = (center - half_band, center + half_band)

        return node_radius, node_band, node_ring

    def _radius_schedule(
        self,
        ring_members: Dict[int, List[ModuleNode]],
        min_gaps: Dict[int, float],
    ) -> Dict[int, float]:
        node_spacing = self._config.ring.node_spacing
        ring_spacing = self._config.ring.ring_spacing
        min_radius = self._config.ring.min_radius

        schedule: Dict[int, float] = {0: 0.0}
        for ring in range(1, max(ring_members, default=0) + 1):
            base = min_radius + (ring - 1) * ring_spacing
            gap = min_radius if ring == 1 else ring_spacing
            min_gap = min_gaps.get(ring, _TWO_PI)
            arc_fit = node_spacing / min_gap if min_gap > _EPSILON else 0.0
            schedule[ring] = max(base, schedule[ring - 1] + gap, arc_fit)

        return schedule

    @staticmethod
    def _min_angular_gaps(
        ring_members: Dict[int, List[ModuleNode]],
        node_angle: Dict[ModuleNode, float],
    ) -> Dict[int, float]:
        gaps: Dict[int, float] = {}
        for ring, members in ring_members.items():
            angles = sorted(node_angle[module] % _TWO_PI for module in members)
            if len(angles) < 2:
                gaps[ring] = _TWO_PI
                continue

            spacings = [angles[index] - angles[index - 1] for index in range(1, len(angles))]
            spacings.append(angles[0] + _TWO_PI - angles[-1])
            gaps[ring] = min((spacing for spacing in spacings if spacing > _EPSILON), default=_TWO_PI)

        return gaps

    @staticmethod
    def _node_wedges(tree: Dict[str, _TreeNode], margin: float) -> Dict[ModuleNode, Tuple[float, float]]:
        wedges: Dict[ModuleNode, Tuple[float, float]] = {}
        for branch in tree.values():
            if not branch.modules:
                continue

            low = branch.wedge_start + margin
            high = branch.wedge_end - margin
            if high < low:
                low = high = (branch.wedge_start + branch.wedge_end) / 2

            for module in branch.modules:
                wedges[module] = (low, high)

        return wedges

    def _separate(
        self,
        node_angle: Dict[ModuleNode, float],
        node_radius: Dict[ModuleNode, float],
        node_band: Dict[ModuleNode, Tuple[float, float]],
        node_wedge: Dict[ModuleNode, Tuple[float, float]],
        node_ring: Dict[ModuleNode, int],
    ) -> Tuple[Dict[ModuleNode, float], Dict[ModuleNode, float]]:
        repulsion = self._config.ring.repulsion
        if repulsion <= 0 or self._config.ring.repulsion_iterations == 0:
            return node_angle, node_radius

        min_separation = self._config.ring.node_spacing
        modules = sorted(node_angle, key=lambda node: (node.module.qualified_name, node.ordinal))
        order = {module: index for index, module in enumerate(modules)}
        by_ring: Dict[int, List[ModuleNode]] = defaultdict(list)
        for module in modules:
            by_ring[node_ring[module]].append(module)

        angle = dict(node_angle)
        radius = dict(node_radius)
        for _ in range(self._config.ring.repulsion_iterations):
            points = {
                module: (radius[module] * math.cos(angle[module]), radius[module] * math.sin(angle[module]))
                for module in modules
            }
            next_angle = dict(angle)
            next_radius = dict(radius)
            for module in modules:
                ring = node_ring[module]
                candidates = by_ring[ring - 1] + by_ring[ring] + by_ring[ring + 1]
                push_x, push_y = self._repulsion_vector(module, points, candidates, min_separation, order, len(modules))
                point_x, point_y = points[module]
                moved_x = point_x + repulsion * push_x
                moved_y = point_y + repulsion * push_y
                next_angle[module] = self._clamp_angle(math.atan2(moved_y, moved_x), node_wedge[module])
                low, high = node_band[module]
                next_radius[module] = min(high, max(low, math.hypot(moved_x, moved_y)))

            angle, radius = next_angle, next_radius

        return angle, radius

    @staticmethod
    def _repulsion_vector(
        module: ModuleNode,
        points: Dict[ModuleNode, Position],
        candidates: List[ModuleNode],
        min_separation: float,
        order: Dict[ModuleNode, int],
        total: int,
    ) -> Position:
        point_x, point_y = points[module]
        push_x = 0.0
        push_y = 0.0
        for other in candidates:
            if other is module:
                continue

            other_x, other_y = points[other]
            delta_x = point_x - other_x
            delta_y = point_y - other_y
            distance = math.hypot(delta_x, delta_y)
            if distance >= min_separation:
                continue

            if distance > _EPSILON:
                strength = (min_separation - distance) / distance * 0.5
                push_x += delta_x * strength
                push_y += delta_y * strength
            else:
                seed_angle = _TWO_PI * order[module] / total
                push_x += math.cos(seed_angle) * min_separation * 0.5
                push_y += math.sin(seed_angle) * min_separation * 0.5

        return (push_x, push_y)

    @staticmethod
    def _clamp_angle(angle: float, wedge: Tuple[float, float]) -> float:
        low, high = wedge
        mid = (low + high) / 2
        nearest = mid + ((angle - mid + math.pi) % _TWO_PI - math.pi)
        return min(high, max(low, nearest))

    def _nudge(
        self,
        tree: Dict[str, _TreeNode],
        node_angle: Dict[ModuleNode, float],
        node_radius: Dict[ModuleNode, float],
        neighbours: Dict[ModuleNode, List[ModuleNode]],
    ) -> Dict[ModuleNode, float]:
        pull = self._config.ring.edge_pull
        margin = self._config.ring.wedge_margin
        if pull <= 0 or self._config.ring.nudge_passes == 0:
            return node_angle

        bounds = self._leaf_bounds(tree, margin)
        if not bounds:
            return node_angle

        best = dict(node_angle)
        best_cost = self._edge_cost(best, node_radius, neighbours)
        for _ in range(self._config.ring.nudge_passes):
            candidate = dict(best)
            for module in sorted(bounds, key=lambda node: (node.module.qualified_name, node.ordinal)):
                target = self._circular_mean(
                    sum(math.cos(best[neighbour]) for neighbour in neighbours.get(module, ())),
                    sum(math.sin(best[neighbour]) for neighbour in neighbours.get(module, ())),
                )
                if target is None:
                    continue

                current = best[module]
                delta = math.atan2(math.sin(target - current), math.cos(target - current))
                low, high = bounds[module]
                candidate[module] = min(high, max(low, current + pull * delta))

            cost = self._edge_cost(candidate, node_radius, neighbours)
            if cost > best_cost - _EPSILON:
                break

            best, best_cost = candidate, cost

        return best

    @staticmethod
    def _leaf_bounds(tree: Dict[str, _TreeNode], margin: float) -> Dict[ModuleNode, Tuple[float, float]]:
        bounds: Dict[ModuleNode, Tuple[float, float]] = {}
        for branch in tree.values():
            if branch.children or not branch.modules:
                continue

            low = branch.wedge_start + margin
            high = branch.wedge_end - margin
            if high < low:
                low = high = (branch.wedge_start + branch.wedge_end) / 2

            for module in branch.modules:
                bounds[module] = (low, high)

        return bounds

    @staticmethod
    def _edge_cost(
        node_angle: Dict[ModuleNode, float],
        node_radius: Dict[ModuleNode, float],
        neighbours: Dict[ModuleNode, List[ModuleNode]],
    ) -> float:
        cost = 0.0
        for source, targets in neighbours.items():
            source_x = node_radius[source] * math.cos(node_angle[source])
            source_y = node_radius[source] * math.sin(node_angle[source])
            for target in targets:
                target_x = node_radius[target] * math.cos(node_angle[target])
                target_y = node_radius[target] * math.sin(node_angle[target])
                cost += math.hypot(source_x - target_x, source_y - target_y)

        return cost

    def _positions(
        self,
        node_angle: Dict[ModuleNode, float],
        node_radius: Dict[ModuleNode, float],
        rng: Random,
    ) -> Dict[ModuleNode, Position]:
        jitter = self._config.ring.jitter
        ring_spacing = self._config.ring.ring_spacing

        positions: Dict[ModuleNode, Position] = {}
        for module, angle in node_angle.items():
            radius = node_radius[module]
            if jitter > 0 and radius > 0:
                radius = max(0.0, radius + rng.uniform(-jitter, jitter) * ring_spacing)

            positions[module] = (radius * math.cos(angle), radius * math.sin(angle))

        return positions

    def _node_options(self, tree: Dict[str, _TreeNode], root: str) -> Dict[ModuleNode, Dict[str, Any]]:
        options: Dict[ModuleNode, Dict[str, Any]] = {}
        if self._config.relaxation.enabled and self._config.relaxation.anchor_centers:
            for module in tree[root].modules:
                options[module] = {"fixed": {"x": True, "y": True}}

        return options

    def _vis_patch(self) -> Dict[str, Any]:
        layout: Dict[str, Any] = {"hierarchical": {"enabled": False}}
        patch: Dict[str, Any] = {"layout": layout}

        relaxation = self._config.relaxation
        if not relaxation.enabled:
            patch["physics"] = {"enabled": False}
            return patch

        layout["randomSeed"] = self._config.ring.seed
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

    @staticmethod
    def _circular_mean(sum_cos: float, sum_sin: float) -> Optional[float]:
        if abs(sum_cos) < _EPSILON and abs(sum_sin) < _EPSILON:
            return None

        return math.atan2(sum_sin, sum_cos) % _TWO_PI


def module_layout_from_config(config: LayoutConfig) -> Optional[GraphLayout[ModuleNode]]:
    match config.mode:
        case "package_ring":
            return PackageRingLayout(config)
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
