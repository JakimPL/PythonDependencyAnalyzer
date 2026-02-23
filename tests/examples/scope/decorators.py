"""
Test file for decorators and property decorators.
"""

from typing import Any, Callable


def prepare() -> Any:
    return None


def cleanup() -> Any:
    return None


def decorator_registry(func: Callable[..., Any]) -> Callable[..., Any]:
    decorator_local = "decorator"

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        wrapper_local = "wrapper"
        before_call = prepare()
        result = func(*args, **kwargs)
        after_call = cleanup()
        return result

    return wrapper


@decorator_registry
def decorated_function(decorated_parameter: str) -> str:
    decorated_local = "decorated"
    return f"{decorated_parameter}{decorated_local}"


class DecoratedClass:
    @decorator_registry
    def decorated_method(self, parameter: str) -> str:
        method_local = parameter
        return method_local

    @staticmethod
    @decorator_registry
    def multi_decorated_static(parameter: int) -> int:
        static_local = parameter * 2
        return static_local


class PropertyExamples:
    def __init__(self) -> None:
        self._private_variable = "private"

    @property
    def read_only_property(self) -> str:
        property_getter_local = self._private_variable
        return property_getter_local

    @property
    def read_write_property(self) -> str:
        return self._private_variable

    @read_write_property.setter
    def read_write_property(self, value: str) -> None:
        setter_local = value.upper()
        self._private_variable = setter_local


def chained_decorators_example() -> Callable[[str], str]:
    def decorator_one(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper_one(*args: Any, **kwargs: Any) -> Any:
            wrapper_one_local = "decorator_one"
            return func(*args, **kwargs)

        return wrapper_one

    def decorator_two(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper_two(*args: Any, **kwargs: Any) -> Any:
            wrapper_two_local = "decorator_two"
            return func(*args, **kwargs)

        return wrapper_two

    @decorator_one
    @decorator_two
    def chained_decorated(parameter: str) -> str:
        chained_local = parameter
        return chained_local

    return chained_decorated
