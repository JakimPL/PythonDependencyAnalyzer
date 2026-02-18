import ast
from dataclasses import dataclass
from typing import Tuple

import pytest

from pda.analyzer.imports.special.type_checking import is_type_checking_only


class TestIfTypeChecking:
    @dataclass
    class TestCase:
        __test__ = False

        label: str
        expected: Tuple[bool, ...]
        code: str

    test_cases = [
        TestCase(
            label="direct_type_checking",
            expected=(True,),
            code="""
if TYPE_CHECKING:
    pass
            """,
        ),
        TestCase(
            label="direct_not_type_checking",
            expected=(False,),
            code="""
if not TYPE_CHECKING:
    pass
            """,
        ),
        TestCase(
            label="and_clause",
            expected=(True,),
            code="""
if True and TYPE_CHECKING == True:
    pass
            """,
        ),
        TestCase(
            label="complex_and_clause",
            expected=(True, True),
            code="""
if 1 > 0 and TYPE_CHECKING is True and some_condition:
    pass
elif TYPE_CHECKING:
    pass
""",
        ),
        TestCase(
            label="bool_cast",
            expected=(True,),
            code="""
if bool(TYPE_CHECKING) > 0:
    pass
""",
        ),
        TestCase(
            label="elif_with_or",
            expected=(
                False,
                False,
                True,
            ),
            code="""
if some_condition:
    pass
elif not TYPE_CHECKING or another_condition:
    pass
else:
    pass
""",
        ),
        TestCase(
            label="or_with_type_checking",
            expected=(False,),
            code="""
if some_condition or TYPE_CHECKING:
    pass
""",
        ),
        TestCase(
            label="or_with_type_checking_in_and",
            expected=(False,),
            code="""
if False or TYPE_CHECKING:
    pass
""",
        ),
        TestCase(
            label="complex_condition_with_type_checking",
            expected=(False,),
            code="""
if some_condition or (TYPE_CHECKING and another_condition):
    pass
""",
        ),
        TestCase(
            label="not_type_checking_in_if",
            expected=(
                False,
                False,
            ),
            code="""
if not TYPE_CHECKING and some_condition:
    pass
else:
    pass
""",
        ),
        TestCase(
            label="type_checking_in_if_and_elif",
            expected=(
                False,
                False,
                False,
            ),
            code="""
if TYPE_CHECKING or some_condition:
    pass
elif another_condition:
    pass
else:
    pass
""",
        ),
    ]

    def _find_if_nodes(self, root: ast.Module) -> Tuple[ast.If, ...]:
        return tuple(node for node in root.body if isinstance(node, ast.If))

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    def test_type_checking(self, test_case: TestCase) -> None:
        root = ast.parse(test_case.code)
        if_nodes = self._find_if_nodes(root)

        if not len(if_nodes) == 1:
            raise ValueError(f"Expected exactly 1 If node in test case, found {len(if_nodes)}")

        results = []
        if_node = if_nodes[0]
        current = if_node
        while current:
            results.append(is_type_checking_only(current, in_else_branch=False))

            if current.orelse:
                if len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
                    current = current.orelse[0]
                else:
                    results.append(is_type_checking_only(if_node, in_else_branch=True))
                    break
            else:
                break

        assert tuple(results) == test_case.expected, f"Expected: {test_case.expected}, got: {tuple(results)}"
