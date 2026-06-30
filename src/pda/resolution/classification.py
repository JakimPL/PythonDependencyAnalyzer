from __future__ import annotations

import sys
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path
from typing import Optional

from pda.resolution.models.environment import TargetEnvironment
from pda.resolution.models.identity import ModuleIdentity
from pda.resolution.models.location import ModuleLocation
from pda.specification import ModuleCategory, ModuleKind
from pda.specification.imports.origin import OriginType
from pda.specification.modules.module.namespace import NamespacePortion


class ModuleClassifier:
    def __init__(self, environment: TargetEnvironment) -> None:
        self._environment = environment

    def kind(self, location: ModuleLocation) -> ModuleKind:
        match location.origin_type:
            case OriginType.BUILT_IN:
                return ModuleKind.BUILTIN
            case OriginType.FROZEN:
                return ModuleKind.FROZEN

        if location.origin is None:
            return ModuleKind.NAMESPACE_PACKAGE if location.submodule_search_locations else ModuleKind.UNKNOWN

        if self._is_extension_origin(location.origin):
            return ModuleKind.EXTENSION

        if location.submodule_search_locations:
            return ModuleKind.REGULAR_PACKAGE

        if location.origin_type == OriginType.PYTHON:
            return ModuleKind.SOURCE_MODULE

        return ModuleKind.UNKNOWN

    @staticmethod
    def _is_extension_origin(origin: Path) -> bool:
        return any(str(origin).endswith(suffix) for suffix in EXTENSION_SUFFIXES)

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
        if location.namespace_portions:
            return any(portion.category == ModuleCategory.LOCAL for portion in location.namespace_portions)

        candidates = list(location.submodule_search_locations)
        if location.origin is not None:
            candidates.append(location.origin)

        return any(self.category_for_path(candidate) == ModuleCategory.LOCAL for candidate in candidates)

    def matched_root(
        self,
        origin: Optional[Path],
        locations: tuple[Path, ...],
    ) -> Optional[Path]:
        for candidate in (origin, *locations):
            if candidate is None:
                continue

            root = self.matched_root_for_path(candidate)
            if root is not None:
                return root

        return None

    def namespace_portions_for(
        self,
        origin: Optional[Path],
        locations: tuple[Path, ...],
    ) -> tuple[NamespacePortion, ...]:
        if origin is not None or not locations:
            return ()

        return self.namespace_portions(locations)

    def namespace_portions(self, locations: tuple[Path, ...]) -> tuple[NamespacePortion, ...]:
        return tuple(
            NamespacePortion(
                path=location,
                matched_root=self.matched_root_for_path(location),
                category=self.category_for_path(location),
            )
            for location in locations
        )

    def matched_root_for_path(self, path: Path) -> Optional[Path]:
        match = self._match_root(path)
        return match[0] if match is not None else None

    def category_for_path(self, path: Path) -> ModuleCategory:
        match = self._match_root(path)
        return match[1] if match is not None else ModuleCategory.UNKNOWN

    def _match_root(self, path: Path) -> Optional[tuple[Path, ModuleCategory]]:
        for root, category in self._classified_roots():
            if path.is_relative_to(root):
                return root, category

        return None

    def _classified_roots(self) -> tuple[tuple[Path, ModuleCategory], ...]:
        roots: list[tuple[Path, ModuleCategory]] = []
        roots.extend((root, ModuleCategory.LOCAL) for root in self._environment.source_roots)
        roots.extend((root, ModuleCategory.EXTERNAL) for root in self._environment.external_roots)
        if self._environment.local_boundary is not None:
            roots.append((self._environment.local_boundary, ModuleCategory.LOCAL))

        roots.extend((root, ModuleCategory.STDLIB) for root in self._environment.stdlib_roots)
        roots.extend((root, ModuleCategory.EXTERNAL) for root in self._environment.sys_path_roots)
        return tuple(roots)
