from functools import lru_cache
from importlib.machinery import ModuleSpec
from importlib.util import find_spec
from pathlib import Path
from typing import Literal, Optional, get_args, overload

from pda.exceptions import (
    PDAFindSpecError,
    PDAInvalidOriginTypeError,
    PDAMissingModuleSpecError,
    PDANoOriginError,
    PDAOriginFileNotFoundError,
)
from pda.tools.logger import logger
from pda.tools.paths import is_file, is_python_file

SpecialOrigin = Literal["frozen", "built-in"]
SPECIAL_ORIGINS = get_args(SpecialOrigin)


def is_module(spec: ModuleSpec) -> bool:
    return not spec.submodule_search_locations


def is_package(spec: ModuleSpec) -> bool:
    return spec.submodule_search_locations is not None


def is_namespace_package(spec: ModuleSpec) -> bool:
    return is_package(spec) and not spec.origin


def validate_spec_origin(
    spec: ModuleSpec,
    *,
    expect_python: bool = True,
) -> Path:
    name = spec.name
    if not spec.origin:
        raise PDANoOriginError(f"Module spec '{name}' has no origin path")

    if expect_python and spec.origin in SPECIAL_ORIGINS:
        raise PDAInvalidOriginTypeError(f"Module '{name}' is frozen/built-in/no-python and cannot be analyzed")

    origin = Path(spec.origin)
    if expect_python:
        if not is_file(origin):
            raise PDAOriginFileNotFoundError(
                f"Module '{name}' has origin '{spec.origin}' that does not exist or is not a file"
            )

        if not is_python_file(origin):
            raise PDAInvalidOriginTypeError(f"Module '{name}' has non-Python origin file: '{spec.origin}'")

    return origin


def validate_spec(
    spec: Optional[ModuleSpec],
    *,
    validate_origin: bool = True,
    expect_python: bool = True,
) -> ModuleSpec:
    if not spec:
        raise PDAMissingModuleSpecError("Module spec not found")

    if validate_origin and not is_namespace_package(spec):
        validate_spec_origin(spec, expect_python=expect_python)

    return spec


@overload
def find_module_spec(
    name: str,
    package: Optional[str] = None,
    *,
    allow_missing_spec: Literal[False] = False,
    raise_error: bool = True,
    validate_origin: bool = True,
    expect_python: bool = True,
) -> ModuleSpec: ...


@overload
def find_module_spec(
    name: str,
    package: Optional[str] = None,
    *,
    allow_missing_spec: Literal[True],
    raise_error: bool = True,
    validate_origin: bool = True,
    expect_python: bool = True,
) -> Optional[ModuleSpec]: ...


@lru_cache(maxsize=None)
def find_module_spec(
    name: str,
    package: Optional[str] = None,
    *,
    allow_missing_spec: bool = False,
    raise_error: bool = True,
    validate_origin: bool = True,
    expect_python: bool = True,
) -> Optional[ModuleSpec]:
    spec: Optional[ModuleSpec] = None
    try:
        spec = find_spec(name, package=package)
    except (ImportError, ModuleNotFoundError, ValueError) as error:
        logger.debug("Error finding spec for module '%s': %s", name, error)
    except (PermissionError, OSError) as error:
        error_message = f"{error.__class__.__name__}: {error}"
        message = f"An error occurred while finding spec for module '{name}' of package '{package}'"
        if raise_error:
            raise PDAFindSpecError(message) from error

        logger.warning("%s: %s", message, error_message)

    if spec is None:
        if allow_missing_spec:
            if name != "__main__":
                logger.debug("Module spec for module '%s' not found", name)

            return None

        raise PDAMissingModuleSpecError(f"Module spec for module '{name}' not found")

    return validate_spec(spec, validate_origin=validate_origin, expect_python=expect_python)
