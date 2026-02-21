from __future__ import annotations

import pkgutil
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional

from pda.config.analyzer.scan import ModuleScanConfig


class PkgModuleInfo(NamedTuple):
    """Information about a module discovered via pkgutil."""

    name: str
    base_path: Path
    package: Optional[str]


class PkgModuleScanner:
    """Scans and filters external modules using pkgutil."""

    def __init__(self, config: ModuleScanConfig) -> None:
        self._pkg_modules = {module.name: module for module in pkgutil.iter_modules()}
        self._config = config

    @property
    def scan_stdlib(self) -> bool:
        return self._config.scan_stdlib

    @property
    def scan_external(self) -> bool:
        return self._config.scan_external

    def discover(self) -> List[PkgModuleInfo]:
        """
        Discover external modules based on configuration.

        Returns:
            List of PkgModuleInfo containing module metadata.
        """
        discovered: List[PkgModuleInfo] = []

        for pkg_module in self._pkg_modules.values():
            name = pkg_module.name
            if self._skip_module(name):
                continue

            is_package = pkg_module.ispkg
            package = name if is_package else None
            base_path = Path(pkg_module.module_finder.path)  # type: ignore[union-attr]
            discovered.append(PkgModuleInfo(name=name, base_path=base_path, package=package))

        return discovered

    def _skip_module(self, name: str) -> bool:
        if name in sys.stdlib_module_names:
            if not self.scan_stdlib:
                return True

        elif not self.scan_external:
            return True

        return False
