from __future__ import annotations

from pathlib import Path

from pda.specification import ModuleSource


def test_module_source_is_filesystem_context_without_resolution_methods(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    origin = package / "module.py"
    origin.write_text("")

    source = ModuleSource(origin=origin, base_path=tmp_path, package="pkg")

    assert source.relative.module == "pkg.module"
    assert source.top_level == "pkg"
    assert not hasattr(source, "module")
    assert not hasattr(source, "get_spec")
    assert not hasattr(source, "get_package_spec")
