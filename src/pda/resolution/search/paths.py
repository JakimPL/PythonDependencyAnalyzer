from __future__ import annotations

from pathlib import Path

from pda.resolution.models.environment import TargetEnvironment
from pda.resolution.paths import unique_path_entries


class TargetSearchPath:
    def __init__(self, environment: TargetEnvironment) -> None:
        self._environment = environment

    def entries(self) -> tuple[str, ...]:
        paths: list[Path] = []
        paths.extend(self._environment.source_roots)
        paths.extend(self._environment.external_roots)
        paths.extend(self._environment.stdlib_roots)
        paths.extend(self._environment.sys_path_roots)

        return unique_path_entries(paths)
