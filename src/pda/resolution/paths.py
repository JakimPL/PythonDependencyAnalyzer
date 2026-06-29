from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from pda.tools.paths import is_python_file


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def longest_containing_root(path: Path, roots: Iterable[Path]) -> Optional[Path]:
    matching_roots = [root for root in roots if is_relative_to(path, root)]
    if not matching_roots:
        return None

    return max(matching_roots, key=lambda root: len(root.parts))


def unique_path_entries(paths: Iterable[Path]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for path in paths:
        entry = str(path)
        if entry in seen:
            continue

        seen.add(entry)
        unique.append(entry)

    return tuple(unique)


def has_python_file_in_tree(path: Path) -> bool:
    try:
        return any(is_python_file(child) for child in path.rglob("*"))
    except OSError:
        return False
