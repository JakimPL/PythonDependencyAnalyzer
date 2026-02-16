from pydantic import Field

from pda.config.base import BaseConfig


class PDAOptions(BaseConfig):
    auto_adjust_spacing: bool = Field(
        default=True,
        description="Whether to automatically adjust spacing between nodes in the visualization for 16:9 aspect ratio.",
    )
