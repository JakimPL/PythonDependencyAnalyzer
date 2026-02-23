"""
Test file for control flow constructs: for, with, try-except, match statements.
"""

from typing import Any


def dangerous_operation() -> None:
    pass


def handle_value_error(error: Any) -> None:
    pass


def handle_general_error(error: Any) -> None:
    pass


def log_exception(exception: Any) -> None:
    pass


class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


def compute_value() -> int:
    return 0


def use_value(value: Any) -> None:
    pass


def read_line() -> str:
    return ""


def process_line(line: str) -> None:
    pass


def perform_operation() -> Any:
    return None


def for_loop_examples() -> None:
    for simple_target in range(10):
        loop_variable = simple_target

    for tuple_target1, tuple_target2 in [(1, 2), (3, 4)]:
        first_target = tuple_target1
        second_target = tuple_target2

    for (nested_target1, nested_target2), nested_target3 in [((1, 2), 3)]:
        first_nested = nested_target1
        second_nested = nested_target2
        third_nested = nested_target3

    dict_items = {"a": 1, "b": 2}
    for dict_key, dict_value in dict_items.items():
        key_variable = dict_key
        value_variable = dict_value


def with_statement_examples() -> None:
    with open("file.txt") as file_handle:
        content = file_handle.read()

    with open("file1.txt") as f1, open("file2.txt") as f2:
        combined = f1.read() + f2.read()


def exception_handler_examples() -> None:
    try:
        dangerous_operation()
    except ValueError as value_error:
        handle_value_error(value_error)
    except (TypeError, KeyError) as general_error:
        handle_general_error(general_error)
    except Exception as exception:
        log_exception(exception)


def match_statement_examples(value: Any) -> Any:
    result: Any = None
    match value:
        case int(matched_int):
            result = matched_int * 2
        case str(matched_string) if len(matched_string) > 5:
            result = matched_string.upper()
        case [first_item, *rest_items]:
            result = first_item + sum(rest_items)
        case {"key": matched_value, **other_items}:
            result = matched_value
        case (tuple_a, tuple_b, tuple_c):
            result = tuple_a + tuple_b + tuple_c
        case Point(x=point_x, y=point_y):
            result = point_x + point_y
        case _ as default_match:
            result = default_match

    return result


def walrus_operator_examples() -> None:
    if (walrus_variable := compute_value()) > 10:
        use_value(walrus_variable)

    while (line := read_line()) != "":
        process_line(line)


def combined_control_flow() -> None:
    outer_variable = "outer"

    for loop_variable in range(10):
        if loop_variable > 5:
            inner_if_variable = loop_variable

    result: Any = None
    try:
        result = perform_operation()
    except ValueError as exception:
        error_handler = str(exception)
        result = None

    match result:
        case int(matched_integer):
            match_result = matched_integer
        case _:
            match_result = 0
