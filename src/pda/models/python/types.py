import ast
from typing import Any, Dict, TypeAlias, Union, cast, overload

from pda.models.python.node import ASTNode
from pda.types import ASTT

NodeMapping: TypeAlias = Dict[ast.AST, ASTNode[Any]]


@overload
def get_ast(node: ASTT) -> ASTT: ...


@overload
def get_ast(node: ASTNode[ASTT]) -> ASTT: ...


def get_ast(node: Union[ASTT, ASTNode[ASTT]]) -> ASTT:
    ast_node: ASTT
    if isinstance(node, ast.AST):
        return cast(ASTT, node)

    if not isinstance(node, ASTNode):
        raise TypeError(f"Expected node to be either ast.AST or ASTNode, got {type(node)}")

    ast_node = node.ast
    return ast_node
