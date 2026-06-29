from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Literal, Optional, get_args

from pda.exceptions import (
    PDAInvalidOriginTypeError,
    PDAMissingModuleSpecError,
    PDANoOriginError,
    PDAOriginFileNotFoundError,
)
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
