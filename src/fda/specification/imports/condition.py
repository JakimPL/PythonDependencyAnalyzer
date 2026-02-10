from enum import StrEnum


class ImportCondition(StrEnum):
    NONE = "none"
    IF = "if"
    ELIF = "elif"
    ELSE = "else"
    CASE = "case"
    TRY = "try"
    EXCEPT = "except"
