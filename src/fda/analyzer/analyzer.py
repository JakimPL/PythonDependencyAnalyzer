from __future__ import annotations

import ast
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, DefaultDict, Deque, Dict, List, Optional, Set, TypeAlias

from fda.analyzer.node import ASTNodeWrapper
from fda.analyzer.scope import Scope

NodeWrapperMap: TypeAlias = Dict[ast.AST, ASTNodeWrapper[Any]]
FunctionCalls: TypeAlias = DefaultDict[ASTNodeWrapper[ast.FunctionDef], Set[ASTNodeWrapper[ast.Call]]]
SimplifiedFunctionCalls: TypeAlias = Dict[str, Set[str]]
CallResolutions: TypeAlias = Dict[ASTNodeWrapper[ast.Call], ASTNodeWrapper[Any]]


class FunctionDependencyAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

        self.root: Optional[ASTNodeWrapper[Any]] = None
        self.wrappers: NodeWrapperMap = {}

        self.function_calls: FunctionCalls = defaultdict(set)
        self.call_resolutions: CallResolutions = {}

        self.current_scope: Optional[Scope] = None
        self.scopes: Dict[ASTNodeWrapper[Any], Scope] = {}
        self.call_scopes: Dict[ASTNodeWrapper[ast.Call], Scope] = {}

    def _clear(self) -> None:
        self.root = None
        self.wrappers.clear()

        self.function_calls.clear()
        self.call_resolutions.clear()

        self.current_scope = None
        self.scopes.clear()
        self.call_scopes.clear()

    def _get_wrapper(self, node: ast.AST) -> ASTNodeWrapper[Any]:
        return self.wrappers[node]

    def _enter_scope(self, wrapper: ASTNodeWrapper[Any], name: str) -> None:
        if self.current_scope:
            self.current_scope.define(name, wrapper)

        self.current_scope = Scope(parent=self.current_scope)
        self.scopes[wrapper] = self.current_scope

    def _exit_scope(self) -> None:
        if self.current_scope:
            self.current_scope = self.current_scope.parent

    def _resolve_name(self, wrapper: ASTNodeWrapper[Any]) -> None:
        call_name = wrapper.ast_name
        if self.current_scope:
            resolved = self.current_scope.resolve(call_name)
            if resolved:
                self.call_resolutions[wrapper] = resolved

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
        if wrapper.parent and wrapper.functions:
            last_function = wrapper.functions[-1]
            self.function_calls[last_function].add(wrapper)
            if self.current_scope:
                self.call_scopes[wrapper] = self.current_scope

        super().generic_visit(node)

    def _simplify_function_calls(self, callee: ASTNodeWrapper[ast.Call]) -> str:
        resolved = self.call_resolutions.get(callee)
        if resolved:
            return resolved.full_path

        return f"<unresolved:{callee.ast_name}>"

    def _get_simplified_function_calls(self) -> SimplifiedFunctionCalls:
        simplified: SimplifiedFunctionCalls = defaultdict(set)
        for caller, callees in self.function_calls.items():
            simplified[caller.full_path] = set(map(self._simplify_function_calls, callees))

        return simplified

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
        for callees in self.function_calls.values():
            for callee in callees:
                call_scope = self.call_scopes.get(callee)
                if call_scope:
                    call_name = callee.ast_name
                    resolved = call_scope.resolve(call_name)
                    if resolved:
                        self.call_resolutions[callee] = resolved

    def analyze(self, tree: ast.AST) -> SimplifiedFunctionCalls:
        self._clear()
        self._analyze_tree(tree)
        self._collect_definitions(tree)
        self._resolve_calls()
        return self._get_simplified_function_calls()
