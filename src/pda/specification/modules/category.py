from __future__ import annotations

from enum import Enum


class ModuleCategory(Enum):
    """Categorizes modules by their origin and relationship to the project."""

    """Project modules under project_root."""
    LOCAL = "local"

    """Python standard library modules."""
    STDLIB = "stdlib"

    """Third-party packages from site-packages."""
    EXTERNAL = "external"

    """Uninstalled or unresolvable modules."""
    UNAVAILABLE = "unavailable"
