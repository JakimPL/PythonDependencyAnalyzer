from typing import Optional

from pydantic import Field

from pydepgraph.config.base import BaseConfig
from pydepgraph.config.imports.output import ImportGraphNodeFormatEnum


class ModulesCollectorConfig(BaseConfig):
    max_level: Optional[int] = Field(
        default=None,
        description="Maximum depth for collecting imports. None means no limit.",
    )
    node_format: ImportGraphNodeFormatEnum = Field(
        default=ImportGraphNodeFormatEnum.NAME,
        description="Output format for the import graph",
    )
