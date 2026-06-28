from __future__ import annotations

from enum import Enum


class ModuleCategory(Enum):
    """Categorizes modules by their origin and relationship to the project."""

    LOCAL = "local"  # project modules under project_root
    STDLIB = "stdlib"  # Python standard library modules
    EXTERNAL = "external"  # third-party packages from site-packages
    UNKNOWN = "unknown"  # origin could not be determined (e.g. the module was not found)

    @property
    def order(self) -> int:
        return list(ModuleCategory).index(self)
