from pathlib import Path
from typing import Optional

from pydantic import ConfigDict, Field

from pda.specification.base import Specification
from pda.specification.modules.module.category import ModuleCategory


class NamespacePortion(Specification):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
        use_enum_values=False,
    )

    path: Path = Field(description="Directory path contributing to a namespace package")
    matched_root: Optional[Path] = Field(
        default=None,
        description="Configured source, external, or stdlib root matched by this portion",
    )
    category: ModuleCategory = Field(description="Dependency category of this namespace portion")
