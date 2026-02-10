import ast
from typing import Any, Dict, TypeAlias, TypeVar, Union, cast, overload

from fda.node.ast_node import ASTNode

NodeMapping: TypeAlias = Dict[ast.AST, ASTNode[Any]]
NodeT = TypeVar("NodeT", bound=ast.AST)
Node: TypeAlias = Union[NodeT, ASTNode[NodeT]]


@overload
def get_ast(node: NodeT) -> NodeT: ...


@overload
def get_ast(node: ASTNode[NodeT]) -> NodeT: ...


def get_ast(node: Node[NodeT]) -> NodeT:
    ast_node: NodeT
    if isinstance(node, ast.AST):
        return cast(NodeT, node)

    if not isinstance(node, ASTNode):
        raise TypeError(f"Expected node to be either ast.AST or ASTNode, got {type(node)}")

    ast_node = node.ast
    return ast_node
