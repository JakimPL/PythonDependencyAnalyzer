"""Test calling undefined/unimported functions and variables for name resolution testing.

Note: This file intentionally contains references to undefined names.
These are used to test the name resolution system's ability to detect
and report unresolved references. All mypy errors in this file are expected.
"""

from typing import Any, Callable


def call_undefined_function() -> None:
    undefined_function_name()


def call_undefined_variable() -> None:
    result = undefined_variable_name


def call_undefined_in_expression() -> None:
    result = undefined_name + 42


def call_undefined_in_comprehension() -> None:
    results = [undefined_in_comp(x) for x in range(10)]


def call_undefined_method() -> None:
    class TestClass:
        def existing_method(self) -> None:
            self.undefined_method()


def call_undefined_nested() -> None:
    def outer() -> None:
        def inner() -> None:
            undefined_nested_call()

        inner()

    outer()


def access_undefined_in_closure() -> Callable[[], Any]:
    def closure_function() -> Any:
        return undefined_closure_variable

    return closure_function


def call_undefined_with_arguments() -> None:
    undefined_function_with_args(1, 2, key="value")


def access_undefined_attribute() -> None:
    import sys

    result = sys.undefined_attribute


def call_unimported_module() -> None:
    result = unimported_module.function()


def call_partially_qualified() -> None:
    import os

    result = os.undefined_submodule.function()
