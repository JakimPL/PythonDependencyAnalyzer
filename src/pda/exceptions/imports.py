from pda.exceptions.base import PDAException


class PDAImportError(PDAException):
    """A general import error."""


class PDAImportResolutionError(PDAImportError):
    """Raised when an import cannot be resolved."""


class PDAModuleSpecError(PDAImportResolutionError):
    """Raised when there is an issue with a module spec during import resolution."""


class PDAPathResolutionError(PDAModuleSpecError):
    """Raised when a path cannot be resolved against any candidate base path or sys.path entry."""


class PDAEmptyOriginError(PDAModuleSpecError):
    """Raised when a module spec has an empty origin."""


class PDAFrozenOriginError(PDAModuleSpecError):
    """Raised when a module spec has a frozen origin."""


class PDAOriginFileNotFoundError(PDAModuleSpecError, FileNotFoundError):
    """Raised when a module spec has an origin path that does not exist."""


class PDAInvalidOriginTypeError(PDAModuleSpecError):
    """Raised when a module spec has an invalid origin type for its origin."""


class PDAMissingModuleSpecError(PDAModuleSpecError):
    """Raised when a module spec cannot be found for a given module name."""


class PDASourceFileOutsideProjectError(PDAModuleSpecError):
    """Raised when the provided source file is outside the analyzed package/module."""


class PDAMissingModuleNameError(PDAImportError):
    """Raised when a module name is empty or cannot be determined."""


class PDARelativeBasePathError(PDAImportError):
    """Raised when a relative path is provided as the base path."""
