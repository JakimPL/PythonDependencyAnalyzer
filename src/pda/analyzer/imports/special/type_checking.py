import ast
from typing import Any, Optional

from pda.analyzer.imports.special.common import (
    any_branch_excludes,
    contains_in_chain,
    contains_negation,
    is_and_clause,
    is_or_clause,
)


def is_type_checking_only(if_node: ast.If, in_else_branch: bool = False) -> bool:
    if in_else_branch:
        return any_branch_excludes_type_checking(if_node)

    test = if_node.test

    if is_type_checking_name(test):
        return True

    if _is_simplified_to_true_with_type_checking(test):
        return True

    if is_and_clause(test):
        return _contains_type_checking_in_and(test)

    if is_or_clause(test):
        return False

    return False


def any_branch_excludes_type_checking(if_node: ast.If) -> bool:
    return any_branch_excludes(if_node, contains_type_checking_negation)


def contains_type_checking_negation(node: ast.expr) -> bool:
    return contains_negation(node, _is_negated_type_checking, _contains_negated_type_checking_in_or_chain)


def simplify_comparison(node: ast.expr) -> Optional[bool]:
    if isinstance(node, ast.Constant):
        return bool(node.value)

    if isinstance(node, ast.Compare):
        if is_type_checking_reference(node.left) and len(node.ops) == 1 and len(node.comparators) == 1:
            return _simplify_type_checking_comparison(node.ops[0], node.comparators[0])

        if isinstance(node.left, ast.Constant) and len(node.ops) == 1 and isinstance(node.comparators[0], ast.Constant):
            return _evaluate_constant_comparison(node.left.value, node.ops[0], node.comparators[0].value)

    if is_bool_type_checking_call(node):
        return True

    return None


def is_type_checking_name(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == "TYPE_CHECKING"


def is_bool_type_checking_call(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "bool"
        and len(node.args) == 1
        and is_type_checking_name(node.args[0])
    )


def is_type_checking_reference(node: ast.expr) -> bool:
    return is_type_checking_name(node) or is_bool_type_checking_call(node)


def _simplify_type_checking_comparison(op: ast.cmpop, comparator: ast.expr) -> Optional[bool]:
    if not isinstance(comparator, ast.Constant):
        return None

    if isinstance(op, (ast.Eq, ast.Is)):
        if comparator.value is True:
            return True
        if comparator.value is False:
            return False

    if isinstance(op, (ast.NotEq, ast.IsNot)):
        if comparator.value is False:
            return True
        if comparator.value is True:
            return False

    if isinstance(op, ast.Gt) and comparator.value == 0:
        return True

    if isinstance(op, ast.Lt) and comparator.value == 1:
        return False

    return None


def _evaluate_constant_comparison(left_val: Any, op: ast.cmpop, right_val: Any) -> Optional[bool]:
    comparison: Optional[bool] = None
    try:
        match op:
            case ast.Gt():
                comparison = left_val > right_val
            case ast.Lt():
                comparison = left_val < right_val
            case ast.Eq():
                comparison = left_val == right_val
            case ast.NotEq():
                comparison = left_val != right_val
            case ast.GtE():
                comparison = left_val >= right_val
            case ast.LtE():
                comparison = left_val <= right_val

    except TypeError:
        return None

    return comparison


def _is_simplified_type_checking_comparison(node: ast.Compare) -> bool:
    result = simplify_comparison(node)
    return result is True and is_type_checking_reference(node.left)


def _contains_type_checking_in_and_chain(node: ast.BoolOp) -> bool:
    return contains_in_chain(
        node,
        lambda v: is_type_checking_name(v)
        or (isinstance(v, ast.Compare) and _is_simplified_type_checking_comparison(v)),
    )


def _contains_type_checking_in_and(node: ast.expr) -> bool:
    if is_type_checking_name(node):
        return True

    if isinstance(node, ast.Compare):
        return _is_simplified_type_checking_comparison(node)

    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        return _contains_type_checking_in_and_chain(node)

    return False


def _is_negated_type_checking(node: ast.expr) -> bool:
    return isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and is_type_checking_name(node.operand)


def _contains_negated_type_checking_in_or_chain(node: ast.BoolOp) -> bool:
    return contains_in_chain(node, _is_negated_type_checking)


def _is_simplified_to_true_with_type_checking(node: ast.expr) -> bool:
    simplified = simplify_comparison(node)
    return simplified is True and _contains_type_checking_in_and(node)
