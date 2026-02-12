from pydepgraph.exceptions.base import PDGException


class PDGPathError(PDGException):
    """Base exception for path-related errors in the Python Dependency Analyzer."""


class PDGPathNotAvailableError(PDGPathError, OSError):
    """Exception raised when a path cannot be accessed due to an OSError, PermissionError, or RuntimeError."""
