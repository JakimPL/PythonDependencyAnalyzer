"""
Test file for lambda expressions, closures, and nested function scopes.
"""

from typing import Callable, Generator, Tuple


def method_with_lambda(lambda_parameter: int) -> Callable[[int], int]:
    lambda_outer = 10
    lambda_result = lambda x: x + lambda_outer + lambda_parameter
    return lambda_result


def lambda_examples() -> None:
    simple_lambda = lambda x: x * 2
    multi_parameter_lambda = lambda a, b, c: a + b * c
    lambda_with_default = lambda x, y=10: x + y

    outer_variable = 100
    lambda_closure = lambda x: x + outer_variable
    nested_lambda = lambda x: (lambda y: x + y)


def closures_with_different_captures() -> Tuple[Callable[[], int], Callable[[], int], Callable[[], None]]:
    counter = 0

    def increment() -> int:
        nonlocal counter
        counter += 1
        return counter

    def decrement() -> int:
        nonlocal counter
        counter -= 1
        return counter

    def reset() -> None:
        nonlocal counter
        counter = 0

    return increment, decrement, reset


def function_returning_lambda() -> Callable[[int], int]:
    outer_value = 42
    return lambda x: x + outer_value


def generator_function(n: int) -> Generator[int, None, None]:
    generator_local = 0
    for i in range(n):
        yield_value = generator_local + i
        yield yield_value
        generator_local += 1


class ClassLevelLambda:
    class_lambda = lambda self, x: x * 2
    class_lambda_with_closure = (lambda y: (lambda x: x + y))(10)


def complex_nested_closures() -> Callable[[str], str]:
    outer_variable = "outer"
    x, y = 1, 2

    def nested_function(parameter: str) -> str:
        nested_local = parameter
        nested_lambda = lambda a: a + nested_local + outer_variable

        def deeply_nested() -> str:
            deeply_nested_local = "deep"
            return deeply_nested_local + nested_local + outer_variable

        return deeply_nested()

    return nested_function
