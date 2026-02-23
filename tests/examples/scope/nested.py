"""Test deeply nested scope structures with multiple scope levels."""

from typing import Any, Callable, Tuple


def perform_operation() -> Any:
    return None


def everything_combined() -> Callable[[str], str]:
    outer_variable = "outer"
    x, y = 1, 2

    def nested_decorated(parameter: str) -> str:
        nested_local = parameter
        nested_lambda = lambda a: a + nested_local + outer_variable

        nested_comprehension = [item for item in range(10) if (filtered := item * 2) > 5]

        class NestedClass:
            nested_class_variable = nested_local

            def nested_class_method(self) -> Callable[[], Tuple[str, str, str]]:
                nested_method_local = self.nested_class_variable
                deeply_nested_lambda = lambda: (
                    nested_method_local,
                    nested_local,
                    outer_variable,
                )
                return deeply_nested_lambda

        for loop_variable in nested_comprehension:
            if loop_variable > 10:
                inner_if_variable = loop_variable

        result: Any = None
        try:
            result = perform_operation()
        except ValueError as exception:
            error_handler = str(exception)
            result = 0

        match result:
            case int(matched_integer):
                match_result = matched_integer
            case _:
                match_result = 0

        return str(match_result)

    return nested_decorated
