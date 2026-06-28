import json
import warnings
from pathlib import Path
from typing import Any, Dict, Generic, List, Literal, Optional, Union, overload

from bs4 import BeautifulSoup, Tag
from pyvis.network import Network

from pda.config import LayoutConfig, PyVisConfig, Theme
from pda.exceptions import PDAGraphLayoutWarning
from pda.structures.graph.base import Graph
from pda.structures.graph.layout import GraphLayout, LayoutResult
from pda.structures.node.types import NodeT
from pda.types.nested_defaultdict import NestedDefaultDict, nested_defaultdict


class PyVisConverter(Generic[NodeT]):
    config: PyVisConfig

    def __init__(
        self,
        *,
        config_path: Path = PyVisConfig.default_path(),
        theme: Theme = "light",
        network_kwargs: Optional[Dict[str, Any]] = None,
        vis_options: Optional[Dict[str, Dict[str, Any]]] = None,
        layout: Optional[GraphLayout[NodeT]] = None,
    ) -> None:
        self.load_config(
            config_path,
            theme=theme,
            network_kwargs=network_kwargs,
            vis_options=vis_options,
        )
        self.layout: Optional[GraphLayout[NodeT]] = layout

    @overload
    def __call__(self, graph: Graph[NodeT], *, html: Literal[False] = False, **kwargs: Any) -> Network: ...

    @overload
    def __call__(self, graph: Graph[NodeT], *, html: Literal[True], **kwargs: Any) -> str: ...

    def __call__(
        self,
        graph: Graph[NodeT],
        *,
        html: bool = False,
        **kwargs: Any,
    ) -> Union[str, Network]:
        if self.layout is None and graph.has_cycles:
            warnings.warn(
                "Graph contains cycles; the hierarchical layout may render them poorly. "
                "Consider the 'package_ring' layout.",
                PDAGraphLayoutWarning,
            )

        result = self.layout.compute(graph) if self.layout is not None else None
        network = self._build_network(graph, result, **kwargs)
        self._set_network_options(network, result)

        if html:
            return self.to_html(network)

        return network

    def to_html(self, network: Network) -> str:
        html: str = network.generate_html(".temp.html")
        return self._inject_background_color(html)

    def load_config(
        self,
        config_path: Path,
        *,
        theme: Theme = "light",
        network_kwargs: Optional[Dict[str, Any]] = None,
        vis_options: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        default = PyVisConfig.default(theme=theme)
        if not config_path.exists():
            self.config = default
            return

        config: PyVisConfig = PyVisConfig.load(config_path, theme=theme)
        config_dict: Dict[str, Any] = {**default.model_dump(), **config.model_dump()}
        vis: Dict[str, Dict[str, Any]] = vis_options if vis_options is not None else config_dict.get("vis", {})
        network: Dict[str, Any] = network_kwargs if network_kwargs is not None else config_dict.get("network", {})
        layout: Dict[str, Any] = config_dict.get("layout", {})

        self.config = PyVisConfig(
            network=network,
            vis=vis,
            layout=LayoutConfig(**layout),
        )

    @property
    def vis_options(self) -> NestedDefaultDict[Any]:
        return nested_defaultdict(self.config.vis)

    @property
    def network_kwargs(self) -> Dict[str, Any]:
        return self.config.network or {}

    def _build_network(
        self,
        graph: Graph[NodeT],
        result: Optional[LayoutResult[NodeT]] = None,
        **kwargs: Any,
    ) -> Network:
        nodes = sorted(graph.nodes)
        network_kwargs = self.network_kwargs
        pyvis_graph = Network(directed=True, **network_kwargs, **kwargs)
        node_map = self._add_nodes(pyvis_graph, nodes, result)
        self._add_edges(pyvis_graph, graph, node_map)
        return pyvis_graph

    def _set_network_options(self, network: Network, result: Optional[LayoutResult[NodeT]] = None) -> None:
        options: Dict[str, Any] = dict(self.vis_options)
        if result is not None:
            options = self._merge_options(options, result.vis_options_patch)

        network.set_options(json.dumps(options))

    def _add_nodes(
        self,
        pyvis_graph: Network,
        nodes: List[NodeT],
        result: Optional[LayoutResult[NodeT]] = None,
    ) -> Dict[NodeT, int]:
        node_map: Dict[NodeT, int] = {}
        for i, node in enumerate(nodes):
            node_map[node] = i
            node_props = self._build_node_properties(node, result)
            pyvis_graph.add_node(i, **node_props)

        return node_map

    def _build_node_properties(self, node: NodeT, result: Optional[LayoutResult[NodeT]] = None) -> Dict[str, Any]:
        node_properties = self.vis_options["nodes"]
        props: Dict[str, Any] = {
            **node_properties,
            "label": node.label,
            "title": node.details or node.label,
            "level": node.level,
            "group": node.group if node.group else "",
        }

        if not node.available:
            props["opacity"] = 0.45
            shape_properties = {**props.get("shapeProperties", {}), "borderDashes": [6, 4]}
            props["shapeProperties"] = shape_properties

        if result is not None and node in result.positions:
            x, y = result.positions[node]
            props["x"] = x
            props["y"] = y
            props.update(result.node_options.get(node, {}))

        return props

    @staticmethod
    def _merge_options(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = dict(base)
        for key, value in patch.items():
            existing = merged.get(key)
            if isinstance(existing, dict) and isinstance(value, dict):
                merged[key] = PyVisConverter._merge_options(existing, value)
            else:
                merged[key] = value

        return merged

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

    def _inject_background_color(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        head: Optional[Tag] = soup.head
        if head is None:
            raise ValueError("Generated HTML is missing a <head> element.")

        network_config = self.network_kwargs
        style_tag = soup.new_tag("style")
        style_tag.string = f"""
        body {{
            background-color: {network_config.get("bgcolor", "#ffffff")};
        }}

        .card, #mynetwork {{
            border: none !important;
        }}
        """

        head.append(style_tag)
        return str(soup)
