from __future__ import annotations

from pathlib import Path

import pytest

from pda.specification import CategorizedModule, Module, ModuleCategory, UnavailableModule
from pda.specification.imports.origin import OriginType


def test_from_module_uses_explicit_category() -> None:
    module = Module(
        name="pkg.module",
        origin=Path(__file__),
        origin_type=OriginType.PYTHON,
    )

    result = CategorizedModule.from_module(module, category=ModuleCategory.LOCAL)

    assert result.name == "pkg.module"
    assert result.category == ModuleCategory.LOCAL
    assert result.available is True
    assert result.availability_reason is None


def test_unavailable_module_is_unknown_and_unavailable() -> None:
    result = CategorizedModule.from_module(
        UnavailableModule(name="definitely_not_a_real_module_xyz", error=Exception("missing")),
        category=ModuleCategory.UNKNOWN,
    )

    assert result.category == ModuleCategory.UNKNOWN
    assert result.available is False
    assert result.availability_reason == "missing"


def test_python_module_with_unreadable_source_keeps_category_but_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pda.specification.modules.module.categorized as categorized_mod

    monkeypatch.setattr(categorized_mod, "is_file", lambda _path: False)
    module = Module(
        name="pkg.module",
        origin=Path(__file__),
        origin_type=OriginType.PYTHON,
    )

    result = CategorizedModule.from_module(module, category=ModuleCategory.LOCAL)

    assert result.category == ModuleCategory.LOCAL
    assert result.available is False
    assert result.availability_reason == "source not available for analysis"


def test_from_module_requires_explicit_category() -> None:
    module = Module(
        name="pkg.module",
        origin=Path(__file__),
        origin_type=OriginType.PYTHON,
    )

    with pytest.raises(TypeError):
        CategorizedModule.from_module(module)  # type: ignore[call-arg]
