from pydantic import Field

from pda.specification.base import Specification
from pda.specification.imports.path import ImportPath
from pda.specification.imports.scope import ImportScope


class ImportStatement(Specification):
    path: ImportPath = Field(
        ...,
        description="The import path, e.g. 'package.module' or 'package.module:ClassName'",
    )
    scope: ImportScope = Field(
        ImportScope.NONE,
        description="Scope in which this import is executed",
    )
