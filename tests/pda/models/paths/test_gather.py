from pathlib import Path
from typing import Set

import pytest

from pda.models import gather_python_files


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.txt").write_text("")

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "c.py").write_text("")

    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "d.py").write_text("")

    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "x.py").write_text("")

    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "e.py").write_text("")

    return tmp_path


def _names(tree: Path, files: Set[Path]) -> Set[str]:
    return {str(path.relative_to(tree)) for path in files}


class TestGatherPythonFiles:
    def test_single_file(self, tree: Path) -> None:
        assert gather_python_files(tree / "a.py") == [tree / "a.py"]

    def test_single_non_python_file_is_dropped(self, tree: Path) -> None:
        assert gather_python_files(tree / "b.txt") == []

    def test_directory_is_walked_recursively(self, tree: Path) -> None:
        result = gather_python_files(tree)

        assert _names(tree, set(result)) == {
            "a.py",
            "pkg/__init__.py",
            "pkg/c.py",
            "pkg/sub/__init__.py",
            "pkg/sub/d.py",
        }

    def test_excludes_pycache_hidden_and_non_python(self, tree: Path) -> None:
        names = _names(tree, set(gather_python_files(tree)))

        assert "b.txt" not in names
        assert not any("__pycache__" in name for name in names)
        assert not any(".hidden" in name for name in names)

    def test_mixed_files_and_directories(self, tree: Path) -> None:
        result = gather_python_files([tree / "a.py", tree / "pkg" / "sub"])

        assert _names(tree, set(result)) == {"a.py", "pkg/sub/__init__.py", "pkg/sub/d.py"}

    def test_overlapping_inputs_are_deduplicated(self, tree: Path) -> None:
        result = gather_python_files([tree / "pkg", tree / "pkg" / "c.py"])

        assert len(result) == len(set(result))
        assert (tree / "pkg" / "c.py") in result
        assert _names(tree, set(result)) == {
            "pkg/__init__.py",
            "pkg/c.py",
            "pkg/sub/__init__.py",
            "pkg/sub/d.py",
        }

    def test_result_is_sorted(self, tree: Path) -> None:
        result = gather_python_files(tree)

        assert result == sorted(result)
