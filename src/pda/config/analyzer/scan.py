from typing import Optional

from pydantic import Field, field_validator

from pda.config.base import BaseConfig

_DEPTH_DESCRIPTION = (
    "Depth to recurse into the {category} category, measured from the boundary "
    "crossing into it (the first {category} node is depth 1). None = unlimited; "
    "0 = hide entirely (never added as a node); 1 = show only the boundary node "
    "without recursing; N = show and recurse N levels deep."
)


class ModuleScanConfig(BaseConfig):
    stdlib_depth: Optional[int] = Field(
        default=0,
        description=_DEPTH_DESCRIPTION.format(category="standard-library"),
    )
    external_depth: Optional[int] = Field(
        default=0,
        description=_DEPTH_DESCRIPTION.format(category="external/third-party"),
    )
    collect_metadata: bool = Field(default=False, description="Collect module metadata.")
    hide_private: bool = Field(default=True, description="Hide private modules (starting with '_').")
    hide_unavailable: bool = Field(default=True, description="Hide unavailable modules (failed to resolve).")

    @field_validator("stdlib_depth", "external_depth")
    @classmethod
    def _validate_depth(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Category depth must be >= 0 or None (unlimited).")

        return value
