from typing import Dict, TypeAlias

from pydepgraph.specification.modules.category import ModuleCategory
from pydepgraph.specification.modules.module import Module

ModuleDict: TypeAlias = Dict[str, Module]
ModulesCollection: TypeAlias = Dict[ModuleCategory, ModuleDict]
