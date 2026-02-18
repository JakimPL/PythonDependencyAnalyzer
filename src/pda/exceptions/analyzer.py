from pda.exceptions.base import PDAWarning


class PDAAnalysisWarning(PDAWarning):
    """Base class for warnings related to PDA analysis."""


class PDADependencyCycleWarning(PDAAnalysisWarning):
    """Warning raised when a cycle is detected in the dependency graph."""
