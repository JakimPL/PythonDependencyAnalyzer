from enum import StrEnum


class ScopeType(StrEnum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    COMPREHENSION = "comprehension"
    LAMBDA = "lambda"
