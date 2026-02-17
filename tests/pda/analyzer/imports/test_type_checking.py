import ast
from dataclasses import dataclass
from typing import Tuple

import pytest

from pda.analyzer.imports.type_checking import is_type_checking_only


class TestIfTypeChecking:
    @dataclass
    class TestCase:
        __test__ = False

        label: str
        expected_type_checking: Tuple[bool, ...]
        code: str

    test_cases = [
        TestCase(
            label="direct_type_checking",
            expected_type_checking=(True,),
            code="""
if TYPE_CHECKING:
    from package.module import SomeType
            """,
        ),
        TestCase(
            label="direct_not_type_checking",
            expected_type_checking=(False,),
            code="""
if not TYPE_CHECKING:
    from package.module import SomeType
            """,
        ),
        TestCase(
            label="and_clause",
            expected_type_checking=(True,),
            code="""
if True and TYPE_CHECKING == True:
    from package.module import SomeTypeOnlyUsedInTypeChecking1
            """,
        ),
        TestCase(
            label="complex_and_clause",
            expected_type_checking=(True, True),
            code="""
if 1 > 0 and TYPE_CHECKING is True and some_condition:
    from package.module import SomeTypeOnlyUsedInTypeChecking2
elif TYPE_CHECKING:
    from package.module import SomeTypeOnlyUsedInTypeChecking3
""",
        ),
        TestCase(
            label="bool_cast",
            expected_type_checking=(True,),
            code="""
if bool(TYPE_CHECKING) > 0:
    from package.module import SomeTypeOnlyUsedInTypeChecking4
""",
        ),
        TestCase(
            label="elif_with_or",
            expected_type_checking=(
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
    from package.module import SomeTypeOnlyUsedInTypeChecking6
""",
        ),
        TestCase(
            label="or_with_type_checking",
            expected_type_checking=(False,),
            code="""
if some_condition or TYPE_CHECKING:
    from package.module import SomeTypeUsedInRuntime1
""",
        ),
        TestCase(
            label="or_with_type_checking_in_and",
            expected_type_checking=(False,),
            code="""
if False or TYPE_CHECKING:  # We won't evaluate conditions, so we a priori consider the import as used in runtime
    from package.module import SomeTypeUsedInRuntime2
""",
        ),
        TestCase(
            label="complex_condition_with_type_checking",
            expected_type_checking=(False,),
            code="""
if some_condition or (TYPE_CHECKING and another_condition):
    from package.module import SomeTypeUsedInRuntime3
""",
        ),
        TestCase(
            label="not_type_checking_in_if",
            expected_type_checking=(
                False,
                False,
            ),
            code="""
if not TYPE_CHECKING and some_condition:
    from package.module import SomeTypeUsedInRuntime4
else:
    from package.module import SomeTypeUsedInRuntime5
""",
        ),
        TestCase(
            label="type_checking_in_if_and_elif",
            expected_type_checking=(
                False,
                False,
                False,
            ),
            code="""
if TYPE_CHECKING or some_condition:
    pass
elif another_condition:
    from package.module import SomeTypeUsedInRuntime6
else:
    from package.module import SomeTypeUsedInRuntime7
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

        assert (
            tuple(results) == test_case.expected_type_checking
        ), f"Expected: {test_case.expected_type_checking}, got: {tuple(results)}"
