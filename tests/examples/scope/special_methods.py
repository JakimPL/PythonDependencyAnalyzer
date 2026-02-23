"""
Test file for special/dunder methods and context managers.
"""

from typing import Any, Union


class ClassWithDunderMethods:
    def __init__(self, value: Any) -> None:
        self.value = value

    def __str__(self) -> str:
        string_local = str(self.value)
        return string_local

    def __repr__(self) -> str:
        repr_local = f"ClassWithDunderMethods({self.value!r})"
        return repr_local

    def __call__(self, argument: Any) -> Any:
        call_local = self.value + argument
        return call_local

    def __enter__(self) -> Any:
        enter_local = self.value
        return enter_local

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        exit_local = "exiting"
        return None

    def __getitem__(self, key: Any) -> Any:
        getitem_local = self.value
        return getitem_local[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        setitem_local = value
        self.value[key] = setitem_local


class ContextManagerExample:
    def __enter__(self) -> str:
        enter_variable = "entering"
        return enter_variable

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Union[bool, None]:
        exit_variable = "exiting"
        return None


def using_context_managers() -> None:
    with ContextManagerExample() as context_variable:
        usage_local = context_variable
