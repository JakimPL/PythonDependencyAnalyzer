import ast
import os
import re
from functools import cached_property
from importlib.util import resolve_name
from pathlib import Path
from typing import List, NamedTuple, Optional, Self, Union

from pydantic import Field, model_validator

from fda.node import Node, get_ast
from fda.specification.base import Specification
from fda.specification.constants import DELIMITER
from fda.types import Pathlike


class PartsAndLevel(NamedTuple):
    parts: List[str]
    level: int


class ImportPath(Specification):
    module: Optional[str] = Field(default=None, description="Full module name, e.g. 'package.module'")
    level: int = Field(default=0, ge=0, description="Relative import level (0 for absolute imports)")
    name: Optional[str] = Field(default=None, description="Imported object name")
    asname: Optional[str] = Field(default=None, description="Optional alias for the module")

    @model_validator(mode="after")
    def validate_level(self) -> Self:
        if self.level < 0:
            raise ValueError("Relative import level cannot be negative")

        if self.parts and any(not part for part in self.parts):
            raise ValueError("Parts cannot be empty")

        for part in self.parts:
            if DELIMITER in part:
                raise ValueError(f"Part '{part}' cannot contain the DELIMITER '{DELIMITER}'")

        return self

    def __bool__(self) -> bool:
        return bool(self.parts or self.level > 0)

    def __str__(self) -> str:
        return self.join()

    def __truediv__(self, other: Optional[Union[str, Self]]) -> Self:
        if not other:
            return self

        if not self.is_module:
            raise ValueError("Cannot join to a non-module ImportPath")

        cls = self.__class__
        if isinstance(other, str):
            parts: List[str] = self.parts
            parts.extend(self.split(other))

            return cls(
                module=DELIMITER.join(parts),
                level=self.level,
            )

        if not isinstance(other, cls):
            raise TypeError(f"Unsupported operand type(s) for /: '{type(self)}' and '{type(other)}'")

        if other.level > 0:
            self = self.get_parent(other.level)

        if not self.module:
            module = other.module
        else:
            module = f"{self.module}{DELIMITER}{other.module}" if other.module else self.module

        return cls(
            module=module,
            name=other.name,
            level=self.level,
            asname=other.asname,
        )

    @property
    def parts(self) -> List[str]:
        components = []
        if self.module:
            components.extend(self.split(self.module))

        if self.name:
            components.append(self.name)

        return components

    @cached_property
    def path(self) -> str:
        return self.join(include_name=False)

    @property
    def absolute(self) -> bool:
        return self.level == 0

    @property
    def is_module(self) -> bool:
        return not self.name

    @cached_property
    def base(self) -> str:
        result = DELIMITER * self.level
        if self.parts:
            result += self.parts[0]

        return result

    def join(self, include_name: bool = True) -> str:
        result = DELIMITER * self.level

        if self.module:
            result += self.module

        if include_name and self.name:
            if result and not result.endswith(DELIMITER):
                result += DELIMITER

            result += self.name or ""

        return result

    def get_module_path(self) -> Self:
        cls = self.__class__
        return cls(module=self.module, level=self.level, asname=self.asname if self.is_module else None)

    def get_parent(self, levels: int = 1) -> Self:
        if levels < 0:
            raise ValueError("Levels must be a non-negative integer")

        if levels == 0:
            return self.model_copy()

        level = self.level
        parts = list(self.parts)

        if self.name and parts:
            parts.pop()

        for _ in range(levels):
            if parts:
                parts.pop()
            else:
                level += 1

        module = DELIMITER.join(parts) if parts else None
        return self.__class__(
            module=module,
            level=level,
            asname=None,
        )

    @staticmethod
    def split(name: str) -> List[str]:
        return name.split(DELIMITER)

    @classmethod
    def from_string(
        cls,
        name: str,
        asname: Optional[str] = None,
        is_module: bool = True,
    ) -> Self:
        if all(char == DELIMITER for char in name):
            return cls(level=len(name))

        if name.endswith(DELIMITER):
            raise ValueError("Module name cannot end with a DELIMITER")

        parts, level = cls._retrieve_parts_and_level(name)

        if any(not part for part in parts):
            raise ValueError(f"Malformed name: {name}, contains empty elements after leading dots")

        if is_module:
            module = DELIMITER.join(parts)
            return cls(module=module, level=level, asname=asname)

        return cls(module=DELIMITER.join(parts[:-1]), name=parts[-1], level=level, asname=asname)

    @staticmethod
    def _retrieve_parts_and_level(name: Optional[str] = None) -> PartsAndLevel:
        if not name:
            return PartsAndLevel([], 0)

        escaped = re.escape(DELIMITER)
        search = re.search(rf"^{escaped}+([^{escaped}].*)", name)
        if not search:
            qualified_name = name
            level = 0
        else:
            qualified_name = search.group(1)
            level = search.start(1)

        parts = ImportPath.split(qualified_name)
        return PartsAndLevel(parts, level)

    @classmethod
    def from_ast(
        cls,
        node: Optional[Union[Node[ast.Import], Node[ast.ImportFrom]]],
    ) -> List[Self]:
        if node is None:
            return [cls()]

        ast_node: Union[ast.Import, ast.ImportFrom] = get_ast(node)
        if isinstance(ast_node, ast.Import):
            return cls._from_ast_import(ast_node)

        if isinstance(ast_node, ast.ImportFrom):
            return cls._from_ast_import_from(ast_node)

        raise TypeError(f"Unsupported AST node type: {type(node)}, expected ast.Import or ast.ImportFrom")

    @classmethod
    def _from_ast_import(cls, node: ast.Import) -> List[Self]:
        paths: List[Self] = []
        for alias in node.names:
            paths.append(
                cls(
                    module=alias.name,
                    asname=alias.asname,
                )
            )

        return paths

    @classmethod
    def _from_ast_import_from(cls, node: ast.ImportFrom) -> List[Self]:
        paths: List[Self] = []
        for alias in node.names:
            paths.append(
                cls(
                    module=node.module,
                    level=node.level,
                    name=alias.name,
                    asname=alias.asname,
                )
            )

        return paths

    @classmethod
    def from_path(
        cls,
        path: Pathlike,
        project_root: Optional[Pathlike] = None,
    ) -> Self:
        path = Path(path)
        if path.is_absolute():
            if all(part == DELIMITER * 2 for part in path.parts):
                return cls(level=len(path.parts) + 1)

            if project_root:
                project_root = Path(project_root)
                if not project_root.is_absolute():
                    raise ValueError("Project root must be an absolute path")

                if not project_root.is_dir():
                    raise ValueError(f"Project root '{project_root}' must be a directory")

                path = path.relative_to(project_root)

        name = str(path.with_suffix("")).replace(os.path.sep, DELIMITER).removesuffix(".__init__")
        package = str(project_root).replace(os.path.sep, DELIMITER) if project_root else None
        return cls.from_string(resolve_name(name, package))

    @classmethod
    def get_relative_path(
        cls,
        origin: Path,
        package_root: Path,
    ) -> Optional[Self]:
        try:
            relative = origin.relative_to(package_root).with_suffix("")
            parts = relative.parts
            if parts[-1] == "__init__":
                parts = parts[:-1]

            return cls(module=DELIMITER.join(parts))
        except ValueError:
            return None
