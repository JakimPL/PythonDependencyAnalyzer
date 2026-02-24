from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

import pytest

from pda.analyzer.scope import ScopeAnalyzer
from pda.models.scope import ScopeNode
from pda.specification import ScopeType


@dataclass
class SymbolExpectation:
    name: str
    scope_path: List[str]
    fqn: str
    origin_file: str


@dataclass
class ScopeExpectation:
    scope_path: List[str]
    scope_type: ScopeType
    symbol_count: int
    parent_path: Optional[List[str]]


def build_and_collect(filepath: Path) -> ScopeNode[Any]:
    analyzer = ScopeAnalyzer()
    scope_forest = analyzer([filepath])
    roots = list(scope_forest.roots)
    assert len(roots) == 1
    return roots[0]


def find_scope_by_path(root: ScopeNode[Any], path: List[str]) -> ScopeNode[Any]:
    if not path:
        return root

    for segment in path:
        found = None
        for child in root.children:
            if segment in child.label:
                found = child
                break
        assert found is not None, f"Could not find scope '{segment}' in path {path}"
        root = found

    return root


class TestAssignmentsCollector:

    @pytest.fixture
    def module_scope(self) -> ScopeNode[Any]:
        filepath = Path("tests/examples/scope/assignments.py")
        return build_and_collect(filepath)

    def test_assignments_complete_expectations(self, module_scope: ScopeNode[Any]) -> None:
        scope_expectations = [
            ScopeExpectation([], ScopeType.MODULE, 28, None),
            ScopeExpectation(["assignment_variations"], ScopeType.FUNCTION, 13, []),
            ScopeExpectation(["augmented_assignment_examples"], ScopeType.FUNCTION, 1, []),
            ScopeExpectation(["multiple_assignment_targets"], ScopeType.FUNCTION, 7, []),
            ScopeExpectation(["starred_expressions"], ScopeType.FUNCTION, 6, []),
            ScopeExpectation(["dictionary_unpacking"], ScopeType.FUNCTION, 4, []),
            ScopeExpectation(["tuple_unpacking_in_loop"], ScopeType.FUNCTION, 6, []),
            ScopeExpectation(["nested_dictionary_structure"], ScopeType.FUNCTION, 4, []),
            ScopeExpectation(["function_with_annotations"], ScopeType.FUNCTION, 5, []),
            ScopeExpectation(
                ["function_with_annotations", "annotated_nested"], ScopeType.FUNCTION, 2, ["function_with_annotations"]
            ),
            ScopeExpectation(["default_arguments_with_mutable"], ScopeType.FUNCTION, 4, []),
        ]

        symbol_expectations = [
            SymbolExpectation("x", [], "x", "assignments.py"),
            SymbolExpectation("y", [], "y", "assignments.py"),
            SymbolExpectation("z", [], "z", "assignments.py"),
            SymbolExpectation("a", [], "a", "assignments.py"),
            SymbolExpectation("b", [], "b", "assignments.py"),
            SymbolExpectation("c", [], "c", "assignments.py"),
            SymbolExpectation("nested_unpack", [], "nested_unpack", "assignments.py"),
            SymbolExpectation("d", [], "d", "assignments.py"),
            SymbolExpectation("e", [], "e", "assignments.py"),
            SymbolExpectation("f", [], "f", "assignments.py"),
            SymbolExpectation("dict_unpack", [], "dict_unpack", "assignments.py"),
            SymbolExpectation("key1", [], "key1", "assignments.py"),
            SymbolExpectation("key2", [], "key2", "assignments.py"),
            SymbolExpectation("key3", [], "key3", "assignments.py"),
            SymbolExpectation("dict_for_items", [], "dict_for_items", "assignments.py"),
            SymbolExpectation("first_key", [], "first_key", "assignments.py"),
            SymbolExpectation("first_value", [], "first_value", "assignments.py"),
            SymbolExpectation("remaining_items", [], "remaining_items", "assignments.py"),
            SymbolExpectation("module_variable", [], "module_variable", "assignments.py"),
            SymbolExpectation("annotated_variable", [], "annotated_variable", "assignments.py"),
            SymbolExpectation("assignment_variations", [], "assignment_variations", "assignments.py"),
            SymbolExpectation("augmented_assignment_examples", [], "augmented_assignment_examples", "assignments.py"),
            SymbolExpectation("multiple_assignment_targets", [], "multiple_assignment_targets", "assignments.py"),
            SymbolExpectation("starred_expressions", [], "starred_expressions", "assignments.py"),
            SymbolExpectation("dictionary_unpacking", [], "dictionary_unpacking", "assignments.py"),
            SymbolExpectation("tuple_unpacking_in_loop", [], "tuple_unpacking_in_loop", "assignments.py"),
            SymbolExpectation("nested_dictionary_structure", [], "nested_dictionary_structure", "assignments.py"),
            SymbolExpectation("function_with_annotations", [], "function_with_annotations", "assignments.py"),
            SymbolExpectation("default_arguments_with_mutable", [], "default_arguments_with_mutable", "assignments.py"),
            SymbolExpectation(
                "single_assign", ["assignment_variations"], "assignment_variations.single_assign", "assignments.py"
            ),
            SymbolExpectation(
                "multi_target", ["assignment_variations"], "assignment_variations.multi_target", "assignments.py"
            ),
            SymbolExpectation(
                "another_target", ["assignment_variations"], "assignment_variations.another_target", "assignments.py"
            ),
            SymbolExpectation("x", ["assignment_variations"], "assignment_variations.x", "assignments.py"),
            SymbolExpectation("y", ["assignment_variations"], "assignment_variations.y", "assignments.py"),
            SymbolExpectation("list_x", ["assignment_variations"], "assignment_variations.list_x", "assignments.py"),
            SymbolExpectation("list_y", ["assignment_variations"], "assignment_variations.list_y", "assignments.py"),
            SymbolExpectation(
                "nested_a", ["assignment_variations"], "assignment_variations.nested_a", "assignments.py"
            ),
            SymbolExpectation(
                "nested_b", ["assignment_variations"], "assignment_variations.nested_b", "assignments.py"
            ),
            SymbolExpectation(
                "nested_c", ["assignment_variations"], "assignment_variations.nested_c", "assignments.py"
            ),
            SymbolExpectation(
                "complex_dict", ["assignment_variations"], "assignment_variations.complex_dict", "assignments.py"
            ),
            SymbolExpectation(
                "dict_key", ["assignment_variations"], "assignment_variations.dict_key", "assignments.py"
            ),
            SymbolExpectation(
                "dict_values", ["assignment_variations"], "assignment_variations.dict_values", "assignments.py"
            ),
            SymbolExpectation(
                "remaining_dict_items",
                ["assignment_variations"],
                "assignment_variations.remaining_dict_items",
                "assignments.py",
            ),
            SymbolExpectation(
                "counter", ["augmented_assignment_examples"], "augmented_assignment_examples.counter", "assignments.py"
            ),
            SymbolExpectation("a", ["multiple_assignment_targets"], "multiple_assignment_targets.a", "assignments.py"),
            SymbolExpectation("b", ["multiple_assignment_targets"], "multiple_assignment_targets.b", "assignments.py"),
            SymbolExpectation("c", ["multiple_assignment_targets"], "multiple_assignment_targets.c", "assignments.py"),
            SymbolExpectation("x", ["multiple_assignment_targets"], "multiple_assignment_targets.x", "assignments.py"),
            SymbolExpectation("y", ["multiple_assignment_targets"], "multiple_assignment_targets.y", "assignments.py"),
            SymbolExpectation("z", ["multiple_assignment_targets"], "multiple_assignment_targets.z", "assignments.py"),
            SymbolExpectation(
                "temp_list", ["multiple_assignment_targets"], "multiple_assignment_targets.temp_list", "assignments.py"
            ),
            SymbolExpectation(
                "first_item", ["starred_expressions"], "starred_expressions.first_item", "assignments.py"
            ),
            SymbolExpectation("last_item", ["starred_expressions"], "starred_expressions.last_item", "assignments.py"),
            SymbolExpectation("end_item", ["starred_expressions"], "starred_expressions.end_item", "assignments.py"),
            SymbolExpectation("dict_data", ["starred_expressions"], "starred_expressions.dict_data", "assignments.py"),
            SymbolExpectation("first_key", ["starred_expressions"], "starred_expressions.first_key", "assignments.py"),
            SymbolExpectation(
                "first_value", ["starred_expressions"], "starred_expressions.first_value", "assignments.py"
            ),
            SymbolExpectation("dict1", ["dictionary_unpacking"], "dictionary_unpacking.dict1", "assignments.py"),
            SymbolExpectation("dict2", ["dictionary_unpacking"], "dictionary_unpacking.dict2", "assignments.py"),
            SymbolExpectation(
                "merged_dict", ["dictionary_unpacking"], "dictionary_unpacking.merged_dict", "assignments.py"
            ),
            SymbolExpectation(
                "dict_with_updates",
                ["dictionary_unpacking"],
                "dictionary_unpacking.dict_with_updates",
                "assignments.py",
            ),
            SymbolExpectation("data", ["tuple_unpacking_in_loop"], "tuple_unpacking_in_loop.data", "assignments.py"),
            SymbolExpectation(
                "person_dict", ["tuple_unpacking_in_loop"], "tuple_unpacking_in_loop.person_dict", "assignments.py"
            ),
            SymbolExpectation("name", ["tuple_unpacking_in_loop"], "tuple_unpacking_in_loop.name", "assignments.py"),
            SymbolExpectation("age", ["tuple_unpacking_in_loop"], "tuple_unpacking_in_loop.age", "assignments.py"),
            SymbolExpectation(
                "person_name", ["tuple_unpacking_in_loop"], "tuple_unpacking_in_loop.person_name", "assignments.py"
            ),
            SymbolExpectation(
                "person_age", ["tuple_unpacking_in_loop"], "tuple_unpacking_in_loop.person_age", "assignments.py"
            ),
            SymbolExpectation(
                "nested_dict",
                ["nested_dictionary_structure"],
                "nested_dictionary_structure.nested_dict",
                "assignments.py",
            ),
            SymbolExpectation(
                "outer_value",
                ["nested_dictionary_structure"],
                "nested_dictionary_structure.outer_value",
                "assignments.py",
            ),
            SymbolExpectation(
                "inner1", ["nested_dictionary_structure"], "nested_dictionary_structure.inner1", "assignments.py"
            ),
            SymbolExpectation(
                "inner2", ["nested_dictionary_structure"], "nested_dictionary_structure.inner2", "assignments.py"
            ),
            SymbolExpectation(
                "annotated_local",
                ["function_with_annotations"],
                "function_with_annotations.annotated_local",
                "assignments.py",
            ),
            SymbolExpectation(
                "annotated_integer",
                ["function_with_annotations"],
                "function_with_annotations.annotated_integer",
                "assignments.py",
            ),
            SymbolExpectation(
                "annotated_list",
                ["function_with_annotations"],
                "function_with_annotations.annotated_list",
                "assignments.py",
            ),
            SymbolExpectation(
                "annotated_dict",
                ["function_with_annotations"],
                "function_with_annotations.annotated_dict",
                "assignments.py",
            ),
            SymbolExpectation(
                "annotated_nested",
                ["function_with_annotations"],
                "function_with_annotations.annotated_nested",
                "assignments.py",
            ),
            SymbolExpectation(
                "parameter",
                ["function_with_annotations", "annotated_nested"],
                "function_with_annotations.annotated_nested.parameter",
                "assignments.py",
            ),
            SymbolExpectation(
                "result",
                ["function_with_annotations", "annotated_nested"],
                "function_with_annotations.annotated_nested.result",
                "assignments.py",
            ),
            SymbolExpectation(
                "mutable_default",
                ["default_arguments_with_mutable"],
                "default_arguments_with_mutable.mutable_default",
                "assignments.py",
            ),
            SymbolExpectation(
                "dict_default",
                ["default_arguments_with_mutable"],
                "default_arguments_with_mutable.dict_default",
                "assignments.py",
            ),
            SymbolExpectation(
                "local_list",
                ["default_arguments_with_mutable"],
                "default_arguments_with_mutable.local_list",
                "assignments.py",
            ),
            SymbolExpectation(
                "local_dict",
                ["default_arguments_with_mutable"],
                "default_arguments_with_mutable.local_dict",
                "assignments.py",
            ),
        ]

        for scope_exp in scope_expectations:
            scope = find_scope_by_path(module_scope, scope_exp.scope_path)

            assert (
                scope.scope_type == scope_exp.scope_type
            ), f"Scope {scope_exp.scope_path} has type {scope.scope_type}, expected {scope_exp.scope_type}"

            actual_count = len(scope.symbols)
            assert (
                actual_count == scope_exp.symbol_count
            ), f"Scope {scope_exp.scope_path} has {actual_count} symbols, expected {scope_exp.symbol_count}"

            if scope_exp.parent_path is None:
                assert scope.parent is None, f"Scope {scope_exp.scope_path} should have no parent"
            else:
                assert scope.parent is not None, f"Scope {scope_exp.scope_path} should have a parent"
                expected_parent = find_scope_by_path(module_scope, scope_exp.parent_path)
                assert scope.parent == expected_parent, f"Scope {scope_exp.scope_path} has wrong parent"

        for sym_exp in symbol_expectations:
            scope = find_scope_by_path(module_scope, sym_exp.scope_path)

            assert sym_exp.name in scope.symbols, f"Symbol '{sym_exp.name}' not found in scope {sym_exp.scope_path}"

            symbol = scope.symbols[sym_exp.name]

            assert (
                symbol.fqn == sym_exp.fqn
            ), f"Symbol '{sym_exp.name}' has FQN '{symbol.fqn}', expected '{sym_exp.fqn}'"

            assert symbol.origin is not None, f"Symbol '{sym_exp.name}' has no origin"
            assert (
                symbol.origin.name == sym_exp.origin_file
            ), f"Symbol '{sym_exp.name}' has origin '{symbol.origin.name}', expected '{sym_exp.origin_file}'"

            assert symbol.node is not None, f"Symbol '{sym_exp.name}' has no AST node"

            assert symbol.span is not None, f"Symbol '{sym_exp.name}' has no source span"
            assert symbol.span.start_line > 0, f"Symbol '{sym_exp.name}' has invalid start line"
            assert symbol.span.start_col >= 0, f"Symbol '{sym_exp.name}' has invalid start column"
