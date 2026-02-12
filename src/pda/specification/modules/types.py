from typing import Dict, TypeAlias

from pda.specification.modules.category import ModuleCategory
from pda.specification.modules.module import Module

ModuleDict: TypeAlias = Dict[str, Module]
ModulesCollection: TypeAlias = Dict[ModuleCategory, ModuleDict]
