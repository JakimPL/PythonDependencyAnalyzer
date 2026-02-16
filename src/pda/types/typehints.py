import ast
from collections.abc import Hashable, Iterable
from pathlib import Path
from typing import TypeAlias, TypeVar, Union

AnyT = TypeVar("AnyT")
AnyT_co = TypeVar("AnyT_co", covariant=True)

ASTT = TypeVar("ASTT", bound=ast.AST)

Pathlike: TypeAlias = Union[str, Path]
PathInput: TypeAlias = Union[Pathlike, Iterable[Pathlike]]
HashableT = TypeVar("HashableT", bound=Hashable)
