from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from pda.specification import ModuleCategory, ModuleKind, ResolutionDiagnostic

from .identity import ModuleIdentity
from .location import ModuleLocation


class ResolutionMode(StrEnum):
    PROJECT = "project"
    FILESYSTEM = "filesystem"
    RUNTIME = "runtime"


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNAVAILABLE = "unavailable"
    AMBIGUOUS = "ambiguous"


class ResolutionAlternativeKind(StrEnum):
    SUBMODULE = "submodule"
    EXPORTED_OBJECT = "exported_object"


@dataclass(frozen=True)
class ResolutionAlternative:
    kind: ResolutionAlternativeKind
    resolution: ModuleResolution


@dataclass(frozen=True)
class ModuleResolution:
    requested: str
    mode: ResolutionMode
    status: ResolutionStatus
    identity: Optional[ModuleIdentity] = None
    location: Optional[ModuleLocation] = None
    kind: ModuleKind = ModuleKind.UNKNOWN
    category: ModuleCategory = ModuleCategory.UNKNOWN
    diagnostic: Optional[ResolutionDiagnostic] = None
    alternatives: tuple[ResolutionAlternative, ...] = ()

    @property
    def resolved(self) -> bool:
        return self.status == ResolutionStatus.RESOLVED and self.identity is not None

    @property
    def reason(self) -> Optional[str]:
        return self.diagnostic.message if self.diagnostic is not None else None
