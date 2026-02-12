from __future__ import annotations

import ast
from typing import Optional

from pydantic import Field

from pda.specification.base import Specification


class SourceSpan(Specification):
    """
    Represents a location span in source code.

    Uses 1-based line numbers and 0-based column offsets,
    matching Python's AST conventions.
    """

    lineno: int = Field(..., ge=1, description="Starting line number (1-based)")
    col_offset: int = Field(..., ge=0, description="Starting column offset (0-based)")
    end_lineno: Optional[int] = Field(..., ge=1, description="Ending line number (1-based)")
    end_col_offset: Optional[int] = Field(..., ge=0, description="Ending column offset (0-based)")

    @classmethod
    def from_ast(cls, node: ast.stmt) -> SourceSpan:
        """
        Create SourceSpan from an AST node.

        Args:
            node: AST node with lineno, col_offset, end_lineno, end_col_offset.

        Returns:
            SourceSpan instance.
        """
        return cls(
            lineno=node.lineno,
            col_offset=node.col_offset,
            end_lineno=node.end_lineno,
            end_col_offset=node.end_col_offset,
        )
