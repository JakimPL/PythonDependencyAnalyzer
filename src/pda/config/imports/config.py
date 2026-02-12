from typing import Optional

from pydantic import Field

from pda.config.base import BaseConfig
from pda.config.imports.output import ImportGraphNodeFormatEnum


class ModuleImportsAnalyzerConfig(BaseConfig):
    ignore_cycles: bool = Field(default=False, description="Ignore cycles in the dependency graph")
    scan_stdlib: bool = Field(default=False, description="Include standard library modules")
    scan_external: bool = Field(default=False, description="Include stdlib/site-packages")
    scan_uninstalled: bool = Field(default=True, description="Try to analyze missing modules")
    resolve_wildcards: bool = Field(default=True, description="Expand wildcard imports")
    max_depth: Optional[int] = Field(default=None, description="Limit recursion depth")
    follow_conditional: bool = Field(default=True, description="Analyze try/except branches")
    node_format: ImportGraphNodeFormatEnum = Field(
        default=ImportGraphNodeFormatEnum.NAME,
        description="Output format for the import graph",
    )
