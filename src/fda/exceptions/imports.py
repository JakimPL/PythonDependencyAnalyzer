from fda.exceptions.base import FDAException


class FDAImportError(FDAException):
    """A general import error."""


class FDAImportResolutionError(FDAImportError):
    """Raised when an import cannot be resolved."""


class FDAPathResolutionError(FDAImportResolutionError):
    """Raised when a path cannot be resolved against any candidate project root or sys.path entry."""


class FDASourceFileOutsideProjectError(FDAImportResolutionError):
    """Raised when the provided source file is outside the analyzed package/module."""


class FDAMissingPackageNameError(FDAImportError):
    """Raised when a package name cannot be determined for a source file."""


class FDARelativeProjectRootError(FDAImportError):
    """Raised when a relative path is provided as the project root."""
