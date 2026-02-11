from pathlib import Path
from typing import Optional, overload

from pydepgraph.types import Pathlike


@overload
def resolve_path(path: Pathlike) -> Path: ...


@overload
def resolve_path(path: None) -> None: ...


def resolve_path(path: Optional[Pathlike]) -> Optional[Path]:
    """
    Resolves a given path to an absolute path. If the input is None, returns None.

    Warning: Empty string is treated as a valid path and will be resolved to
    the current working directory.

    Args:
        path: The path to resolve, or None.

    Returns:
        The resolved absolute path, or None if the input was None.
    """
    if path is None:
        return None

    return Path(path).resolve()
