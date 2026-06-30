from pda.exceptions.base import PDAException


class PDAModuleError(PDAException):
    """A general module error."""


class PDAMissingModuleNameError(PDAModuleError):
    """Raised when a module name is empty or cannot be determined."""


class PDAMissingTopLevelModuleError(PDAModuleError):
    """Raised when the top-level module name cannot be determined from the import path."""


class PDAInvalidModuleOriginError(PDAModuleError):
    """Raised when a module fact has an invalid origin for its origin type."""
