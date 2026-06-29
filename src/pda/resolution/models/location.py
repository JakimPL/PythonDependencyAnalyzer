from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from pda.specification.imports.origin import OriginType
from pda.specification.modules.module.namespace import NamespacePortion

from .identity import ModuleIdentity


@dataclass(frozen=True)
class ModuleLocation:
    origin: Optional[Path]
    origin_type: OriginType
    submodule_search_locations: Tuple[Path, ...] = ()
    matched_root: Optional[Path] = None
    namespace_portions: Tuple[NamespacePortion, ...] = ()


@dataclass(frozen=True)
class ModuleCoordinates:
    identity: ModuleIdentity
    location: ModuleLocation
