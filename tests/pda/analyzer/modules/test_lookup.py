from __future__ import annotations

from typing import Optional, cast

from pda.analyzer.modules.lookup import RuntimeModuleLookup
from pda.resolution import ModuleResolution, ModuleResolutionService, TargetEnvironment
from pda.specification import CategorizedModule, ModuleCategory


class SpyRuntimeResolver:
    def __init__(self) -> None:
        self._resolver = ModuleResolutionService(TargetEnvironment.runtime())
        self.runtime_calls: list[tuple[str, Optional[str]]] = []
        self.project_calls: list[tuple[str, Optional[str]]] = []

    def resolve_runtime_name(
        self,
        name: str,
        *,
        containing_package: Optional[str] = None,
    ) -> ModuleResolution:
        self.runtime_calls.append((name, containing_package))
        return self._resolver.resolve_runtime_name(name, containing_package=containing_package)

    def resolve_project_name(
        self,
        name: str,
        *,
        containing_package: Optional[str] = None,
    ) -> ModuleResolution:
        self.project_calls.append((name, containing_package))
        raise AssertionError("RuntimeModuleLookup must not resolve discovered modules through project mode")

    def to_categorized_module(self, resolution: ModuleResolution) -> CategorizedModule:
        return self._resolver.to_categorized_module(resolution)


def test_runtime_lookup_uses_runtime_resolution_mode() -> None:
    resolver = SpyRuntimeResolver()
    lookup = RuntimeModuleLookup(resolver=cast(ModuleResolutionService, resolver))

    module = lookup.discovered_module("sys", containing_package=None)

    assert module.name == "sys"
    assert resolver.runtime_calls == [("sys", None)]
    assert resolver.project_calls == []


def test_runtime_lookup_category_uses_runtime_resolution_mode() -> None:
    resolver = SpyRuntimeResolver()
    lookup = RuntimeModuleLookup(resolver=cast(ModuleResolutionService, resolver))
    module = lookup.discovered_module("sys", containing_package=None)

    category = lookup.category(module)

    assert category == ModuleCategory.STDLIB
    assert resolver.runtime_calls == [("sys", None), ("sys", None)]
    assert resolver.project_calls == []
