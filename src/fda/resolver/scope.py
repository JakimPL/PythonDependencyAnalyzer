from __future__ import annotations

from typing import Any, Dict, Optional

from fda.node.wrapper import ASTNodeWrapper


class Scope:
    def __init__(self, parent: Optional[Scope] = None) -> None:
        self.parent = parent
        self.symbols: Dict[str, ASTNodeWrapper[Any]] = {}

    def define(self, name: str, node: ASTNodeWrapper[Any]) -> None:
        self.symbols[name] = node

    def resolve(self, name: str) -> Optional[ASTNodeWrapper[Any]]:
        if name in self.symbols:
            return self.symbols[name]

        if self.parent:
            return self.parent.resolve(name)

        return None
