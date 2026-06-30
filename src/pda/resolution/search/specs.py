from __future__ import annotations

from importlib.machinery import BuiltinImporter, FrozenImporter, ModuleSpec, PathFinder
from typing import Optional, Sequence

from pda.constants import DELIMITER

from .paths import TargetSearchPath


class ModuleSpecResolver:
    def __init__(self, search_path: TargetSearchPath) -> None:
        self._search_path = search_path

    def find(self, fullname: str) -> Optional[ModuleSpec]:
        builtin_or_frozen = BuiltinImporter.find_spec(fullname) or FrozenImporter.find_spec(fullname)
        if builtin_or_frozen is not None:
            return builtin_or_frozen

        return self._find_project_path_spec(fullname, self._search_path.entries())

    def _find_project_path_spec(
        self,
        fullname: str,
        search_path: Sequence[str],
    ) -> Optional[ModuleSpec]:
        path: Optional[Sequence[str]] = search_path
        spec: Optional[ModuleSpec] = None
        parts = fullname.split(DELIMITER)

        for index in range(len(parts)):
            qualified_name = DELIMITER.join(parts[: index + 1])
            local_spec = self._find_local_spec(qualified_name, path)
            full_spec = PathFinder.find_spec(qualified_name, path)
            spec = self._select_spec(local_spec, full_spec)
            if spec is None:
                return None

            if index < len(parts) - 1:
                path = spec.submodule_search_locations
                if path is None:
                    return None

        return spec

    def _find_local_spec(self, fullname: str, path: Optional[Sequence[str]]) -> Optional[ModuleSpec]:
        if path is None:
            return None

        local_path = self._search_path.local_entries(path)
        if not local_path:
            return None

        return PathFinder.find_spec(fullname, local_path)

    def _select_spec(
        self,
        local_spec: Optional[ModuleSpec],
        full_spec: Optional[ModuleSpec],
    ) -> Optional[ModuleSpec]:
        if local_spec is None:
            return full_spec

        if full_spec is not None and self._is_namespace_spec(local_spec) and self._is_namespace_spec(full_spec):
            return full_spec

        return local_spec

    @staticmethod
    def _is_namespace_spec(spec: ModuleSpec) -> bool:
        return spec.origin is None and spec.submodule_search_locations is not None
