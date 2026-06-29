from __future__ import annotations

import sys
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path
from typing import Optional

from pda.resolution.models import ModuleIdentity, ModuleLocation, ResolvedModuleKind, TargetEnvironment
from pda.resolution.paths import is_relative_to
from pda.specification import ModuleCategory
from pda.specification.imports.origin import OriginType


class ModuleClassifier:
    def __init__(self, environment: TargetEnvironment) -> None:
        self._environment = environment

    def kind(self, location: ModuleLocation) -> ResolvedModuleKind:
        if location.origin_type == OriginType.BUILT_IN:
            return ResolvedModuleKind.BUILTIN

        if location.origin_type == OriginType.FROZEN:
            return ResolvedModuleKind.FROZEN

        if location.origin is None and location.submodule_search_locations:
            return ResolvedModuleKind.NAMESPACE_PACKAGE

        if location.origin is not None and any(str(location.origin).endswith(suffix) for suffix in EXTENSION_SUFFIXES):
            return ResolvedModuleKind.EXTENSION

        if location.submodule_search_locations:
            return ResolvedModuleKind.REGULAR_PACKAGE

        if location.origin_type == OriginType.PYTHON:
            return ResolvedModuleKind.SOURCE_MODULE

        return ResolvedModuleKind.UNKNOWN

    def category(
        self,
        identity: ModuleIdentity,
        location: ModuleLocation,
    ) -> ModuleCategory:
        if self.is_local(location):
            return ModuleCategory.LOCAL

        if location.origin_type in {OriginType.BUILT_IN, OriginType.FROZEN}:
            return ModuleCategory.STDLIB

        if identity.top_level_name in sys.stdlib_module_names:
            return ModuleCategory.STDLIB

        return ModuleCategory.EXTERNAL

    def is_local(self, location: ModuleLocation) -> bool:
        candidates = list(location.submodule_search_locations)
        if location.origin is not None:
            candidates.append(location.origin)

        return any(is_relative_to(candidate, self._environment.local_boundary) for candidate in candidates)

    def matched_root(
        self,
        origin: Optional[Path],
        locations: tuple[Path, ...],
    ) -> Optional[Path]:
        candidates = [candidate for candidate in (origin, *locations) if candidate is not None]
        for root in (*self._environment.source_roots, *self._environment.external_roots):
            if any(is_relative_to(candidate, root) for candidate in candidates):
                return root

        return None
