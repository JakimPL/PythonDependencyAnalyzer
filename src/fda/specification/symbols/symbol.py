from __future__ import annotations

import ast
from pathlib import Path

from pydantic import Field

from fda.specification.base import Specification
from fda.specification.source.span import SourceSpan
from fda.specification.symbols.kind import SymbolKind


class Symbol(Specification):
    node: ast.AST = Field(..., description="Internal AST node")
    fqn: str = Field(description="Fully qualified name, e.g. module.path.ClassName")
    origin: Path = Field(description="Absolute file path where symbol is defined")
    span: SourceSpan = Field(description="Location in source file where symbol is defined")

    @property
    def kind(self) -> SymbolKind:
        return SymbolKind.from_ast(self.node)
