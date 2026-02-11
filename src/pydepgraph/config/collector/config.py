from pydantic import Field

from pydepgraph.config.base import BaseConfig
from pydepgraph.config.imports.output import ImportGraphNodeFormatEnum


class ModulesCollectorConfig(BaseConfig):
    node_format: ImportGraphNodeFormatEnum = Field(
        default=ImportGraphNodeFormatEnum.NAME,
        description="Output format for the import graph",
    )
