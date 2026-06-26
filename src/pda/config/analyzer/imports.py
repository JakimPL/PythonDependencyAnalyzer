from pydantic import Field, field_validator

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
        default=True,
        description="Whether to unify nodes representing the same module across different import paths.",
    )
    fail_on_cycle: bool = Field(
        default=False,
        description="Raise an error instead of reporting when the dependency graph contains import cycles.",
    )
    cycle_length_bound: int = Field(
        default=8,
        description="""Maximum length of an example simple cycle enumerated within each
        strongly-connected component when reporting import cycles.""",
    )
    cycle_examples: int = Field(
        default=5,
        description="Maximum number of example cycles reported per strongly-connected component.",
    )
    follow_conditional: bool = Field(
        default=False,
        description="Analyze imports from try/except branches.",
    )

    @field_validator("cycle_length_bound")
    @classmethod
    def _validate_cycle_length_bound(cls, value: int) -> int:
        if value < 1:
            raise ValueError("cycle_length_bound must be >= 1")

        return value

    @field_validator("cycle_examples")
    @classmethod
    def _validate_cycle_examples(cls, value: int) -> int:
        if value < 0:
            raise ValueError("cycle_examples must be >= 0")

        return value
