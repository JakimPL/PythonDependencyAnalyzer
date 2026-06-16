from pydantic import Field

from pda.config.base import BaseConfig


class ModuleScanConfig(BaseConfig):
    scan_stdlib: bool = Field(default=False, description="Include standard library modules.")
    scan_external: bool = Field(default=False, description="Include stdlib/site-packages.")
    collect_metadata: bool = Field(default=False, description="Collect module metadata.")
    hide_private: bool = Field(default=True, description="Hide private modules (starting with '_').")
    hide_unavailable: bool = Field(default=True, description="Hide unavailable modules (failed to resolve).")
    hide_stdlib: bool = Field(
        default=False,
        description="Exclude standard library modules from the graph entirely (not added as nodes).",
    )
    hide_external: bool = Field(
        default=False,
        description="Exclude external/third-party modules from the graph entirely (not added as nodes).",
    )
