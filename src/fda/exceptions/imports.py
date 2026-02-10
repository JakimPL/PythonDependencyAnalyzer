from fda.exceptions.base import FDAException


class FDAImportError(FDAException):
    """A general import error."""


class FDAImportResolutionError(FDAImportError):
    """Raised when an import cannot be resolved."""


class FDAModuleSpecError(FDAImportResolutionError):
    """Raised when there is an issue with a module spec during import resolution."""


class FDAPathResolutionError(FDAModuleSpecError):
    """Raised when a path cannot be resolved against any candidate base path or sys.path entry."""


class FDAEmptyOriginError(FDAModuleSpecError):
    """Raised when a module spec has an empty origin."""


class FDAFrozenOriginError(FDAModuleSpecError):
    """Raised when a module spec has a frozen origin."""


class FDAOriginFileNotFoundError(FDAModuleSpecError, FileNotFoundError):
    """Raised when a module spec has an origin path that does not exist."""


class FDAInvalidOriginTypeError(FDAModuleSpecError):
    """Raised when a module spec has an invalid origin type for its origin."""


class FDAMissingModuleSpecError(FDAModuleSpecError):
    """Raised when a module spec cannot be found for a given module name."""


class FDASourceFileOutsideProjectError(FDAModuleSpecError):
    """Raised when the provided source file is outside the analyzed package/module."""


class FDAMissingModuleNameError(FDAImportError):
    """Raised when a module name is empty or cannot be determined."""


class FDARelativeBasePathError(FDAImportError):
    """Raised when a relative path is provided as the base path."""
