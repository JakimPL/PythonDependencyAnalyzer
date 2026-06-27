from pathlib import Path

from wasm import pyodide_candidates


def test_normalizes_leading_double_slash() -> None:
    candidates = {"purelib": Path("//lib/python3.14/site-packages"), "stdlib": Path("//lib/python3.14")}

    resolved = pyodide_candidates(candidates, "/lib/python314.zip/ast.py")

    assert resolved["purelib"] == Path("/lib/python3.14/site-packages")
    assert resolved["stdlib"] == Path("/lib/python3.14")


def test_adds_stdlib_archive_from_origin() -> None:
    resolved = pyodide_candidates({}, "/lib/python314.zip/ast.py")

    assert resolved["stdlib_archive"] == Path("/lib/python314.zip")


def test_leaves_single_slash_paths_unchanged() -> None:
    candidates = {"purelib": Path("/usr/lib/python3.13/site-packages")}

    resolved = pyodide_candidates(candidates, "/usr/lib/python3.13/ast.py")

    assert resolved["purelib"] == Path("/usr/lib/python3.13/site-packages")


def test_does_not_override_existing_stdlib_archive() -> None:
    candidates = {"stdlib_archive": Path("/custom/archive")}

    resolved = pyodide_candidates(candidates, "/lib/python314.zip/ast.py")

    assert resolved["stdlib_archive"] == Path("/custom/archive")
