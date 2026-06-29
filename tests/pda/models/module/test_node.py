from __future__ import annotations

from pda.analyzer.modules.creator import ModuleCreator
from pda.models import ModuleNode


def test_available_module_node_omits_availability_flag() -> None:
    module = ModuleCreator().create_module("pathlib")

    data = ModuleNode(module).serialize()

    assert data["category"] == "stdlib"
    assert "available" not in data


def test_unavailable_module_node_serializes_availability() -> None:
    module = ModuleCreator().create_module("definitely_not_a_real_module_xyz")

    node = ModuleNode(module)
    data = node.serialize()

    assert node.available is False
    assert data["category"] == "unknown"
    assert data["available"] is False
