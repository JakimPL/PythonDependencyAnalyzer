from __future__ import annotations

import ast
from collections import deque
from pathlib import Path
from typing import Any, Deque, Generic, List, Optional, Type, TypeVar

from anytree import Node

NodeT = TypeVar("NodeT", bound=ast.AST)


class ASTNodeWrapper(Node, Generic[NodeT]):  # type: ignore[misc]
    def __init__(
        self,
        ast_node: NodeT,
        filepath: Path,
        parent: Optional[ASTNodeWrapper[Any]] = None,
    ) -> None:
        self.ast_node: NodeT = ast_node
        self.ast_type: Type[NodeT] = type(ast_node)
        self.ast_name: str = self.get_name()
        super().__init__(self.ast_name, parent=parent)

        self.filepath: Path = filepath.with_suffix("")
        self.functions: List[ASTNodeWrapper[ast.FunctionDef]] = self.get_functions(parent)
        self.classes: List[ASTNodeWrapper[ast.ClassDef]] = self.get_classes(parent)

    @property
    def full_name(self) -> str:
        chain = self.get_chain()
        return ".".join(node.ast_name for node in chain)

    @property
    def full_path(self) -> str:
        chain = self.get_chain()
        names = [str(self.filepath)]
        names.extend(
            [node.ast_name for node in chain if isinstance(node.ast_node, (ast.FunctionDef, ast.ClassDef, ast.Call))]
        )
        return ".".join(names)

    def get_chain(self) -> Deque[ASTNodeWrapper[Any]]:
        chain: Deque[ASTNodeWrapper[Any]] = deque([])
        node: Optional[ASTNodeWrapper[Any]] = self
        while node is not None:
            chain.appendleft(node)
            node = node.parent

        return chain

    def get_name(self) -> str:
        if isinstance(self.ast_node, (ast.FunctionDef, ast.ClassDef)):
            return self.ast_node.name

        if isinstance(self.ast_node, ast.Name):
            return self.ast_node.id

        if isinstance(self.ast_node, ast.Call):
            if isinstance(self.ast_node.func, ast.Name):
                return self.ast_node.func.id
            if isinstance(self.ast_node.func, ast.Attribute):
                return self.ast_node.func.attr

        name = self.ast_type.__name__
        return getattr(self.ast_node, "name", name)

    def get_functions(
        self,
        parent: Optional[ASTNodeWrapper[Any]],
    ) -> List[ASTNodeWrapper[ast.FunctionDef]]:
        functions = []
        if parent is not None:
            functions.extend(parent.functions)

        if isinstance(self.ast_node, ast.FunctionDef):
            functions.append(self)

        return functions

    def get_classes(
        self,
        parent: Optional[ASTNodeWrapper[Any]],
    ) -> List[ASTNodeWrapper[ast.ClassDef]]:
        classes = []
        if parent is not None:
            classes.extend(parent.classes)

        if isinstance(self.ast_node, ast.ClassDef):
            classes.append(self)

        return classes

    def add_function(self, other: ASTNodeWrapper[ast.FunctionDef]) -> None:
        self.functions.append(other)

    def add_class(self, other: ASTNodeWrapper[ast.ClassDef]) -> None:
        self.classes.append(other)
