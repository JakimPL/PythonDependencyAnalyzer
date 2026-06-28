from __future__ import annotations

import pytest

from pda.config import ValidationOptions
from pda.specification import CategorizedModule, ModuleCategory

_LENIENT = ValidationOptions(allow_missing_spec=True, validate_origin=True, expect_python=False, raise_error=False)


def test_real_python_module_is_available_with_category() -> None:
    result = CategorizedModule.create("pathlib")

    assert result.category == ModuleCategory.STDLIB
    assert result.available is True
    assert result.availability_reason is None


def test_builtin_module_is_available() -> None:
    result = CategorizedModule.create("sys", validation_options=_LENIENT)

    assert result.category == ModuleCategory.STDLIB
    assert result.available is True


def test_missing_module_is_unknown_and_unavailable() -> None:
    result = CategorizedModule.create("definitely_not_a_real_module_xyz", validation_options=_LENIENT)

    assert result.category == ModuleCategory.UNKNOWN
    assert result.available is False
    assert result.availability_reason


def test_python_module_with_unreadable_source_keeps_category_but_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pda.specification.modules.module.categorized as categorized_mod

    monkeypatch.setattr(categorized_mod, "is_file", lambda _path: False)

    result = CategorizedModule.create("pathlib")

    assert result.category == ModuleCategory.STDLIB
    assert result.available is False
    assert result.availability_reason == "source not available for analysis"
