from pda.specification import CategorizedModule
from pda.structures.node.base import Node


class ModuleNode(Node[CategorizedModule]):
    def __init__(self, module: CategorizedModule, *, ordinal: int = 0, level: int = 0) -> None:
        label = module.name
        group = module.category.value
        super().__init__(
            item=module,
            ordinal=ordinal,
            label=label,
            level=level,
            group=group,
        )

    @property
    def module(self) -> CategorizedModule:
        return self.item
