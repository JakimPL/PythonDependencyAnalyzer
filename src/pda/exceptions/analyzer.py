from pda.exceptions.base import PDAException, PDAWarning


class PDAAnalysisWarning(PDAWarning):
    """Base class for warnings related to PDA analysis."""


class PDADependencyCycleWarning(PDAAnalysisWarning):
    """Warning raised when a cycle is detected in the dependency graph."""


class PDAAnalysisError(PDAException):
    """Base class for errors related to PDA analysis."""


class PDADependencyCycleError(PDAAnalysisError):
    """Error raised when a cycle is detected in the dependency graph and cycles are not ignored."""
