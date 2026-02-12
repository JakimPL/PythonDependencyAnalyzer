from pda.exceptions.base import PDAException


class PDAPathError(PDAException):
    """Base exception for path-related errors in the Python Dependency Analyzer."""


class PDAPathNotAvailableError(PDAPathError, OSError):
    """Exception raised when a path cannot be accessed due to an OSError, PermissionError, or RuntimeError."""
