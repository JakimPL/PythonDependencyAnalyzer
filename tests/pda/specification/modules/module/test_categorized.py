from __future__ import annotations

from pathlib import Path

import pytest

from pda.specification import (
    CategorizedModule,
    Module,
    ModuleCategory,
    ModuleKind,
    ResolutionDiagnostic,
    ResolutionDiagnosticCode,
    UnavailableModule,
)
from pda.specification.imports.origin import OriginType


def test_from_module_uses_explicit_category() -> None:
    module = Module(
        name="pkg.module",
        kind=ModuleKind.SOURCE_MODULE,
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
        UnavailableModule(
            name="definitely_not_a_real_module_xyz",
            diagnostic=ResolutionDiagnostic.create(ResolutionDiagnosticCode.MODULE_SPEC_NOT_FOUND, "missing"),
        ),
        category=ModuleCategory.UNKNOWN,
    )

    assert result.category == ModuleCategory.UNKNOWN
    assert result.available is False
    assert result.availability_reason == "missing"
    assert result.diagnostic is not None
    assert result.diagnostic.code == ResolutionDiagnosticCode.MODULE_SPEC_NOT_FOUND


def test_python_module_with_unreadable_source_keeps_category_but_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pda.specification.modules.module.categorized as categorized_mod

    monkeypatch.setattr(categorized_mod, "is_file", lambda _path: False)
    module = Module(
        name="pkg.module",
        kind=ModuleKind.SOURCE_MODULE,
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
        kind=ModuleKind.SOURCE_MODULE,
        origin=Path(__file__),
        origin_type=OriginType.PYTHON,
    )

    with pytest.raises(TypeError):
        CategorizedModule.from_module(module)  # type: ignore[call-arg]


def test_categorized_module_rejects_unknown_attribute() -> None:
    module = Module(
        name="pkg.module",
        kind=ModuleKind.SOURCE_MODULE,
        origin=Path(__file__),
        origin_type=OriginType.PYTHON,
    )
    categorized = CategorizedModule.from_module(module, category=ModuleCategory.LOCAL)

    with pytest.raises(AttributeError):
        _ = categorized.does_not_exist
