from __future__ import annotations

import pkgutil
import sys
from pathlib import Path
from typing import Any, List, Optional

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

            base_path = self._finder_base_path(pkg_module.module_finder)
            if base_path is None:
                continue

            containing_package = name if pkg_module.ispkg else None
            discovered.append(
                PKGModuleInfo(
                    name=name,
                    base_path=base_path,
                    containing_package=containing_package,
                )
            )

        return discovered

    @staticmethod
    def _finder_base_path(finder: Any) -> Optional[Path]:
        path = getattr(finder, "path", None)
        if path is not None:
            return Path(path)

        archive = getattr(finder, "archive", None)
        if archive is not None:
            prefix = getattr(finder, "prefix", "") or ""
            return Path(archive) / prefix if prefix else Path(archive)

        return None

    def _skip_module(self, name: str) -> bool:
        """
        Decide whether to skip discovery of a top-level installed package.

        Each discovered package is the boundary node (category-depth 1) of its category,
        so it is skipped only when that category is hidden entirely (its depth is 0).
        """
        category = ModuleCategory.STDLIB if name in sys.stdlib_module_names else ModuleCategory.EXTERNAL
        return not self._policy.should_include(CategoryContext(category, 1))
