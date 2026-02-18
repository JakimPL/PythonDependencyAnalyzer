from pda.exceptions.base import PDAWarning


class PDAOptionsWarning(PDAWarning):
    """Warning related to PDA options."""


class PDAValidationOptionsWarning(PDAOptionsWarning):
    """Warning related to validation options."""


class PDACategoryDisabledWarning(PDAOptionsWarning):
    """Warning raised when a disabled category is tried to be accessed."""


class PDAGraphLayoutWarning(PDAOptionsWarning):
    """Warning raised when an invalid graph layout is specified."""
