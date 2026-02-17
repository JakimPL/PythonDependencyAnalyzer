import ast
from typing import Optional


def simplify_comparison(node: ast.expr) -> Optional[bool]:
    """
    Simplify common comparison patterns to True/False/None.
    Returns None if we can't determine the value.
    """
    if isinstance(node, ast.Constant):
        return bool(node.value)

    if isinstance(node, ast.Compare):
        is_type_checking_left = isinstance(node.left, ast.Name) and node.left.id == "TYPE_CHECKING"

        is_bool_type_checking = (
            isinstance(node.left, ast.Call)
            and isinstance(node.left.func, ast.Name)
            and node.left.func.id == "bool"
            and len(node.left.args) == 1
            and isinstance(node.left.args[0], ast.Name)
            and node.left.args[0].id == "TYPE_CHECKING"
        )

        if (is_type_checking_left or is_bool_type_checking) and len(node.ops) == 1 and len(node.comparators) == 1:
            op = node.ops[0]
            comparator = node.comparators[0]

            if isinstance(op, (ast.Eq, ast.Is)):
                if isinstance(comparator, ast.Constant) and comparator.value is True:
                    return True
                if isinstance(comparator, ast.Constant) and comparator.value is False:
                    return False

            if isinstance(op, (ast.NotEq, ast.IsNot)):
                if isinstance(comparator, ast.Constant) and comparator.value is False:
                    return True
                if isinstance(comparator, ast.Constant) and comparator.value is True:
                    return False

            if isinstance(op, ast.Gt):
                if isinstance(comparator, ast.Constant) and comparator.value == 0:
                    return True

            if isinstance(op, ast.Lt):
                if isinstance(comparator, ast.Constant) and comparator.value == 1:
                    return False

        if isinstance(node.left, ast.Constant) and len(node.ops) == 1:
            left_val = node.left.value
            comparator = node.comparators[0]
            if isinstance(comparator, ast.Constant):
                right_val = comparator.value
                op = node.ops[0]

                try:
                    if isinstance(op, ast.Gt):
                        return left_val > right_val
                    elif isinstance(op, ast.Lt):
                        return left_val < right_val
                    elif isinstance(op, ast.Eq):
                        return left_val == right_val
                    elif isinstance(op, ast.NotEq):
                        return left_val != right_val
                    elif isinstance(op, ast.GtE):
                        return left_val >= right_val
                    elif isinstance(op, ast.LtE):
                        return left_val <= right_val
                except TypeError:
                    return None

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "bool":
            if len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                if node.args[0].id == "TYPE_CHECKING":
                    return True

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        inner = simplify_comparison(node.operand)
        if inner is not None:
            return not inner

    return None


def contains_type_checking_in_and(node: ast.expr) -> bool:
    if isinstance(node, ast.Name) and node.id == "TYPE_CHECKING":
        return True

    if isinstance(node, ast.Compare):
        result = simplify_comparison(node)
        if result is True:
            if isinstance(node.left, ast.Name) and node.left.id == "TYPE_CHECKING":
                return True
            if (
                isinstance(node.left, ast.Call)
                and isinstance(node.left.func, ast.Name)
                and node.left.func.id == "bool"
                and len(node.left.args) == 1
                and isinstance(node.left.args[0], ast.Name)
                and node.left.args[0].id == "TYPE_CHECKING"
            ):
                return True

        return False

    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        has_type_checking = False
        for value in node.values:
            if isinstance(value, ast.Name) and value.id == "TYPE_CHECKING":
                has_type_checking = True
            elif isinstance(value, ast.Compare):
                if simplify_comparison(value) is True:
                    if isinstance(value.left, ast.Name) and value.left.id == "TYPE_CHECKING":
                        has_type_checking = True
                    elif (
                        isinstance(value.left, ast.Call)
                        and isinstance(value.left.func, ast.Name)
                        and value.left.func.id == "bool"
                        and len(value.left.args) == 1
                        and isinstance(value.left.args[0], ast.Name)
                        and value.left.args[0].id == "TYPE_CHECKING"
                    ):
                        has_type_checking = True

        return has_type_checking

    return False


def can_simplify_to_true(node: ast.expr) -> bool:
    result = simplify_comparison(node)
    return result is True


def contains_type_checking_negation(node: ast.expr) -> bool:
    """
    Check if a condition contains TYPE_CHECKING in a way that makes it False when TYPE_CHECKING is True.
    Examples:
    - not TYPE_CHECKING → True (negation)
    - not TYPE_CHECKING or something → True (in OR with negation)
    """
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        if isinstance(node.operand, ast.Name) and node.operand.id == "TYPE_CHECKING":
            return True

    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        for value in node.values:
            if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.Not):
                if isinstance(value.operand, ast.Name) and value.operand.id == "TYPE_CHECKING":
                    return True

    return False


def any_branch_excludes_type_checking(if_node: ast.If) -> bool:
    """
    Check if any if/elif branch is guaranteed True when TYPE_CHECKING is False.
    This means the else branch would only execute when TYPE_CHECKING is True.

    For example:
    - if some_condition: pass
    - elif not TYPE_CHECKING or another: pass
    - else: import  # type-checking only

    The elif is always True when TYPE_CHECKING is False, so else can only run when TYPE_CHECKING is True.
    """
    current = if_node

    while current:
        test = current.test

        if contains_type_checking_negation(test):
            return True

        if current.orelse and len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
            current = current.orelse[0]
        else:
            break

    return False


def is_type_checking_only(if_node: ast.If, in_else_branch: bool = False) -> bool:
    """
    Determine if an import in this If node is type-checking only.
    """
    if in_else_branch:
        return any_branch_excludes_type_checking(if_node)

    test = if_node.test

    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True

    simplified = simplify_comparison(test)
    if simplified is True:
        return contains_type_checking_in_and(test)

    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        return contains_type_checking_in_and(test)

    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
        return False

    return False
