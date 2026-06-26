from pydantic import Field

from pda.config.analyzer.base import ModuleAnalyzerConfig
from pda.config.analyzer.scan import ModuleScanConfig


class ModulesCollectorConfig(ModuleAnalyzerConfig):
    module_scan: ModuleScanConfig = Field(
        default=ModuleScanConfig(
            stdlib_depth=None,
            external_depth=None,
            collect_metadata=True,
            hide_private=False,
            hide_unavailable=False,
        ),
        description="Configuration for scanning modules during collection.",
    )
