import ast
from typing import Callable, Optional, cast


def is_elif_branch(orelse: list[ast.stmt]) -> bool:
    return len(orelse) == 1 and isinstance(orelse[0], ast.If)


def get_next_elif(current: ast.If) -> Optional[ast.If]:
    if current.orelse and is_elif_branch(current.orelse):
        return cast(ast.If, current.orelse[0])

    return None


def is_or_clause(node: ast.expr) -> bool:
    return isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or)


def is_and_clause(node: ast.expr) -> bool:
    return isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And)


def any_branch_excludes(if_node: ast.If, check_negation: Callable[[ast.expr], bool]) -> bool:
    current: Optional[ast.If] = if_node

    while current:
        if check_negation(current.test):
            return True

        current = get_next_elif(current)

    return False


def contains_negation(
    node: ast.expr,
    is_negated: Callable[[ast.expr], bool],
    contains_in_or_chain: Callable[[ast.BoolOp], bool],
) -> bool:
    if is_negated(node):
        return True

    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return contains_in_or_chain(node)

    return False


def contains_in_chain(node: ast.BoolOp, predicate: Callable[[ast.expr], bool]) -> bool:
    for value in node.values:
        if predicate(value):
            return True

    return False
