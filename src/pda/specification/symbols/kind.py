from __future__ import annotations

import ast
from enum import StrEnum


class SymbolKind(StrEnum):
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    MODULE = "module"

    @staticmethod
    def from_ast(node: ast.AST) -> SymbolKind:
        match node:
            case ast.FunctionDef():
                return SymbolKind.FUNCTION
            case ast.ClassDef():
                return SymbolKind.CLASS
            case ast.Module():
                return SymbolKind.MODULE
            case _:
                return SymbolKind.VARIABLE
