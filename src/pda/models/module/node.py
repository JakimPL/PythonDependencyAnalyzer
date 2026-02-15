from pda.specification import CategorizedModule
from pda.structures.node.base import Node


class ModuleNode(Node[CategorizedModule]):
    def __init__(self, module: CategorizedModule, *, level: int = 0) -> None:
        group = module.category.value
        super().__init__(
            item=module,
            label=module.name,
            level=level,
            group=group,
        )

    @property
    def module(self) -> CategorizedModule:
        return self.item
