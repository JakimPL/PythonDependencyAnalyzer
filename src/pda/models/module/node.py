from typing import Any, Dict, Optional, Tuple, override

from pda.specification import CategorizedModule
from pda.structures.node.base import Node


class ModuleNode(Node[CategorizedModule]):
    def __init__(
        self,
        module: CategorizedModule,
        *,
        ordinal: int = 0,
        level: int = 0,
        qualified_name: bool = False,
        label: Optional[str] = None,
    ) -> None:
        if label is None:
            label = module.qualified_name if qualified_name else module.module_name

        available = module.available
        details = module.name
        if not available and module.availability_reason:
            details = f"{module.name} — {module.availability_reason}"

        group = module.category.value
        order = module.category.order
        super().__init__(
            item=module,
            ordinal=ordinal,
            label=label,
            details=details,
            level=level,
            order=order,
            group=group,
            available=available,
        )

    @property
    def module(self) -> CategorizedModule:
        return self.item

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModuleNode):
            return NotImplemented

        return self.module.qualified_name == other.module.qualified_name and self.ordinal == other.ordinal

    @override
    def __hash__(self) -> int:
        return hash((self.module.qualified_name, self.ordinal))

    @property
    @override
    def key(self) -> Tuple[Any, ...]:
        return (self.level, self.order, self.details, self.label, self.ordinal)

    @property
    @override
    def identifier(self) -> str:
        name = self.module.qualified_name
        return f"{name}#{self.ordinal}" if self.ordinal else name

    @override
    def serialize(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.identifier,
            "label": self.label,
            "category": self.group,
            "level": self.level,
        }

        if not self.available:
            data["available"] = False
            diagnostic = self.module.diagnostic
            if diagnostic is not None:
                data["diagnostic"] = diagnostic.code.value

        origin = self.module.origin
        if origin is not None:
            data["origin"] = str(origin)

        data.update(self.cycle_data())
        return data
