from __future__ import annotations

import pytest

from pda.analyzer.modules.creator import ModuleCreator
from pda.exceptions import PDAPathResolutionError
from pda.models import ModuleNode
from pda.specification.modules.module.module import Module


def test_available_module_node_omits_availability_flag() -> None:
    module = ModuleCreator().create_module("pathlib")

    data = ModuleNode(module).serialize()

    assert data["category"] == "stdlib"
    assert "available" not in data


def test_unavailable_module_node_serializes_availability(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_self: Module) -> None:
        raise PDAPathResolutionError("simulated base path failure")

    monkeypatch.setattr(Module, "base_path", property(_raise))
    module = ModuleCreator().create_module("pathlib")

    node = ModuleNode(module)
    data = node.serialize()

    assert node.available is False
    assert data["category"] == "unknown"
    assert data["available"] is False
