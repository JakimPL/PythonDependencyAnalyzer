from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Dict, Optional, Set, TypeAlias, Union

from pda.models.paths.node import PathNode
from pda.models.python.builder import build_ast_tree
from pda.models.python.graph import ASTGraph
from pda.models.python.node import ASTNode
from pda.parser import parse_python_file
from pda.structures import Forest
from pda.types import Pathlike

PathNodes: TypeAlias = Union[
    Iterable[Pathlike],
    Iterable[PathNode],
]


class ASTForest(Forest[ASTNode[Any]]):
    def __init__(
        self,
        nodes: PathNodes,
    ) -> None:
        self._root_origins: Dict[ASTNode[Any], Path] = {}

        super().__init__(self._to_nodes(nodes))
        self._mapping: Dict[ast.AST, ASTNode[Any]] = self._get_node_mapping()

    def __getitem__(self, node: ast.AST) -> ASTNode[Any]:
        return self._mapping[node]

    def _to_nodes(self, items: PathNodes) -> Set[ASTNode[Any]]:
        node: ASTNode[Any]
        nodes: Set[ASTNode[Any]] = set()
        for item in items:
            if isinstance(item, ASTNode):
                nodes.add(item)
                continue

            if isinstance(item, PathNode):
                item = item.filepath

            if isinstance(item, (str, Path)):
                path = Path(item).resolve()
                tree = parse_python_file(path)
                node = build_ast_tree(tree)
                self._root_origins[node] = path
                nodes.add(node)
                continue

            raise TypeError(f"Unsupported node type: {type(item)}, expected str, Path, PathNode or ASTNode")

        return nodes

    def get_origin(self, node: ASTNode[Any]) -> Optional[Path]:
        """
        Get the origin file path for any node in the forest.

        Args:
            node: Any ASTNode in the forest.

        Returns:
            The Path where the node's root was parsed from, or None if not found.
        """
        return self._root_origins.get(node.root)

    @property
    def root_origins(self) -> Dict[ASTNode[Any], Path]:
        """
        Get the mapping of root nodes to their origin file paths.

        Returns:
            Dictionary mapping root ASTNodes to their source file Paths.
        """
        return self._root_origins.copy()

    def _get_node_mapping(self) -> Dict[ast.AST, ASTNode[Any]]:
        return {node.ast: node for node in self}

    def get(self, node: ast.AST) -> Optional[ASTNode[Any]]:
        return self._mapping.get(node)

    @property
    def graph(self) -> ASTGraph:
        return ASTGraph(self.nx)
