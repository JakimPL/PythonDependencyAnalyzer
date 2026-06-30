from pathlib import Path
from typing import Optional, Tuple

from pydantic import Field

from pda.config.base import BaseConfig


class ModuleResolutionConfig(BaseConfig):
    source_roots: Optional[Tuple[Path, ...]] = Field(
        default=None,
        description="Import source roots, resolved relative to the project root when relative.",
    )
    local_boundary: Optional[Path] = Field(
        default=None,
        description="Filesystem boundary for local module categorization. Defaults to the project root.",
    )
    external_roots: Tuple[Path, ...] = Field(
        default_factory=tuple,
        description="Dependency search roots, resolved relative to the project root when relative.",
    )
    include_sys_path: bool = Field(
        default=True,
        description="Use the active interpreter sys.path for external dependency resolution.",
    )
