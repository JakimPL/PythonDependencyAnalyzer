from __future__ import annotations

import ast
from enum import StrEnum


class SymbolKind(StrEnum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    VARIABLE = "variable"

    @staticmethod
    def from_ast(node: ast.AST) -> SymbolKind:
        match node:
            case ast.Module():
                return SymbolKind.MODULE
            case ast.ClassDef():
                return SymbolKind.CLASS
            case ast.FunctionDef():
                return SymbolKind.FUNCTION
            case _:
                return SymbolKind.VARIABLE
