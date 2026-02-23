"""
Test file for function parameter variations and *args/**kwargs.
"""

from typing import Any, Dict


def parameter_variations(
    positional_only1: int,
    positional_only2: str,
    /,
    regular_parameter1: int,
    regular_parameter2: str = "default",
    *args: Any,
    keyword_only1: int,
    keyword_only2: str = "kw_default",
    **kwargs: Any,
) -> None:
    parameter_local = positional_only1 + regular_parameter1 + keyword_only1
    args_count = len(args)
    kwargs_count = len(kwargs)


def function_with_star_args(*args: Any, **kwargs: Any) -> None:
    args_local = len(args)
    kwargs_local = len(kwargs)

    for argument in args:
        argument_item = argument

    for key, value in kwargs.items():
        keyword_key = key
        keyword_value = value


def function_accepting_kwargs(**kwargs: Any) -> Dict[str, Any]:
    kwargs_collected = kwargs
    return kwargs_collected


def call_with_unpacking() -> None:
    dict1 = {"a": 1, "b": 2}
    dict2 = {"c": 3, "d": 4}

    result = function_accepting_kwargs(**dict1, **dict2)
    final_result = result
