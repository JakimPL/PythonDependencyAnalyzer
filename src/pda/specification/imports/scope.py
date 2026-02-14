from enum import IntFlag, auto


class ImportScope(IntFlag):
    NONE = 0
    IF = auto()  # also ELIF
    ELSE = auto()
    TYPE_CHECKING = auto()  # (el)if TYPE_CHECKING
    MAIN = auto()  # (el)if __name__ == "__main__":
    CASE = auto()
    DEFAULT = auto()  # subset of CASE
    TRY = auto()
    EXCEPT = auto()
    FINALLY = auto()
    LOOP = auto()  # for, while, comprehensions
    WITH = auto()
    CLASS = auto()  # inside class def
    FUNCTION = auto()  # inside function def body
    DECORATOR = auto()
