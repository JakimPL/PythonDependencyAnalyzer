from __future__ import annotations

from enum import StrEnum


class ModuleCategory(StrEnum):
    """Categorizes modules by their origin and relationship to the project."""

    """Project modules under project_root."""
    INTERNAL = "internal"

    """Python standard library modules."""
    STDLIB = "stdlib"

    """Third-party packages from site-packages."""
    EXTERNAL = "external"

    """Uninstalled or unresolvable modules."""
    UNAVAILABLE = "unavailable"

    @staticmethod
    def from_syspath_key(key: str) -> ModuleCategory:
        match key:
            case "stdlib":
                return ModuleCategory.STDLIB
            case "purelib":
                return ModuleCategory.EXTERNAL

        return ModuleCategory.UNAVAILABLE
