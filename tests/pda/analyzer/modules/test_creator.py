from __future__ import annotations

from pathlib import Path

from pda.analyzer.modules.creator import ModuleCreator
from pda.specification import ModuleCategory


def test_create_module_returns_available_module_for_runtime_module_without_project_root() -> None:
    creator = ModuleCreator()

    result = creator.create_module("pathlib")

    assert result.name == "pathlib"
    assert result.category == ModuleCategory.STDLIB
    assert result.available is True


def test_create_module_uses_project_resolution_when_project_root_is_available(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("")

    creator = ModuleCreator(project_root=tmp_path)
    result = creator.create_module("pkg")

    assert result.name == "pkg"
    assert result.category == ModuleCategory.LOCAL
    assert result.origin == package / "__init__.py"


def test_create_module_marks_missing_module_unknown_and_unavailable() -> None:
    creator = ModuleCreator()
    result = creator.create_module("definitely_not_a_real_module_xyz")

    assert result.name == "definitely_not_a_real_module_xyz"
    assert result.category == ModuleCategory.UNKNOWN
    assert result.available is False
