from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Optional, Tuple

from pda.constants import DELIMITER
from pda.specification import ModuleCategory
from pda.specification.imports.origin import OriginType
from pda.types import Pathlike


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
class TargetEnvironment:
    source_roots: Tuple[Path, ...]
    local_boundary: Path
    external_roots: Tuple[Path, ...] = ()
    include_sys_path: bool = True

    @classmethod
    def create(
        cls,
        source_roots: Tuple[Pathlike, ...],
        *,
        local_boundary: Optional[Pathlike] = None,
        external_roots: Tuple[Pathlike, ...] = (),
        include_sys_path: bool = True,
    ) -> TargetEnvironment:
        roots = tuple(Path(root).resolve() for root in source_roots)
        if not roots:
            raise ValueError("At least one source root is required")

        boundary = Path(local_boundary).resolve() if local_boundary is not None else roots[0]
        return cls(
            source_roots=roots,
            local_boundary=boundary,
            external_roots=tuple(Path(root).resolve() for root in external_roots),
            include_sys_path=include_sys_path,
        )


@dataclass(frozen=True)
class ModuleIdentity:
    name: str

    @property
    def parts(self) -> Tuple[str, ...]:
        return tuple(part for part in self.name.split(DELIMITER) if part)

    @property
    def public_fqn(self) -> str:
        return self.name.removesuffix(f"{DELIMITER}__init__")

    @property
    def parent_name(self) -> Optional[str]:
        parts = self.parts
        if len(parts) <= 1:
            return None

        return DELIMITER.join(parts[:-1])

    @property
    def top_level_name(self) -> str:
        parts = self.parts
        return parts[0] if parts else self.name


@dataclass(frozen=True)
class ModuleLocation:
    origin: Optional[Path]
    origin_type: OriginType
    submodule_search_locations: Tuple[Path, ...] = ()
    matched_root: Optional[Path] = None


@dataclass(frozen=True)
class ModuleCoordinates:
    identity: ModuleIdentity
    location: ModuleLocation


@dataclass(frozen=True)
class ModuleResolution:
    requested: str
    mode: ResolutionMode
    status: ResolutionStatus
    identity: Optional[ModuleIdentity] = None
    location: Optional[ModuleLocation] = None
    kind: ResolvedModuleKind = ResolvedModuleKind.UNKNOWN
    category: ModuleCategory = ModuleCategory.UNKNOWN
    reason: Optional[str] = None

    @property
    def resolved(self) -> bool:
        return self.status == ResolutionStatus.RESOLVED and self.identity is not None


@dataclass(frozen=True)
class SourceModuleContext:
    identity: ModuleIdentity
    location: ModuleLocation
    source_root: Path
    local_boundary: Path
    environment: TargetEnvironment

    @property
    def containing_package(self) -> str:
        if self.location.submodule_search_locations:
            return self.identity.public_fqn

        parent_name = self.identity.parent_name
        return parent_name or self.identity.top_level_name
