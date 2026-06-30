from collections.abc import Iterable
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Generic, List, Optional, Protocol, Union, overload

from pda.constants import DELIMITER
from pda.tools.logger import logger
from pda.types import AnyT, AnyT_co, Pathlike


class PathFunction(Protocol, Generic[AnyT_co]):
    __name__: str

    def __call__(self, path: Path, *args: Any, **kwargs: Any) -> AnyT_co: ...


class OptionalPathlikeFunction(Protocol, Generic[AnyT_co]):
    __name__: str

    def __call__(self, path: Optional[Pathlike], *args: Any, **kwargs: Any) -> AnyT_co: ...


@overload
def safe_path(
    default: Callable[[], AnyT],
) -> Callable[[PathFunction[AnyT]], OptionalPathlikeFunction[AnyT]]: ...


@overload
def safe_path(default: AnyT) -> Callable[[PathFunction[AnyT]], OptionalPathlikeFunction[AnyT]]: ...


def safe_path(
    default: Union[AnyT, Callable[[], AnyT]],
) -> Callable[[PathFunction[AnyT]], OptionalPathlikeFunction[AnyT]]:
    """
    Decorator that wraps a function with error handling for path operations.
    Returns the provided default value if OSError, PermissionError, or RuntimeError occurs.

    If callable is provided as default, it will be called to get the default value
    each time an error occurs.

    Args:
        default: The default value or a factory function
            to return if an error occurs.

    Returns:
        A decorator function.
    """

    def get_default() -> AnyT:
        if callable(default):
            return default()

        return default

    def decorator(func: PathFunction[AnyT]) -> OptionalPathlikeFunction[AnyT]:
        @wraps(func)
        def wrapper(path: Optional[Pathlike], *args: Any, **kwargs: Any) -> AnyT:
            value = get_default()
            try:
                if path is None:
                    return value

                return func(Path(path), *args, **kwargs)
            except (OSError, PermissionError, RuntimeError):
                logger.warning(
                    "Error accessing path '%s' in %s, returning default value %s.",
                    path,
                    func.__name__,
                    value,
                )
                return value

        return wrapper

    return decorator


def default_path_factory() -> Optional[Path]:
    return None


def default_path_list_factory() -> List[Path]:
    return []


@safe_path(default=default_path_factory)
def resolve_path(path: Path) -> Optional[Path]:
    """
    Resolves a given path to an absolute path. If the input is None, returns None.

    Warning: Empty string is treated as a valid path and will be resolved to
    the current working directory.

    Args:
        path: The path to resolve, or None.

    Returns:
        The resolved absolute path, or None if the input was None.
    """
    return path.resolve()


@safe_path(default=False)
def is_symlink(path: Path) -> bool:
    """
    Checks if the given path is a symbolic link.

    Args:
        path: The path to check.

    Returns:
        True if the path is a symbolic link, False otherwise.
    """
    return path.is_symlink()


@safe_path(default=False)
def exists(path: Path, *, follow_symlinks: bool = False) -> bool:
    """
    Checks if the given path exists.

    Args:
        path: The path to check.
        follow_symlinks: Whether to follow symbolic links when checking for existence.
            Default is False.

    Returns:
        True if the path exists, False otherwise.
    """
    return path.exists(follow_symlinks=follow_symlinks)


@safe_path(default=False)
def is_dir(path: Path, *, follow_symlinks: bool = False) -> bool:
    """
    Checks if the given path is a directory.

    Args:
        path: The path to check.
        follow_symlinks: Whether to follow symbolic links when checking
            if the path is a directory. Default is False.


    Returns:
        True if the path is a directory, False otherwise.
    """
    return path.is_dir(follow_symlinks=follow_symlinks)


@safe_path(default=False)
def is_file(path: Path, *, follow_symlinks: bool = False) -> bool:
    """
    Checks if the given path is a file.

    Args:
        path: The path to check.
        follow_symlinks: Whether to follow symbolic links when checking
            if the path is a file. Default is False.

    Returns:
        True if the path is a file, False otherwise.
    """
    return path.is_file(follow_symlinks=follow_symlinks)


@safe_path(default=False)
def is_python_file(path: Path, *, follow_symlinks: bool = False) -> bool:
    """
    Checks if the given path is a Python file (i.e., has a .py extension).

    Args:
        path: The path to check.
        follow_symlinks: Whether to follow symbolic links when checking
            if the path is a file. Default is False.

    Returns:
        True if the path is a Python file, False otherwise.
    """
    return path.is_file(follow_symlinks=follow_symlinks) and path.suffix.lower() == ".py"


@safe_path(default=True)
def does_skip_path(path: Path) -> bool:
    """
    Determines whether a given path should be skipped based on its name.

    Paths that start with a dot (.) or are named "__pycache__" are considered
    hidden or special directories and will be skipped.

    Args:
        path: The path to check.

    Returns:
        True if the path should be skipped, False otherwise.
    """
    return path.name.startswith(DELIMITER) or path.name == "__pycache__" or path.is_symlink()


@safe_path(default=default_path_list_factory)
def iterdir(path: Path) -> List[Path]:
    """
    Safely iterates over the contents of a directory,
    returning an empty list if an error occurs.

    Returns a sorted list of Path objects.

    Args:
        path: The directory path to iterate over.

    Returns:
        A list of Path objects representing the contents of the directory, or an empty list if an
        error occurs.
    """
    return sorted(path for path in path.iterdir() if not does_skip_path(path))


@safe_path(default=default_path_list_factory)
def glob(path: Path, pattern: str) -> List[Path]:
    """
    Safely performs a glob operation on the given path,
    returning an empty list if an error occurs.

    Returns a sorted list of Path objects.

    Args:
        path: The directory path to perform the glob operation on.
        pattern: The glob pattern to match files against.

    Returns:
        A list of Path objects representing the matched files, or an empty list if an error occurs.
    """
    return sorted(path.glob(pattern))


def normalize_paths(paths: Union[Pathlike, Iterable[Pathlike]]) -> List[Path]:
    """
    Normalizes a single path or an iterable of paths to a list of resolved Path objects.

    Args:
        paths: A single path or an iterable of paths to normalize.

    Returns:
        A list of resolved Path objects.
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]

    elif not isinstance(paths, Iterable):
        raise TypeError("Input must be a path or an iterable of paths")

    return [Path(path).resolve() for path in paths]


def filter_subdirectories(paths: Iterable[Pathlike]) -> List[Path]:
    """
    Filter out paths that are subdirectories of any other path in the list.

    Returns only the "root" paths, removing any paths that are nested within others.

    Example:
        Input: ['/usr/lib/python3.10', '/usr/lib/python3.10/site-packages', '/home/user/project']
        Output: ['/usr/lib/python3.10', '/home/user/project']

    Args:
        paths: An iterable of paths to filter.

    Returns:
        A sorted list of Path objects with subdirectories removed.
    """
    resolved_paths = [Path(path).resolve() for path in paths]
    resolved_paths.sort(key=lambda path: len(path.parts))

    filtered: List[Path] = []
    for path in resolved_paths:
        if not any(path.is_relative_to(root) for root in filtered):
            filtered.append(path)

    return sorted(filtered)
