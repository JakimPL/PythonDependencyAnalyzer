"""
Test file for basic scope hierarchy: MODULE, CLASS, FUNCTION scopes.
Tests nested classes, methods, and basic scope relationships.
"""

from typing import Callable

module_variable = "module_level"
module_constant: int = 42


def module_function(param1: str, param2: int = 10) -> str:
    local_variable = "local"
    return f"{param1}{param2}{local_variable}"


annotated_variable: str = "annotated"


class OuterClass:
    class_variable = "class_level"
    class_constant: int = 100

    def __init__(self, init_parameter: str) -> None:
        self.instance_variable = init_parameter
        self.another_variable = self.class_variable

    def method(self, method_parameter: str) -> str:
        method_local = "method_local"
        class_access = OuterClass.class_variable
        return f"{method_parameter}{method_local}{self.instance_variable}"

    @staticmethod
    def static_method(static_parameter: int) -> int:
        static_local = static_parameter * 2
        return static_local

    @classmethod
    def class_method(cls, class_method_parameter: str) -> str:
        class_method_local = cls.class_variable
        return f"{class_method_parameter}{class_method_local}"

    def method_with_nested_function(self, outer_parameter: str) -> Callable[[str], str]:
        outer_local = "outer"

        def nested_function(nested_parameter: str) -> str:
            nested_local = "nested"
            closure_access = outer_local
            parameter_access = outer_parameter
            return f"{nested_parameter}{nested_local}{closure_access}{parameter_access}"

        return nested_function

    class InnerClass:
        inner_class_variable = "inner"

        def __init__(self, inner_parameter: str) -> None:
            self.inner_instance_variable = inner_parameter

        def inner_method(self, inner_method_parameter: str) -> str:
            inner_method_local = self.inner_class_variable
            return f"{inner_method_parameter}{inner_method_local}"

        class DoublyNestedClass:
            doubly_nested_variable = "doubly_nested"

            def doubly_nested_method(self) -> str:
                return self.doubly_nested_variable


class ClassWithComplexNesting:
    class_level_variable = "class"

    def method_with_complex_nesting(self) -> Callable[[], Callable[[], tuple[str, str, str]]]:
        method_variable = "method"

        def nested_function() -> Callable[[], tuple[str, str, str]]:
            nested_variable = "nested_func"

            class LocalClass:
                local_class_variable = "local_class"

                def local_method(self) -> Callable[[], tuple[str, str, str]]:
                    local_method_variable = "local_method"
                    local_lambda = lambda: (
                        local_method_variable,
                        nested_variable,
                        method_variable,
                    )
                    return local_lambda

            return LocalClass().local_method()

        return nested_function


class EmptyClass:
    pass


class InheritanceExample(list[int]):
    def custom_method(self) -> int:
        custom_local = len(self)
        return custom_local


class MethodReturningNestedClass:
    def get_class(self, parameter: str) -> type:
        method_local = parameter

        class ReturnedClass:
            returned_class_variable = method_local

            def returned_method(self) -> str:
                return self.returned_class_variable

        return ReturnedClass
