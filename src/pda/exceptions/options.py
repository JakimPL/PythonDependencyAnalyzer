from pda.exceptions.base import PDAWarning


class PDAOptionsWarning(PDAWarning):
    """Warning related to PDA options."""


class PDACategoryDisabledWarning(PDAOptionsWarning):
    """Warning raised when a disabled category is tried to be accessed."""


class PDAExternalResolutionWarning(PDAOptionsWarning):
    """Warning raised when external traversal is enabled without external search roots."""


class PDAGraphLayoutWarning(PDAOptionsWarning):
    """Warning raised when an invalid graph layout is specified."""
