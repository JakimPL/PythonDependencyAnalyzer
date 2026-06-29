from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from pda.specification import ModuleCategory

from .diagnostics import ResolutionDiagnostic
from .identity import ModuleIdentity
from .location import ModuleLocation


class ResolutionMode(StrEnum):
    PROJECT = "project"
    FILESYSTEM = "filesystem"
    RUNTIME = "runtime"
    ENVIRONMENT = "environment"


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNAVAILABLE = "unavailable"
    AMBIGUOUS = "ambiguous"


class ResolvedModuleKind(StrEnum):
    SOURCE_MODULE = "source_module"
    REGULAR_PACKAGE = "regular_package"
    NAMESPACE_PACKAGE = "namespace_package"
    BUILTIN = "builtin"
    FROZEN = "frozen"
    EXTENSION = "extension"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ModuleResolution:
    requested: str
    mode: ResolutionMode
    status: ResolutionStatus
    identity: Optional[ModuleIdentity] = None
    location: Optional[ModuleLocation] = None
    kind: ResolvedModuleKind = ResolvedModuleKind.UNKNOWN
    category: ModuleCategory = ModuleCategory.UNKNOWN
    diagnostic: Optional[ResolutionDiagnostic] = None

    @property
    def resolved(self) -> bool:
        return self.status == ResolutionStatus.RESOLVED and self.identity is not None

    @property
    def reason(self) -> Optional[str]:
        return self.diagnostic.message if self.diagnostic is not None else None
