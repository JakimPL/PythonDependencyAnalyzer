import ast

from pda.analyzer.imports.special.common import (
    any_branch_excludes,
    contains_in_chain,
    contains_negation,
    is_and_clause,
    is_or_clause,
)


def is_main_guard_only(if_node: ast.If, in_else_branch: bool = False) -> bool:
    if in_else_branch:
        return any_branch_excludes_main_guard(if_node)

    test = if_node.test

    if isinstance(test, ast.Compare) and is_main_guard_comparison(test):
        return True

    if is_and_clause(test):
        return _contains_main_guard_in_and(test)

    if is_or_clause(test):
        return False

    return False


def any_branch_excludes_main_guard(if_node: ast.If) -> bool:
    return any_branch_excludes(if_node, contains_main_guard_negation)


def contains_main_guard_negation(node: ast.expr) -> bool:
    return contains_negation(node, _is_negated_main_guard, _contains_negated_main_guard_in_or_chain)


def is_main_guard_comparison(node: ast.Compare) -> bool:
    return _is_main_guard_comparison_with_op(node, ast.Eq)


def is_negated_main_guard_comparison(node: ast.Compare) -> bool:
    return _is_main_guard_comparison_with_op(node, ast.NotEq)


def _is_name_dunder_name(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == "__name__"


def _is_main_string(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value == "__main__"


def _is_main_guard_comparison_with_op(node: ast.Compare, op_type: type[ast.cmpop]) -> bool:
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return False

    op = node.ops[0]
    if not isinstance(op, op_type):
        return False

    left_is_name = _is_name_dunder_name(node.left)
    right_is_main = _is_main_string(node.comparators[0])

    left_is_main = _is_main_string(node.left)
    right_is_name = _is_name_dunder_name(node.comparators[0])

    return (left_is_name and right_is_main) or (left_is_main and right_is_name)


def _contains_main_guard_in_and_chain(node: ast.BoolOp) -> bool:
    return contains_in_chain(node, lambda v: isinstance(v, ast.Compare) and is_main_guard_comparison(v))


def _contains_main_guard_in_and(node: ast.expr) -> bool:
    if isinstance(node, ast.Compare):
        return is_main_guard_comparison(node)

    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        return _contains_main_guard_in_and_chain(node)

    return False


def _is_negated_main_guard(node: ast.expr) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        if isinstance(node.operand, ast.Compare):
            return is_main_guard_comparison(node.operand)

    if isinstance(node, ast.Compare):
        return is_negated_main_guard_comparison(node)

    return False


def _contains_negated_main_guard_in_or_chain(node: ast.BoolOp) -> bool:
    return contains_in_chain(node, _is_negated_main_guard)
