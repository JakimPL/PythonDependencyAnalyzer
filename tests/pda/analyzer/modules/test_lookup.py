from __future__ import annotations

from typing import Optional, cast

from pda.analyzer.modules.lookup import RuntimeModuleLookup
from pda.resolution import ModuleResolution, ModuleResolutionService, TargetEnvironment
from pda.specification import CategorizedModule, ModuleCategory


class SpyRuntimeResolver:
    def __init__(self) -> None:
        self._resolver = ModuleResolutionService(TargetEnvironment.runtime())
        self.calls: list[tuple[str, Optional[str]]] = []

    def resolve_name(
        self,
        name: str,
        *,
        containing_package: Optional[str] = None,
    ) -> ModuleResolution:
        self.calls.append((name, containing_package))
        return self._resolver.resolve_name(name, containing_package=containing_package)

    def to_categorized_module(self, resolution: ModuleResolution) -> CategorizedModule:
        return self._resolver.to_categorized_module(resolution)


def test_runtime_lookup_resolves_through_runtime_environment() -> None:
    resolver = SpyRuntimeResolver()
    lookup = RuntimeModuleLookup(resolver=cast(ModuleResolutionService, resolver))

    module = lookup.discovered_module("sys", containing_package=None)

    assert module.name == "sys"
    assert module.category == ModuleCategory.STDLIB
    assert resolver.calls == [("sys", None)]


def test_runtime_lookup_category_resolves_through_runtime_environment() -> None:
    resolver = SpyRuntimeResolver()
    lookup = RuntimeModuleLookup(resolver=cast(ModuleResolutionService, resolver))
    module = lookup.discovered_module("sys", containing_package=None)

    category = lookup.category(module)

    assert category == ModuleCategory.STDLIB
    assert resolver.calls == [("sys", None), ("sys", None)]
