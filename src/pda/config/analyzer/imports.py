from pydantic import Field

from pda.config.analyzer.base import ModuleAnalyzerConfig
from pda.config.analyzer.scan import ModuleScanConfig
from pda.config.structures.graph import GraphSortMethod


class ModuleImportsAnalyzerConfig(ModuleAnalyzerConfig):
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
    ignore_cycles: bool = Field(default=False, description="Ignore cycles in the dependency graph.")
    follow_conditional: bool = Field(default=False, description="Analyze imports from try/except branches.")
