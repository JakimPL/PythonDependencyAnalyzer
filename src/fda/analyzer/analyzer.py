from __future__ import annotations

import ast
from collections import defaultdict

from fda.node import ASTNodeWrapper, CallResolutions, FunctionCalls, NodeWrapperMap, SimplifiedFunctionCalls


class FunctionDependencyAnalyzer(ast.NodeVisitor):
    def __init__(self, wrappers: NodeWrapperMap, call_resolutions: CallResolutions) -> None:
        self.wrappers = wrappers
        self.call_resolutions = call_resolutions

        self.function_calls: FunctionCalls = defaultdict(set)

    def _clear(self) -> None:
        self.function_calls.clear()

    def visit_Call(self, node: ast.Call) -> None:  # pylint: disable=invalid-name
        wrapper = self.wrappers[node]
        if wrapper.parent and wrapper.functions:
            last_function = wrapper.functions[-1]
            self.function_calls[last_function].add(wrapper)

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

    def analyze(self, tree: ast.AST) -> SimplifiedFunctionCalls:
        self._clear()
        self.visit(tree)
        return self._get_simplified_function_calls()
