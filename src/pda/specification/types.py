import ast
from typing import Iterable, TypeAlias, Union

Alias: TypeAlias = Union[ast.alias, str]
Names: TypeAlias = Union[Iterable[ast.alias], Iterable[str], Iterable[Alias]]
