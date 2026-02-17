from enum import IntFlag, auto


class ImportScope(IntFlag):
    NONE = 0

    # Base branches
    IF = auto()  # also ELIF
    ELIF = auto()
    ELSE = auto()
    CASE = auto()
    DEFAULT = auto()
    TRY = auto()
    EXCEPT = auto()
    TRY_ELSE = auto()
    FINALLY = auto()

    # Loops, comprehensions and context managers
    LOOP = auto()  # for, while, comprehensions
    WITH = auto()

    # Definitions
    CLASS = auto()  # inside class def
    FUNCTION = auto()  # inside function def body
    DECORATOR = auto()  # inside a function

    # Special scopes
    TYPE_CHECKING = auto()  # `if TYPE_CHECKING` and variants
    MAIN = auto()  # `if __name__ == "__main__"`` and variants

    # Combinations
    IF_ELSE = IF | ELSE
    ERROR_HANDLING = TRY | EXCEPT | TRY_ELSE | FINALLY
    DEFAULT_CASE = CASE | DEFAULT
    BRANCH = IF_ELSE | DEFAULT_CASE | ERROR_HANDLING
    DEFINITION = CLASS | FUNCTION

    def validate(self) -> None:
        if self & ImportScope.TYPE_CHECKING and not self & ImportScope.IF_ELSE:
            raise ValueError("TYPE_CHECKING flag must be combined with IF or ELSE")

        if self & ImportScope.MAIN and not self & ImportScope.IF_ELSE:
            raise ValueError("MAIN flag must be combined with IF or ELSE")

        if self & ImportScope.DEFAULT and not self & ImportScope.CASE:
            raise ValueError("DEFAULT flag must be combined with CASE")

        if self & ImportScope.DECORATOR and not self & ImportScope.FUNCTION:
            raise ValueError("DECORATOR flag must be combined with FUNCTION")
