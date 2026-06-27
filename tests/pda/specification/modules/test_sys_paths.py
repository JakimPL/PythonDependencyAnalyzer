from __future__ import annotations

from pathlib import Path

from pda.specification import SysPaths


def test_resolve_returns_none_when_origin_under_no_candidate() -> None:
    origin = Path("/nonexistent/uv-cache/archive/lib/python3.13/site-packages/yaml/__init__.py")
    base_path = Path("/nonexistent/project/src")

    assert SysPaths.resolve(origin, base_path=base_path) is None


def test_resolve_import_path_returns_none_when_origin_under_no_candidate() -> None:
    origin = Path("/nonexistent/elsewhere/pkg/module.py")
    base_path = Path("/nonexistent/project/src")

    assert SysPaths.resolve_import_path(origin, base_path) is None


def test_resolve_import_path_resolves_origin_under_base_path() -> None:
    base_path = Path("/nonexistent/project/src")
    origin = base_path / "pkg" / "module.py"

    result = SysPaths.resolve_import_path(origin, base_path)

    assert result is not None
    assert result.module == "pkg.module"
