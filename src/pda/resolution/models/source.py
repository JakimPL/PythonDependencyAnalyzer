from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    def containing_package(self) -> str:
        if self.location.submodule_search_locations:
            return self.identity.public_fqn

        parent_name = self.identity.parent_name
        return parent_name or self.identity.top_level_name
