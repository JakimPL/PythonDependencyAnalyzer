from __future__ import annotations

import ast
from functools import cached_property
from typing import Any, Generic, Optional, Type

from pda.graph.types import NodeT
from pda.nodes.base import BaseNode


class ASTNode(BaseNode[NodeT], Generic[NodeT]):
    def __init__(
        self,
        node: NodeT,
        parent: Optional[ASTNode[Any]] = None,
    ) -> None:
        super().__init__(item=node, parent=parent)
        self.ast: NodeT = node
        self.type: Type[NodeT] = type(node)

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
