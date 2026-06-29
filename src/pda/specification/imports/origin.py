from __future__ import annotations

from enum import StrEnum
from pathlib import Path


class OriginType(StrEnum):
    NONE = "none"
    PYTHON = "python"
    NO_PYTHON = "no-python"
    FROZEN = "frozen"
    BUILT_IN = "built-in"

    @classmethod
    def from_origin(cls, origin: str | None) -> OriginType:
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

                return cls.NO_PYTHON
