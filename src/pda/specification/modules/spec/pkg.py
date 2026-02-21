from pathlib import Path
from typing import NamedTuple, Optional


class PKGModuleInfo(NamedTuple):
    """Information about a module discovered via pkgutil."""

    name: str
    base_path: Path
    package: Optional[str]
