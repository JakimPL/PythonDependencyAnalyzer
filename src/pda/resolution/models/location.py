from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from pda.specification.imports.origin import OriginType

from .identity import ModuleIdentity


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
