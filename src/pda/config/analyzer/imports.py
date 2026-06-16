from typing import Optional

from pydantic import Field, field_validator

from pda.config.analyzer.scan import ModuleScanConfig
from pda.config.base import BaseConfig
from pda.config.structures.graph import GraphSortMethod


class ModuleImportsAnalyzerConfig(BaseConfig):
    module_scan: ModuleScanConfig = Field(
        default=ModuleScanConfig(
            stdlib_depth=1,
            external_depth=1,
            collect_metadata=False,
            hide_private=True,
            hide_unavailable=False,
        ),
        description="Configuration for scanning modules during import analysis.",
    )

    sort_method: GraphSortMethod = Field(
        default="auto",
        description="""Method for sorting the dependency graph. 'auto' will choose
        topological sorting if the graph is acyclic, otherwise it will sort by condensation.""",
    )
    unify_nodes: bool = Field(
        default=False,
        description="Whether to unify nodes representing the same module across different import paths.",
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
    ignore_cycles: bool = Field(default=False, description="Ignore cycles in the dependency graph.")
    follow_conditional: bool = Field(default=False, description="Analyze imports from try/except branches.")
    max_depth: Optional[int] = Field(
        default=None,
        description="Maximum depth for recursion. None means no limit.",
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
