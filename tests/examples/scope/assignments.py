"""
Test file for all assignment variations and unpacking patterns.
"""

from typing import Any, Dict, List, Tuple, Union

x, y, z = 1, 2, 3
(a, b), c = (4, 5), 6
nested_unpack: Tuple[Tuple[int, int], int] = ((7, 8), 9)
(d, e), f = nested_unpack

dict_unpack = {"key1": 1, "key2": 2, "key3": 3}
key1, key2, key3 = dict_unpack.values()

dict_for_items = {"alpha": 10, "beta": 20, "gamma": 30}
(first_key, first_value), *remaining_items = dict_for_items.items()

module_variable = "initial"
module_variable += "_modified"

annotated_variable: str = "annotated"


def assignment_variations() -> None:
    single_assign = 1
    multi_target = 2
    another_target = multi_target

    x, y = 3, 4
    [list_x, list_y] = [5, 6]
    (nested_a, nested_b), nested_c = ((7, 8), 9)

    complex_dict: Dict[str, List[int]] = {"items": [1, 2, 3]}
    (dict_key, dict_values), *remaining_dict_items = complex_dict.items()


def augmented_assignment_examples() -> None:
    counter = 0
    counter += 1
    counter *= 2
    counter -= 5
    counter //= 2
    counter %= 3


def multiple_assignment_targets() -> None:
    a = b = c = 10
    x = y = z = []
    temp_list: List[Any] = []
    x = y = z = temp_list


def starred_expressions() -> None:
    first_item, *middle_items, last_item = range(10)
    *beginning_items, end_item = [1, 2, 3, 4, 5]

    dict_data = {"a": 1, "b": 2, "c": 3, "d": 4}
    (first_key, first_value), *rest_dict_items = dict_data.items()


def dictionary_unpacking() -> None:
    dict1 = {"a": 1, "b": 2}
    dict2 = {"c": 3, "d": 4}

    merged_dict = {**dict1, **dict2}
    dict_with_updates = {**dict1, "b": 20, "e": 5}


def tuple_unpacking_in_loop() -> None:
    data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]

    for person_dict in data:
        name, age = person_dict["name"], person_dict["age"]
        person_name = name
        person_age = age


def nested_dictionary_structure() -> None:
    nested_dict: Dict[str, Any] = {"outer": {"inner1": 1, "inner2": 2}, "other": 3}

    outer_value: Dict[str, int] = nested_dict["outer"]
    inner1, inner2 = outer_value["inner1"], outer_value["inner2"]


def function_with_annotations() -> None:
    annotated_local: str = "annotated"
    annotated_integer: int = 42
    annotated_list: List[str] = ["a", "b"]
    annotated_dict: Dict[str, int] = {"key": 1}

    def annotated_nested(parameter: int) -> str:
        result: str = str(parameter)
        return result


def default_arguments_with_mutable(
    mutable_default: Union[List[int], None] = None,
    dict_default: Union[Dict[str, int], None] = None,
) -> None:
    if mutable_default is None:
        mutable_default = []
    if dict_default is None:
        dict_default = {}

    local_list = mutable_default
    local_dict = dict_default
