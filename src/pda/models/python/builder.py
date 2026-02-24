import ast
from typing import Any, Optional

from pda.models.python.node import ASTNode
from pda.types import ASTT


def to_ast_node(node: ASTT, parent: Optional[ASTNode[Any]] = None) -> ASTNode[ASTT]:
    return ASTNode[ASTT](node, parent=parent)


def build_ast_tree(node: ASTT, parent: Optional[ASTNode[Any]] = None) -> ASTNode[ASTT]:
    ast_node: ASTNode[ASTT] = to_ast_node(node, parent=parent)
    if ast_node is None:
        return None

    for child in ast.iter_child_nodes(node):
        build_ast_tree(child, parent=ast_node)

    return ast_node
