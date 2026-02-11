from pathlib import Path
from typing import TypeAlias, TypeVar, Union

T = TypeVar("T")
Pathlike: TypeAlias = Union[str, Path]
