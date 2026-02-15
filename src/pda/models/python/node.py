from __future__ import annotations

from typing import Optional, Type

from pda.models.python.dump import ast_dump, ast_label
from pda.structures import AnyNode
from pda.types import ASTT


class ASTNode(AnyNode[ASTT]):
    _ordinal_counter: int = 0

    def __init__(
        self,
        node: ASTT,
        *,
        parent: Optional[ASTNode[ASTT]] = None,
        label: Optional[str] = None,
    ) -> None:
        label = label or ast_label(node)
        group = type(node).__name__
        super().__init__(
            item=node,
            parent=parent,
            ordinal=self._ordinal(),
            label=label,
            group=group,
        )

    @property
    def ast(self) -> ASTT:
        return self.item

    @property
    def type(self) -> Type[ASTT]:
        return type(self.ast)

    def __str__(self) -> str:
        return ast_label(self.ast)

    def __repr__(self) -> str:
        return ast_dump(self.ast, short=True)

    @classmethod
    def _ordinal(cls) -> int:
        cls._ordinal_counter += 1
        return cls._ordinal_counter
