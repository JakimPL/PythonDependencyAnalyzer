from __future__ import annotations

import sys
from importlib.machinery import BuiltinImporter, FrozenImporter, ModuleSpec, PathFinder
from pathlib import Path
from typing import Optional, Sequence

from pda.constants import DELIMITER
from pda.resolution.models import TargetEnvironment
from pda.resolution.paths import unique_path_entries


class TargetSearchPath:
    def __init__(self, environment: TargetEnvironment) -> None:
        self._environment = environment

    def entries(self) -> tuple[str, ...]:
        paths: list[Path] = []
        paths.extend(self._environment.source_roots)
        paths.extend(self._environment.external_roots)
        if self._environment.include_sys_path:
            paths.extend(Path(entry).resolve() for entry in sys.path if entry)

        return unique_path_entries(paths)


class ModuleSpecResolver:
    def __init__(self, search_path: TargetSearchPath) -> None:
        self._search_path = search_path

    def find(self, fullname: str) -> Optional[ModuleSpec]:
        builtin_or_frozen = BuiltinImporter.find_spec(fullname) or FrozenImporter.find_spec(fullname)
        if builtin_or_frozen is not None:
            return builtin_or_frozen

        return self._find_path_spec(fullname, self._search_path.entries())

    def _find_path_spec(
        self,
        fullname: str,
        search_path: Sequence[str],
    ) -> Optional[ModuleSpec]:
        path: Optional[Sequence[str]] = search_path
        spec: Optional[ModuleSpec] = None
        parts = fullname.split(DELIMITER)

        for index in range(len(parts)):
            qualified_name = DELIMITER.join(parts[: index + 1])
            spec = PathFinder.find_spec(qualified_name, path)
            if spec is None:
                return None

            if index < len(parts) - 1:
                path = spec.submodule_search_locations
                if path is None:
                    return None

        return spec
