from pda.exceptions.analyzer import (
    PDAAnalysisError,
    PDAAnalysisWarning,
    PDADependencyCycleError,
    PDADependencyCycleWarning,
)
from pda.exceptions.base import PDAException, PDAWarning
from pda.exceptions.imports import (
    PDAImportPathError,
    PDAPathResolutionError,
    PDARelativeBasePathError,
    PDASourceFileOutsideProjectError,
)
from pda.exceptions.modules import PDAMissingModuleNameError, PDAMissingTopLevelModuleError, PDAModuleError
from pda.exceptions.options import (
    PDACategoryDisabledWarning,
    PDAGraphLayoutWarning,
    PDAOptionsWarning,
    PDAValidationOptionsWarning,
)
from pda.exceptions.spec import (
    PDAFindSpecError,
    PDAInvalidOriginTypeError,
    PDAMissingModuleSpecError,
    PDAModuleSpecError,
    PDANoOriginError,
    PDAOriginFileNotFoundError,
    PDARelativeOriginError,
)

__all__ = [
    # Base classes
    "PDAException",
    "PDAWarning",
    # Analysis-related warnings
    "PDAAnalysisWarning",
    "PDADependencyCycleWarning",
    "PDAAnalysisError",
    "PDADependencyCycleError",
    # Module-related exceptions
    "PDAModuleError",
    "PDAMissingModuleNameError",
    "PDAMissingTopLevelModuleError",
    # Import-related exceptions
    "PDAImportPathError",
    "PDASourceFileOutsideProjectError",
    "PDARelativeBasePathError",
    "PDAPathResolutionError",
    # Spec-related exceptions
    "PDAModuleSpecError",
    "PDAFindSpecError",
    "PDANoOriginError",
    "PDARelativeOriginError",
    "PDAOriginFileNotFoundError",
    "PDAInvalidOriginTypeError",
    "PDAMissingModuleSpecError",
    # Options-related warnings
    "PDAOptionsWarning",
    "PDAValidationOptionsWarning",
    "PDACategoryDisabledWarning",
    "PDAGraphLayoutWarning",
]
