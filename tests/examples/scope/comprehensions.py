"""
Test file for comprehensions (list, dict, set, generator) and their scope isolation.
"""

from typing import Any, Dict, List, Union

items = [1, 2, 3]


def transform(item: Any) -> Any:
    return item


def method_with_comprehensions(comprehension_parameter: List[int]) -> Dict[int, int]:
    list_comprehension = [item * 2 for item in comprehension_parameter]
    set_comprehension = {item for item in comprehension_parameter if item > 0}
    dict_comprehension = {key: value for key, value in enumerate(comprehension_parameter)}
    generator_expression = (item**2 for item in comprehension_parameter)
    nested_comprehension = [[x * y for x in range(3)] for y in comprehension_parameter]
    return dict_comprehension


def comprehension_edge_cases() -> None:
    outer_scope_variable = 10
    comprehension_with_outer_access = [x + outer_scope_variable for x in range(5)]
    nested_comprehension = [[x * y for x in range(3)] for y in range(4)]
    comprehension_with_condition = [x for x in range(10) if x % 2 == 0]
    comprehension_with_multiple_loops = [(x, y) for x in range(3) for y in range(3) if x != y]
    dict_comprehension_with_destructuring = {key: value for key, value in enumerate(["a", "b", "c"])}


def comprehension_variable_isolation() -> None:
    leak_test = "outer"
    comprehension_result = [leak_test for leak_test in range(10)]
    assert leak_test == "outer", "Comprehension variable should not leak!"
    generator_result = (leak_test for leak_test in range(5))
    assert leak_test == "outer", "Generator expression variable should not leak!"


class ComprehensionAccessingClassScope:
    class_variable_for_comprehension = 100

    def get_comprehension(self) -> List[int]:
        return [self.class_variable_for_comprehension + i for i in range(5)]


class ClassWithComprehensionInBody:
    class_list_comprehension = [i for i in range(10)]
    class_dict_comprehension = {i: i**2 for i in range(5)}


def comprehension_in_default_args(data: Union[List[int], None] = None) -> None:
    if data is None:
        data = [x * 2 for x in range(5)]

    data_local = data


def comprehension_with_walrus() -> None:
    results = [result for item in items if (result := transform(item)) is not None]
    collected_results = results
