import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional

from pyvis.network import Network

from pda.config.pyvis.config import PyVisConfig
from pda.config.pyvis.options import PDAOptions
from pda.structures.graph.base import Graph
from pda.structures.node.types import NodeT
from pda.types.nested_defaultdict import NestedDefaultDict, nested_defaultdict


class PyVisConverter(Generic[NodeT]):
    config: PyVisConfig

    def __init__(
        self,
        *,
        config_path: Path = PyVisConfig.default_path(),
        network_kwargs: Optional[Dict[str, Any]] = None,
        vis_options: Optional[Dict[str, Dict[str, Any]]] = None,
        auto_adjust_spacing: Optional[bool] = None,
    ) -> None:
        self.load_config(
            config_path,
            network_kwargs=network_kwargs,
            vis_options=vis_options,
            auto_adjust_spacing=auto_adjust_spacing,
        )

    def __call__(self, graph: Graph[NodeT]) -> Network:
        nodes = sorted(graph.nodes)
        options = self._prepare_vis_options(nodes)

        network_kwargs = {**self.network_kwargs}
        pyvis_graph = Network(directed=True, **network_kwargs)
        node_map = self._add_nodes(pyvis_graph, nodes)
        self._add_edges(pyvis_graph, graph, node_map)

        if options:
            pyvis_graph.set_options(json.dumps(options))

        return pyvis_graph

    def load_config(
        self,
        config_path: Path,
        *,
        network_kwargs: Optional[Dict[str, Any]] = None,
        vis_options: Optional[Dict[str, Dict[str, Any]]] = None,
        auto_adjust_spacing: Optional[bool] = None,
    ) -> None:
        default = PyVisConfig.default()
        if not config_path.exists():
            self.config = default
            return

        config: PyVisConfig = PyVisConfig.load(config_path)
        config_dict: Dict[str, Dict[str, Any]] = {**default.model_dump(), **config.model_dump()}
        vis: Dict[str, Dict[str, Any]] = vis_options if vis_options is not None else config_dict.get("vis", {})
        network: Dict[str, Any] = network_kwargs if network_kwargs is not None else config_dict.get("network", {})
        pda_options: PDAOptions = PDAOptions(**config_dict.get("pda", {}))
        if auto_adjust_spacing is not None:
            pda_options.auto_adjust_spacing = auto_adjust_spacing

        self.config = PyVisConfig(
            pda=pda_options,
            network=network,
            vis=vis,
        )

    @property
    def vis_options(self) -> NestedDefaultDict[Any]:
        return nested_defaultdict(self.config.vis)

    @property
    def network_kwargs(self) -> Dict[str, Any]:
        return self.config.network or {}

    @property
    def auto_adjust_spacing(self) -> bool:
        return self.config.pda.auto_adjust_spacing

    @property
    def ratio(self) -> float:
        return self.config.pda.ratio

    def _prepare_vis_options(self, nodes: List[NodeT]) -> Dict[str, Dict[str, Any]]:
        options: Dict[str, Dict[str, Any]] = deepcopy(self.vis_options)

        if self.auto_adjust_spacing and nodes:
            level_separation = self._calculate_level_separation(nodes)
            options["layout"]["hierarchical"]["levelSeparation"] = level_separation

        return options

    def _add_nodes(self, pyvis_graph: Network, nodes: List[NodeT]) -> Dict[NodeT, int]:
        node_map: Dict[NodeT, int] = {}
        for i, node in enumerate(nodes):
            node_map[node] = i
            node_props = self._build_node_properties(node)
            pyvis_graph.add_node(i, **node_props)

        return node_map

    def _build_node_properties(self, node: NodeT) -> Dict[str, Any]:
        node_properties = self.vis_options["nodes"]
        props = {
            "label": node.label,
            "title": node.details or node.label,
            "level": node.level,
            "group": node.group if node.group else "",
            **node_properties,
        }

        return props

    def _add_edges(
        self,
        pyvis_graph: Network,
        graph: Graph[NodeT],
        node_map: Dict[NodeT, int],
    ) -> None:
        for from_node, to_node in graph.edges:
            edge_properties = self._build_edge_properties(graph, from_node, to_node)
            pyvis_graph.add_edge(
                node_map[from_node],
                node_map[to_node],
                **edge_properties,
            )

    def _build_edge_properties(self, graph: Graph[NodeT], from_node: NodeT, to_node: NodeT) -> Dict[str, Any]:
        edge_properties = self.vis_options["edges"]
        return {
            "title": graph.edge_label(from_node, to_node),
            **edge_properties,
        }

    def _calculate_level_separation(self, nodes: List[NodeT]) -> int:
        base_node_spacing = self.vis_options["layout"]["hierarchical"]["levelSeparation"] or 150
        if not nodes:
            return base_node_spacing

        levels = [node.level for node in nodes]
        max_level = max(levels, default=0)

        nodes_per_level: Dict[int, int] = {}
        for level in levels:
            nodes_per_level[level] = nodes_per_level.get(level, 0) + 1

        max_width = max(nodes_per_level.values(), default=1)
        depth = max_level + 1

        ratio = self.ratio
        ratio = 1.0 / ratio if self.vis_options["layout"]["hierarchical"]["direction"] in ("LR", "RL") else ratio
        estimated_width = max_width * base_node_spacing
        target_height = estimated_width * ratio

        if depth > 1:
            level_separation = max(base_node_spacing, int(target_height / depth))
        else:
            level_separation = base_node_spacing

        return level_separation
