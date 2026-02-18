from typing import Any, Tuple, override

from pda.specification import CategorizedModule
from pda.structures.node.base import Node


class ModuleNode(Node[CategorizedModule]):
    def __init__(self, module: CategorizedModule, *, ordinal: int = 0, level: int = 0) -> None:
        label = module.module_name
        details = module.name
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
        )

    @property
    def module(self) -> CategorizedModule:
        return self.item

    @property
    @override
    def key(self) -> Tuple[Any, ...]:
        return (self.level, self.order, self.details, self.label, self.ordinal)
