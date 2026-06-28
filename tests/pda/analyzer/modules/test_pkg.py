from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pda.analyzer.modules.pkg import PkgModuleScanner


def test_finder_base_path_file_finder() -> None:
    finder = SimpleNamespace(path="/usr/lib/python3.13")

    assert PkgModuleScanner._finder_base_path(finder) == Path("/usr/lib/python3.13")


def test_finder_base_path_zipimporter_with_prefix() -> None:
    finder = SimpleNamespace(archive="/lib/python314.zip", prefix="pkg/")

    assert PkgModuleScanner._finder_base_path(finder) == Path("/lib/python314.zip/pkg")


def test_finder_base_path_zipimporter_without_prefix() -> None:
    finder = SimpleNamespace(archive="/lib/python314.zip", prefix="")

    assert PkgModuleScanner._finder_base_path(finder) == Path("/lib/python314.zip")


def test_finder_base_path_unknown_finder_returns_none() -> None:
    finder = SimpleNamespace()

    assert PkgModuleScanner._finder_base_path(finder) is None
