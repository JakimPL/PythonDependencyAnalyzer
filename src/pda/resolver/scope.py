from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from pda.nodes.python.node import ASTNode
from pda.specification import Symbol


class Scope:
    def __init__(self, parent: Optional[Scope] = None) -> None:
        self.parent = parent
        self.symbols: Dict[str, ASTNode[Any]] = {}
        self.imported_symbols: Dict[str, Symbol] = {}

    def define(self, name: str, node: ASTNode[Any]) -> None:
        self.symbols[name] = node

    def import_symbol(self, local_name: str, symbol: Symbol) -> None:
        self.imported_symbols[local_name] = symbol

    def resolve(self, name: str) -> Optional[ASTNode[Any]]:
        if name in self.symbols:
            return self.symbols[name]

        if self.parent:
            return self.parent.resolve(name)

        return None

    def resolve_import(self, name: str) -> Optional[Symbol]:
        if name in self.imported_symbols:
            return self.imported_symbols[name]

        if self.parent:
            return self.parent.resolve_import(name)

        return None

    def resolve_with_imports(self, name: str) -> Tuple[Optional[ASTNode[Any]], Optional[Symbol]]:
        local = self.resolve(name)
        imported = self.resolve_import(name)
        return local, imported
