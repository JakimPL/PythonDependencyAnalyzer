from __future__ import annotations

import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

from pda.types import Pathlike


@dataclass(frozen=True)
class TargetEnvironment:
    source_roots: Tuple[Path, ...]
    local_boundary: Optional[Path]
    external_roots: Tuple[Path, ...] = ()
    stdlib_roots: Tuple[Path, ...] = ()
    include_sys_path: bool = False

    @classmethod
    def create(
        cls,
        source_roots: Tuple[Pathlike, ...],
        *,
        local_boundary: Optional[Pathlike] = None,
        external_roots: Tuple[Pathlike, ...] = (),
        include_sys_path: bool = False,
    ) -> TargetEnvironment:
        roots = tuple(Path(root).resolve() for root in source_roots)
        return cls(
            source_roots=roots,
            local_boundary=resolve_local_boundary(roots, local_boundary),
            external_roots=tuple(Path(root).resolve() for root in external_roots),
            stdlib_roots=default_stdlib_roots(),
            include_sys_path=include_sys_path,
        )

    @classmethod
    def runtime(cls) -> TargetEnvironment:
        return cls(
            source_roots=(),
            local_boundary=None,
            stdlib_roots=default_stdlib_roots(),
            include_sys_path=True,
        )

    @property
    def sys_path_roots(self) -> Tuple[Path, ...]:
        if not self.include_sys_path:
            return ()

        return unique_resolved_paths(Path(entry) for entry in sys.path if entry)


def default_stdlib_roots() -> Tuple[Path, ...]:
    roots: list[Path] = []
    for key in ("stdlib", "platstdlib"):
        raw_path = sysconfig.get_path(key)
        if raw_path is None:
            continue

        root = Path(raw_path).resolve()
        if root not in roots:
            roots.append(root)

    return tuple(roots)


def unique_resolved_paths(paths: Iterable[Pathlike]) -> Tuple[Path, ...]:
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = Path(path).resolve()
        if resolved in seen:
            continue

        seen.add(resolved)
        unique.append(resolved)

    return tuple(unique)


def resolve_local_boundary(
    source_roots: Tuple[Path, ...],
    local_boundary: Optional[Pathlike],
) -> Optional[Path]:
    if local_boundary is not None:
        return Path(local_boundary).resolve()

    if source_roots:
        return source_roots[0]

    return None
