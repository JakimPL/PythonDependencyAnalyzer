from __future__ import annotations

import ast
from functools import cached_property
from pathlib import Path
from typing import Any, Generic, Iterable, Optional, Tuple, Type, TypeVar, Union

from anytree import NodeMixin

NodeT = TypeVar("NodeT", bound=ast.AST)


class ASTNode(NodeMixin, Generic[NodeT]):  # type: ignore[misc]
    def __init__(
        self,
        node: NodeT,
        filepath: Path,
        parent: Optional[ASTNode[Any]] = None,
    ) -> None:
        self.ast: NodeT = node
        self.type: Type[NodeT] = type(node)
        self.filepath: Path = filepath.with_suffix("")

        self.parent: Optional[ASTNode[Any]] = parent

    @cached_property
    def name(self) -> str:
        if isinstance(self.ast, (ast.FunctionDef, ast.ClassDef)):
            return self.ast.name

        if isinstance(self.ast, ast.Name):
            return self.ast.id

        if isinstance(self.ast, ast.Call):
            if isinstance(self.ast.func, ast.Name):
                return self.ast.func.id
            if isinstance(self.ast.func, ast.Attribute):
                return self.ast.func.attr

        name = self.type.__name__
        return getattr(self.ast, "name", name)

    def has_ancestor(self, ancestor: Union[ASTNode[Any], Iterable[ASTNode[Any]]]) -> bool:
        current = self.parent
        ancestors = {ancestor} if isinstance(ancestor, ASTNode) else set(ancestor)
        while current:
            if current in ancestors:
                return True

            current = current.parent

        return False

    def has_ancestor_of_type(
        self,
        ancestor_type: Union[Type[ASTNode[Any]], Tuple[Type[ASTNode[Any]], ...]],
    ) -> bool:
        current = self.parent
        while current:
            if isinstance(current, ancestor_type):
                return True

            current = current.parent

        return False
