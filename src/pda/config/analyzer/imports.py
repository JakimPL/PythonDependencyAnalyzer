from typing import Optional

from pydantic import Field

from pda.config.analyzer.scan import ModuleScanConfig
from pda.config.base import BaseConfig
from pda.config.structures.graph import GraphSortMethod


class ModuleImportsAnalyzerConfig(BaseConfig):
    module_scan: ModuleScanConfig = Field(
        default=ModuleScanConfig(
            scan_stdlib=False,
            scan_external=False,
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
    ignore_cycles: bool = Field(default=False, description="Ignore cycles in the dependency graph.")
    follow_conditional: bool = Field(default=True, description="Analyze if/try/except branches.")
    max_depth: Optional[int] = Field(
        default=None,
        description="Maximum depth for recursion. None means no limit.",
    )

    @property
    def scan_stdlib(self) -> bool:
        return self.module_scan.scan_stdlib

    @property
    def scan_external(self) -> bool:
        return self.module_scan.scan_external

    @property
    def collect_metadata(self) -> bool:
        return self.module_scan.collect_metadata

    @property
    def hide_private(self) -> bool:
        return self.module_scan.hide_private

    @property
    def hide_unavailable(self) -> bool:
        return self.module_scan.hide_unavailable
