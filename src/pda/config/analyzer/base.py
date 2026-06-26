from typing import Optional

from pydantic import Field, field_validator

from pda.config.analyzer.scan import ModuleScanConfig
from pda.config.base import BaseConfig


class ModuleAnalyzerConfig(BaseConfig):
    """
    Shared configuration for analyzers that scan modules and produce a ModuleGraph.
    """

    module_scan: ModuleScanConfig = Field(
        default_factory=ModuleScanConfig,
        description="Configuration for scanning modules.",
    )
    qualified_names: bool = Field(
        default=False,
        description="""Whether to use qualified module names (e.g., 'package.module' instead of 'module')
        as labels in the graph.""",
    )
    collapse_level: Optional[int] = Field(
        default=None,
        description="""Post-processing structural collapse of the graph by absolute dotted-name level,
        counted from the package root. 0 = collapse to the top-level package; N = keep the first N+1
        components; None = no collapsing. Distinct from 'max_depth', which bounds scan recursion
        relative to the entry point.""",
    )
    max_depth: Optional[int] = Field(
        default=None,
        description="Maximum recursion depth relative to the entry point. None means no limit.",
    )

    @field_validator("collapse_level")
    @classmethod
    def _validate_collapse_level(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("collapse_level must be >= 0 or None")

        return value

    @property
    def collect_metadata(self) -> bool:
        return self.module_scan.collect_metadata

    @property
    def hide_private(self) -> bool:
        return self.module_scan.hide_private

    @property
    def hide_unavailable(self) -> bool:
        return self.module_scan.hide_unavailable

    @property
    def stdlib_depth(self) -> Optional[int]:
        return self.module_scan.stdlib_depth

    @property
    def external_depth(self) -> Optional[int]:
        return self.module_scan.external_depth
