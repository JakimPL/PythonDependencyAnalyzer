from pathlib import Path
from typing import List

from pydantic import Field

from pda.specification.base import Specification
from pda.specification.imports.path import ImportPath
from pda.specification.imports.scope import ImportScope
from pda.specification.source.span import SourceSpan


class ImportStatement(Specification):
    origin: Path = Field(..., description="The file from which this import statement was extracted")
    span: SourceSpan = Field(..., description="Source code span of the import statement")
    path: ImportPath = Field(
        ...,
        description="The import path, e.g. 'package.module' or 'package.module:ClassName'",
    )
    scopes: List[ImportScope] = Field(
        default_factory=list,
        description="Scope in which this import is executed, from innermost to outermost",
    )

    def in_scope(self, scope: ImportScope) -> bool:
        """Check if this import statement is within the given scope.

        Args:
            scope: The scope flag(s) to check for

        Returns:
            True if any of the statement's scopes contain the given scope flag(s)

        Examples:
            If checking for IF and scope is (IF | MAIN), returns True
            If checking for (IF | TYPE_CHECKING) and scope contains both flags, returns True
        """
        return any((s & scope) == scope for s in self.scopes)
