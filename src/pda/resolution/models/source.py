from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .environment import TargetEnvironment
from .identity import ModuleIdentity
from .location import ModuleLocation


@dataclass(frozen=True)
class SourceModuleContext:
    identity: ModuleIdentity
    location: ModuleLocation
    source_root: Path
    local_boundary: Path
    environment: TargetEnvironment

    @property
    def containing_package(self) -> Optional[str]:
        if self.location.submodule_search_locations:
            return self.identity.public_fqn

        return self.identity.parent_name
