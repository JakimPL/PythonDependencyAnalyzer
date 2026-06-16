from __future__ import annotations

import pkgutil
import sys
from pathlib import Path
from typing import List

from pda.analyzer.depth import CategoryContext, CategoryDepthPolicy
from pda.config import ModuleScanConfig
from pda.specification import ModuleCategory, PKGModuleInfo


class PkgModuleScanner:
    """Scans and filters external modules using pkgutil."""

    def __init__(self, config: ModuleScanConfig) -> None:
        self._pkg_modules = {module.name: module for module in pkgutil.iter_modules()}
        self._policy = CategoryDepthPolicy(config.stdlib_depth, config.external_depth)

    def discover(self) -> List[PKGModuleInfo]:
        """
        Discover external modules based on configuration.

        Returns:
            List of PKGModuleInfo containing module metadata.
        """
        discovered: List[PKGModuleInfo] = []

        for pkg_module in self._pkg_modules.values():
            name = pkg_module.name
            if self._skip_module(name):
                continue

            is_package = pkg_module.ispkg
            package = name if is_package else None
            base_path = Path(pkg_module.module_finder.path)  # type: ignore[union-attr]
            discovered.append(PKGModuleInfo(name=name, base_path=base_path, package=package))

        return discovered

    def _skip_module(self, name: str) -> bool:
        """
        Decide whether to skip discovery of a top-level installed package.

        Each discovered package is the boundary node (category-depth 1) of its category,
        so it is skipped only when that category is hidden entirely (its depth is 0).
        """
        category = ModuleCategory.STDLIB if name in sys.stdlib_module_names else ModuleCategory.EXTERNAL
        return not self._policy.should_include(CategoryContext(category, 1))
