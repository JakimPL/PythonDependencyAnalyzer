from importlib.machinery import ModuleSpec
from importlib.util import find_spec
from pathlib import Path
from typing import Literal, Optional, get_args

from fda.exceptions import (
    FDAEmptyOriginError,
    FDAFrozenOriginError,
    FDAInvalidOriginTypeError,
    FDAMissingModuleSpecError,
    FDAOriginFileNotFoundError,
    FDARelativeBasePathError,
)
from fda.tools import logger

SpecialOrigin = Literal["frozen", "built-in"]
SPECIAL_ORIGINS = get_args(SpecialOrigin)


def is_spec_origin_valid(origin: Optional[str]) -> bool:
    if not origin or origin in SPECIAL_ORIGINS:
        return False

    path = Path(origin)
    if not path.is_absolute():
        return False

    return path.is_file() or path.is_dir()


def validate_spec_origin(spec: ModuleSpec) -> None:
    name = spec.name
    if not spec.origin:
        raise FDAEmptyOriginError(f"Module spec '{name}' has no origin path")

    if spec.origin in SPECIAL_ORIGINS:
        raise FDAFrozenOriginError(f"Module spec '{name}' is frozen/built-in and cannot be analyzed")

    origin = Path(spec.origin)
    if not origin.is_absolute():
        raise FDARelativeBasePathError(f"Module spec '{name}' has non-absolute origin path: '{spec.origin}'")

    if not origin.is_file():
        raise FDAOriginFileNotFoundError(
            f"Module spec '{name}' has origin '{spec.origin}' that does not exist or is not a file"
        )

    if origin.is_file() and origin.suffix != ".py":
        raise FDAInvalidOriginTypeError(f"Module spec '{name}' has non-Python origin file: '{spec.origin}'")


def validate_spec(spec: Optional[ModuleSpec], validate_origin: bool = True) -> ModuleSpec:
    if not spec:
        raise FDAMissingModuleSpecError("Module spec not found")

    if validate_origin:
        validate_spec_origin(spec)

    return spec


def find_module_spec(name: str, package: Optional[str] = None) -> Optional[ModuleSpec]:
    try:
        return find_spec(name, package=package)
    except (ImportError, ModuleNotFoundError, ValueError) as error:
        logger.warning("An error occurred while finding spec for module %s: %s, skipping...", name, error)

    return None
