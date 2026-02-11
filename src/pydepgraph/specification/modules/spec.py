from importlib.machinery import ModuleSpec
from importlib.util import find_spec
from pathlib import Path
from typing import Literal, Optional, get_args

from pydepgraph.exceptions import (
    PDGEmptyOriginError,
    PDGFrozenOriginError,
    PDGInvalidOriginTypeError,
    PDGMissingModuleSpecError,
    PDGOriginFileNotFoundError,
    PDGRelativeBasePathError,
)
from pydepgraph.tools import logger

SpecialOrigin = Literal["frozen", "built-in"]
SPECIAL_ORIGINS = get_args(SpecialOrigin)


def is_spec_origin_valid(origin: Optional[str]) -> bool:
    if not origin or origin in SPECIAL_ORIGINS:
        return False

    path = Path(origin)
    if not path.is_absolute():
        return False

    return path.is_file() or path.is_dir()


def validate_spec_origin(spec: ModuleSpec, expect_python: bool = True) -> None:
    name = spec.name
    if not spec.origin:
        raise PDGEmptyOriginError(f"Module spec '{name}' has no origin path")

    if expect_python and spec.origin in SPECIAL_ORIGINS:
        raise PDGFrozenOriginError(f"Module '{name}' is frozen/built-in and cannot be analyzed")

    origin = Path(spec.origin)
    if not origin.is_absolute():
        raise PDGRelativeBasePathError(f"Module '{name}' has non-absolute origin path: '{spec.origin}'")

    if not origin.is_file():
        raise PDGOriginFileNotFoundError(
            f"Module '{name}' has origin '{spec.origin}' that does not exist or is not a file"
        )

    if expect_python and origin.is_file() and origin.suffix != ".py":
        raise PDGInvalidOriginTypeError(f"Module '{name}' has non-Python origin file: '{spec.origin}'")


def validate_spec(
    spec: Optional[ModuleSpec],
    validate_origin: bool = True,
    expect_python: bool = False,
) -> ModuleSpec:
    if not spec:
        raise PDGMissingModuleSpecError("Module spec not found")

    if validate_origin:
        validate_spec_origin(spec, expect_python=expect_python)

    return spec


def find_module_spec(name: str, package: Optional[str] = None) -> Optional[ModuleSpec]:
    try:
        return find_spec(name, package=package)
    except (ImportError, ModuleNotFoundError, ValueError) as error:
        logger.warning("An error occurred while finding spec for module %s: %s", name, error)

    return None
