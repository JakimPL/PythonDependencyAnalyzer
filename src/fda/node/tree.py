from __future__ import annotations

import ast
from collections import deque
from pathlib import Path
from typing import Any, Deque, List

from fda.node.ast_node import ASTNode
from fda.node.types import NodeMapping
from fda.parser.parser import parse_python_file


class AST:
    """
    Wraps an AST as a anytree tree structure for convenient traversal and analysis.
    """

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.mapping: NodeMapping = {}
        self.root: ASTNode[ast.Module] = self.analyze()

    def _analyze_node(self, wrapper: ASTNode[Any]) -> List[ASTNode[Any]]:
        nodes: List[ASTNode[Any]] = []
        for child in ast.iter_child_nodes(wrapper.ast):
            child_wrapper = ASTNode[Any](child, filepath=self.filepath, parent=wrapper)
            self.mapping[child] = child_wrapper
            nodes.append(child_wrapper)

        return nodes

    def analyze(self) -> ASTNode[ast.Module]:
        tree = parse_python_file(self.filepath)
        self.root = ASTNode[Any](tree, filepath=self.filepath)
        self.mapping = {tree: self.root}
        wrappers: Deque[ASTNode[Any]] = deque([self.root])
        while wrappers:
            wrapper = wrappers.popleft()
            wrappers.extend(self._analyze_node(wrapper))

        return self.root
