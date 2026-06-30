from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Optional, Tuple, Union

from pda.specification.imports.origin import OriginType
from pda.specification.modules.diagnostics import ResolutionDiagnostic
from pda.specification.modules.module.category import ModuleCategory
from pda.specification.modules.module.kind import ModuleKind
from pda.specification.modules.module.module import Module
from pda.specification.modules.module.namespace import NamespacePortion
from pda.specification.modules.module.unavailable import UnavailableModule
from pda.tools.paths import is_file


class CategorizedModule(NamedTuple):
    module: Union[Module, UnavailableModule]
    category: ModuleCategory

    @property
    def name(self) -> str:
        return self.module.name

    @property
    def module_name(self) -> str:
        return self.module.module_name

    @property
    def qualified_name(self) -> str:
        return self.module.qualified_name

    @property
    def origin(self) -> Optional[Path]:
        return self.module.origin if isinstance(self.module, Module) else None

    @property
    def origin_type(self) -> OriginType:
        return self.module.origin_type if isinstance(self.module, Module) else OriginType.NONE

    @property
    def submodule_search_locations(self) -> Optional[Tuple[Path, ...]]:
        return self.module.submodule_search_locations if isinstance(self.module, Module) else None

    @property
    def namespace_portions(self) -> Tuple[NamespacePortion, ...]:
        return self.module.namespace_portions if isinstance(self.module, Module) else ()

    @property
    def base_path(self) -> Optional[Path]:
        return self.module.base_path if isinstance(self.module, Module) else None

    def prefix(self, level: int) -> str:
        return self.module.prefix(level)

    @property
    def top_level_module(self) -> str:
        return self.module.top_level_module

    @property
    def is_top_level(self) -> bool:
        return self.module.is_top_level

    @property
    def is_private(self) -> bool:
        return self.module.is_private

    @property
    def is_module(self) -> bool:
        return self.module.is_module if isinstance(self.module, Module) else False

    @property
    def is_package(self) -> bool:
        return self.module.is_package if isinstance(self.module, Module) else False

    @property
    def is_namespace_package(self) -> bool:
        return self.module.is_namespace_package if isinstance(self.module, Module) else False

    @property
    def kind(self) -> ModuleKind:
        return self.module.kind if isinstance(self.module, Module) else ModuleKind.UNKNOWN

    @property
    def available(self) -> bool:
        if isinstance(self.module, UnavailableModule):
            return False

        if self.origin_type == OriginType.PYTHON:
            return self.origin is not None and is_file(self.origin)

        return True

    @property
    def diagnostic(self) -> Optional[ResolutionDiagnostic]:
        return self.module.diagnostic if isinstance(self.module, UnavailableModule) else None

    @property
    def availability_reason(self) -> Optional[str]:
        if isinstance(self.module, UnavailableModule):
            return self.module.diagnostic.message if self.module.diagnostic is not None else "module not found"

        if not self.available:
            return "source not available for analysis"

        return None

    @staticmethod
    def from_module(
        module: Union[Module, UnavailableModule],
        *,
        category: ModuleCategory,
    ) -> CategorizedModule:
        return CategorizedModule(module=module, category=category)
