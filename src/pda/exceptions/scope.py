from pda.exceptions.base import PDAException


class PDAScopeException(PDAException):
    """Base exception for scope-related errors in the PDA."""


class PDAMissingScopeOrigin(PDAScopeException):
    """Raised when a scope is created without an associated origin path.""" """Raised when a scope is created without an associated origin path."""
