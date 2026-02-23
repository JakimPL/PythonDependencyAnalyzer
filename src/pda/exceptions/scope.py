from pda.exceptions.base import PDAException


class PDAScopeException(PDAException):
    """Base exception for scope-related errors in the PDA."""


class PDAMissingScopeOriginError(PDAScopeException):
    """Raised when a scope is created without an associated origin path."""


class PDAEmptyScopeError(PDAScopeException):
    """Raised when a scope is expected to have symbols but is found to be empty."""
