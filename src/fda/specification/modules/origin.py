from __future__ import annotations

from enum import StrEnum
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Union


class OriginType(StrEnum):
    NONE = "none"
    PYTHON = "python"
    NON_PYTHON = "non-python"
    FROZEN = "frozen"
    BUILT_IN = "built-in"

    @classmethod
    def from_spec(cls, spec: Union[str, ModuleSpec]) -> OriginType:
        origin = spec.origin if isinstance(spec, ModuleSpec) else spec
        match origin:
            case None:
                return cls.NONE
            case "frozen":
                return cls.FROZEN
            case "built-in":
                return cls.BUILT_IN
            case _:
                path = Path(origin)
                if path.suffix == ".py":
                    return cls.PYTHON

                return cls.NON_PYTHON
