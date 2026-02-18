from typing import Optional

from pydantic import Field

from pda.config.analyzer.scan import ModuleScanConfig
from pda.config.base import BaseConfig


class ModulesCollectorConfig(BaseConfig):
    module_scan: ModuleScanConfig = Field(
        default=ModuleScanConfig(
            scan_stdlib=True,
            scan_external=True,
            collect_metadata=True,
            hide_private=False,
        ),
        description="Configuration for scanning modules during collection.",
    )

    max_level: Optional[int] = Field(
        default=None,
        description="Maximum depth for collecting imports. None means no limit.",
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
