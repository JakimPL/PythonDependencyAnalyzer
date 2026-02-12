from importlib.machinery import ModuleSpec
from typing import Any, NamedTuple

from pda.specification.modules.category import ModuleCategory
from pda.specification.modules.module import Module


class ModuleWrapper(NamedTuple):
    spec: ModuleSpec
    module: Module
    category: ModuleCategory

    def __getattr__(self, item: Any) -> Any:
        return getattr(self.module, item)
