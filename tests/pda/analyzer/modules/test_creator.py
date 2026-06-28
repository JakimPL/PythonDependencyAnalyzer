from __future__ import annotations

import pytest

from pda.analyzer.modules.creator import ModuleCreator
from pda.exceptions import PDAPathResolutionError
from pda.specification import ModuleCategory
from pda.specification.modules.module.module import Module


def test_create_module_returns_available_module_for_real_module() -> None:
    creator = ModuleCreator()

    result = creator.create_module("pathlib")

    assert result.name == "pathlib"
    assert result.category == ModuleCategory.STDLIB
    assert result.available is True


def test_create_module_marks_unknown_and_unavailable_when_base_path_unresolvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(_self: Module) -> None:
        raise PDAPathResolutionError("simulated base path failure")

    monkeypatch.setattr(Module, "base_path", property(_raise))

    creator = ModuleCreator()
    result = creator.create_module("pathlib")

    assert result.name == "pathlib"
    assert result.category == ModuleCategory.UNKNOWN
    assert result.available is False
