from pydantic import Field

from fda.specification.base import Specification
from fda.specification.imports.condition import ImportCondition
from fda.specification.imports.type import ImportType
from fda.specification.symbols.symbol import Symbol


class ImportStatement(Specification):
    symbol: Symbol = Field(..., description="Entity of the import statement")
    fqn: str = Field(..., description="Import path, e.g. 'package.module' or 'package.module.ClassName'")
    type: ImportType = Field(
        ImportType.STATIC,
        description="Type of import statement (e.g. 'STATIC', 'DYNAMIC', 'CONDITIONAL' or 'DYNAMIC_CONDITIONAL')",
    )
    condition: ImportCondition = Field(
        ImportCondition.NONE,
        description="Branch type under which this import is executed",
    )
