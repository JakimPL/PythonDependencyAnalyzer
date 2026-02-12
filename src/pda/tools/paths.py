from collections.abc import Iterable
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Generic, List, Optional, Protocol, Union, overload

from pda.tools import logger
from pda.types import AnyT, AnyT_co, Pathlike


class PathlikeFunction(Protocol, Generic[AnyT_co]):
    __name__: str

    def __call__(self, path: Pathlike, *args: Any, **kwargs: Any) -> AnyT_co: ...


class OptionalPathlikeFunction(Protocol, Generic[AnyT_co]):
    __name__: str

    def __call__(self, path: Optional[Pathlike], *args: Any, **kwargs: Any) -> AnyT_co: ...


@overload
def safe_path(
    default: Callable[[], AnyT],
) -> Callable[[PathlikeFunction[AnyT]], OptionalPathlikeFunction[AnyT]]: ...


@overload
def safe_path(default: AnyT) -> Callable[[PathlikeFunction[AnyT]], OptionalPathlikeFunction[AnyT]]: ...


def safe_path(
    default: Union[AnyT, Callable[[], AnyT]],
) -> Callable[[PathlikeFunction[AnyT]], OptionalPathlikeFunction[AnyT]]:
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

    def decorator(func: PathlikeFunction[AnyT]) -> OptionalPathlikeFunction[AnyT]:
        @wraps(func)
        def wrapper(path: Optional[Pathlike], *args: Any, **kwargs: Any) -> AnyT:
            value = get_default()
            try:
                if path is None:
                    return value

                return func(path, *args, **kwargs)
            except (OSError, PermissionError, RuntimeError):
                logger.warning("Error accessing path in %s, returning default value.", func.__name__)
                return value

        return wrapper

    return decorator


def default_path_factory() -> Optional[Path]:
    return None


def default_path_list_factory() -> List[Path]:
    return []


@safe_path(default=default_path_factory)
def resolve_path(path: Pathlike) -> Optional[Path]:
    """
    Resolves a given path to an absolute path. If the input is None, returns None.

    Warning: Empty string is treated as a valid path and will be resolved to
    the current working directory.

    Args:
        path: The path to resolve, or None.

    Returns:
        The resolved absolute path, or None if the input was None.
    """
    return Path(path).resolve()


@safe_path(default=False)
def exists(path: Pathlike) -> bool:
    """
    Checks if the given path exists.

    Args:
        path: The path to check.

    Returns:
        True if the path exists, False otherwise.
    """
    return Path(path).exists()


@safe_path(default=False)
def is_dir(path: Pathlike) -> bool:
    """
    Checks if the given path is a directory.

    Args:
        path: The path to check.

    Returns:
        True if the path is a directory, False otherwise.
    """
    return Path(path).is_dir()


@safe_path(default=False)
def is_file(path: Pathlike) -> bool:
    """
    Checks if the given path is a file.

    Args:
        path: The path to check.

    Returns:
        True if the path is a file, False otherwise.
    """
    return Path(path).is_file()


@safe_path(default=default_path_list_factory)
def iterdir(path: Pathlike) -> List[Path]:
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
    return sorted(Path(path).iterdir())


@safe_path(default=default_path_list_factory)
def glob(path: Pathlike, pattern: str) -> List[Path]:
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
    return sorted(Path(path).glob(pattern))


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
        raise TypeError("Input must be a path or an iterable of paths.")

    return [Path(path).resolve() for path in paths]
