from __future__ import annotations

import ast
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from fda.node import ASTNodeWrapper, CallResolutions, NodeWrapperMap
from fda.resolver.scope import Scope


class NameResolver(ast.NodeVisitor):
    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

        self.root: Optional[ASTNodeWrapper[Any]] = None
        self.wrappers: NodeWrapperMap = {}

        self.call_resolutions: CallResolutions = {}

        self.current_scope: Optional[Scope] = None
        self.scopes: Dict[ASTNodeWrapper[Any], Scope] = {}
        self.call_scopes: Dict[ASTNodeWrapper[ast.Call], Scope] = {}

    def _clear(self) -> None:
        self.root = None
        self.wrappers.clear()

        self.call_resolutions.clear()

        self.current_scope = None
        self.scopes.clear()
        self.call_scopes.clear()

    def _enter_scope(self, wrapper: ASTNodeWrapper[Any], name: str) -> None:
        if self.current_scope:
            self.current_scope.define(name, wrapper)

        self.current_scope = Scope(parent=self.current_scope)
        self.scopes[wrapper] = self.current_scope

    def _exit_scope(self) -> None:
        if self.current_scope:
            self.current_scope = self.current_scope.parent

    def _visit_with_scope(self, node: ast.AST) -> None:
        wrapper = self.wrappers[node]
        self._enter_scope(wrapper, wrapper.ast_name)
        super().generic_visit(node)
        self._exit_scope()

    def visit_Module(self, node: ast.Module) -> None:  # pylint: disable=invalid-name
        wrapper = self.wrappers[node]
        self.current_scope = Scope()
        self.scopes[wrapper] = self.current_scope
        super().generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # pylint: disable=invalid-name
        self._visit_with_scope(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # pylint: disable=invalid-name
        self._visit_with_scope(node)

    def visit_Call(self, node: ast.Call) -> None:  # pylint: disable=invalid-name
        wrapper = self.wrappers[node]
        if self.current_scope:
            self.call_scopes[wrapper] = self.current_scope

        super().generic_visit(node)

    def _analyze_node(self, wrapper: ASTNodeWrapper[Any]) -> List[ASTNodeWrapper[Any]]:
        nodes: List[ASTNodeWrapper[Any]] = []
        for child in ast.iter_child_nodes(wrapper.ast_node):
            child_wrapper = ASTNodeWrapper[Any](child, filepath=self.filepath, parent=wrapper)
            self.wrappers[child] = child_wrapper
            nodes.append(child_wrapper)

        return nodes

    def _analyze_tree(self, tree: ast.AST) -> None:
        self.root = ASTNodeWrapper[Any](tree, filepath=self.filepath)
        self.wrappers = {tree: self.root}
        wrappers: Deque[ASTNodeWrapper[Any]] = deque([self.root])
        while wrappers:
            wrapper = wrappers.popleft()
            wrappers.extend(self._analyze_node(wrapper))

    def _collect_definitions(self, tree: ast.AST) -> None:
        self.visit(tree)

    def _resolve_calls(self) -> None:
        for callee, call_scope in self.call_scopes.items():
            call_name = callee.ast_name
            resolved = call_scope.resolve(call_name)
            if resolved:
                self.call_resolutions[callee] = resolved

    def resolve(self, tree: ast.AST) -> tuple[NodeWrapperMap, CallResolutions]:
        self._clear()
        self._analyze_tree(tree)
        self._collect_definitions(tree)
        self._resolve_calls()
        return self.wrappers, self.call_resolutions
