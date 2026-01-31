from __future__ import annotations

import ast
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, DefaultDict, Deque, Dict, Optional, Set, TypeAlias

from fda.analyzer.node import ASTNodeWrapper

NodeWrapperMap: TypeAlias = Dict[ast.AST, ASTNodeWrapper[Any]]
FunctionCalls: TypeAlias = DefaultDict[ASTNodeWrapper[ast.FunctionDef], Set[ASTNodeWrapper[ast.Call]]]
SimplifiedFunctionCalls: TypeAlias = Dict[str, Set[str]]


class FunctionDependencyAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.nodes: NodeWrapperMap = {}
        self.function_calls: FunctionCalls = defaultdict(set)
        self.root: Optional[ASTNodeWrapper[Any]] = None

    def get_wrapper(self, node: ast.AST) -> ASTNodeWrapper[Any]:
        return self.nodes[node]

    def generic_visit(self, node: ast.AST) -> None:
        pass

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # pylint: disable=invalid-name
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # pylint: disable=invalid-name
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # pylint: disable=invalid-name
        wrapper = self.nodes[node]
        if wrapper.parent and wrapper.functions:
            last_function = wrapper.functions[-1]
            self.function_calls[last_function].add(wrapper)

        self.generic_visit(node)

    def get_simplified_function_calls(self) -> SimplifiedFunctionCalls:
        simplified: SimplifiedFunctionCalls = defaultdict(set)
        for caller, callees in self.function_calls.items():
            for callee in callees:
                simplified[caller.full_path].add(callee.full_path)

        return simplified

    def analyze(self, tree: ast.AST) -> SimplifiedFunctionCalls:
        self.root = ASTNodeWrapper[Any](tree, filepath=self.filepath)
        self.nodes = {tree: self.root}
        nodes: Deque[ASTNodeWrapper[Any]] = deque([self.root])
        while nodes:
            node = nodes.popleft()
            self.visit(node.ast_node)
            for child in ast.iter_child_nodes(node.ast_node):
                child_wrapper = ASTNodeWrapper[Any](child, filepath=self.filepath, parent=node)
                self.nodes[child] = child_wrapper
                nodes.append(child_wrapper)

        return self.get_simplified_function_calls()
