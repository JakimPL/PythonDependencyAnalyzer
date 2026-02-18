from pydantic import Field

from pda.config.base import BaseConfig


class ModuleScanConfig(BaseConfig):
    scan_stdlib: bool = Field(default=False, description="Include standard library modules.")
    scan_external: bool = Field(default=False, description="Include stdlib/site-packages.")
    scan_uninstalled: bool = Field(default=True, description="Try to analyze missing modules.")
    collect_metadata: bool = Field(default=False, description="Collect module metadata.")
    hide_private: bool = Field(default=True, description="Hide private modules (starting with '_').")
