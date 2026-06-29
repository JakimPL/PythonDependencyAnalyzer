from pda.exceptions.base import PDAException


class PDAModuleSpecError(PDAException):
    """Raised when there is an issue with a module spec during import resolution."""


class PDANoOriginError(PDAModuleSpecError):
    """Raised when a module spec has an empty origin."""


class PDARelativeOriginError(PDAModuleSpecError):
    """Raised when a module spec has a relative origin path that cannot be resolved."""


class PDAOriginFileNotFoundError(PDAModuleSpecError, FileNotFoundError):
    """Raised when a module spec has an origin path that does not exist."""


class PDAInvalidOriginTypeError(PDAModuleSpecError):
    """Raised when a module spec has an invalid origin type for its origin."""


class PDAMissingModuleSpecError(PDAModuleSpecError):
    """Raised when a module spec cannot be found for a given module name."""
