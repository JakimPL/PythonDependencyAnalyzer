from collections.abc import Iterable
from pathlib import Path
from typing import TypeAlias, TypeVar, Union

AnyT = TypeVar("AnyT")
AnyT_co = TypeVar("AnyT_co", covariant=True)

Pathlike: TypeAlias = Union[str, Path]
PathInput: TypeAlias = Union[Pathlike, Iterable[Pathlike]]
