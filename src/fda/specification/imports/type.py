from enum import IntFlag


class ImportType(IntFlag):
    """
    Categorizes imports based on their nature.
    """

    """Module imports that occur at the top level of a file."""
    STATIC = 0

    """Module imports that occur at runtime."""
    DYNAMIC = 1

    """Module imports that are wrapped in conditional statements."""
    CONDITIONAL = 2

    """Combined flag for imports that are both dynamic and conditional."""
    DYNAMIC_CONDITIONAL = DYNAMIC | CONDITIONAL
