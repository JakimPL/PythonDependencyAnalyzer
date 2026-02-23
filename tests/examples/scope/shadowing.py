"""
Test file for variable shadowing across different scope levels.
"""

from typing import Any


def risky_operation() -> None:
    pass


def risky() -> None:
    pass


def context() -> Any:
    return None


def something() -> Any:
    return None


shadowed_at_module = "module"


def shadowing_example() -> None:
    shadowed_name: Any = "outer"

    def nested_shadowing(shadowed_name: str) -> str:
        return shadowed_name

    if True:
        shadowed_name = "middle"

        def inner_nested() -> str:
            shadowed_name = "inner"
            return shadowed_name

    for shadowed_name in range(10):
        loop_local = shadowed_name

    try:
        risky_operation()
    except Exception as shadowed_name:
        exception_local = str(shadowed_name)


def shadowing_chain() -> str:
    shadowed_at_module = "function"

    def level1() -> str:
        shadowed_at_module = "level1"

        def level2() -> str:
            shadowed_at_module = "level2"

            def level3() -> str:
                shadowed_at_module = "level3"
                return shadowed_at_module

            return level3()

        return level2()

    return level1()


def overlapping_names_different_scopes() -> None:
    name: Any = "outer"

    for name in range(5):
        loop_name = name

    name = "reset"
    try:
        risky()
    except Exception as exception:
        exception_name = exception
        name = str(exception)

    with context() as context_value:
        context_name = context_value
        name = str(context_value)

    match something():
        case x if (name := x) > 0:
            match_name = name


class ShadowingInClass:
    class_variable = "class"

    def method_with_shadowing(self, class_variable: str) -> str:
        local_variable = class_variable
        return local_variable
