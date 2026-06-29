import sys
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple, Union

import pytest

from pda.analyzer import ModuleImportsAnalyzer
from pda.config import ModuleImportsAnalyzerConfig, ModuleScanConfig
from pda.specification import ModuleCategory, clear_module_spec_cache
from pda.types import Pathlike

PKG = "pdamultiroot"


@pytest.fixture
def project(tmp_path: Path) -> Tuple[Path, Path]:
    pkg = tmp_path / PKG
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text(
        f"import json\nimport {PKG}.b\nimport {PKG}.shared\n\nif __name__ == '__main__':\n    import csv\n"
    )
    (pkg / "b.py").write_text(f"import json\nimport {PKG}.shared\n\nif __name__ == '__main__':\n    import gzip\n")
    (pkg / "shared.py").write_text("import json\n")

    sub = pkg / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "c.py").write_text(f"import {PKG}.shared\n")

    clear_module_spec_cache()
    try:
        yield tmp_path, pkg
    finally:
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
        for module in list(sys.modules):
            if module == PKG or module.startswith(f"{PKG}."):
                del sys.modules[module]
        clear_module_spec_cache()


def _analyze(
    project_root: Path,
    paths: Union[Pathlike, Iterable[Pathlike]],
    source_roots: Optional[Tuple[Pathlike, ...]] = None,
    **scan_kwargs: object,
) -> ModuleImportsAnalyzer:
    config = (
        ModuleImportsAnalyzerConfig(module_scan=ModuleScanConfig(**scan_kwargs))
        if scan_kwargs
        else ModuleImportsAnalyzerConfig()
    )
    analyzer = ModuleImportsAnalyzer(config, project_root=project_root, package=PKG, source_roots=source_roots)
    analyzer(paths)
    return analyzer


def _names(analyzer: ModuleImportsAnalyzer, category: Optional[ModuleCategory] = None) -> Set[str]:
    return {
        node.module.qualified_name for node in analyzer.graph if category is None or node.module.category == category
    }


class TestMultiRoot:
    def test_two_roots_share_a_dependency(self, project: Tuple[Path, Path]) -> None:
        root, pkg = project
        analyzer = _analyze(root, [pkg / "a.py", pkg / "b.py"])

        local = _names(analyzer, ModuleCategory.LOCAL)
        assert {f"{PKG}.a", f"{PKG}.b", f"{PKG}.shared"} <= local
        assert analyzer.filepaths == sorted([pkg / "a.py", pkg / "b.py"])

    def test_directory_input_makes_every_file_a_root(self, project: Tuple[Path, Path]) -> None:
        root, pkg = project
        analyzer = _analyze(root, pkg)

        assert len(analyzer.filepaths) == 6
        local = _names(analyzer, ModuleCategory.LOCAL)
        assert {f"{PKG}.a", f"{PKG}.b", f"{PKG}.shared", f"{PKG}.sub", f"{PKG}.sub.c"} <= local

    def test_mixed_files_and_directories(self, project: Tuple[Path, Path]) -> None:
        root, pkg = project
        analyzer = _analyze(root, [pkg / "a.py", pkg / "sub"])

        assert pkg / "a.py" in analyzer.filepaths
        assert pkg / "sub" / "c.py" in analyzer.filepaths

    def test_overlapping_inputs_do_not_duplicate_roots(self, project: Tuple[Path, Path]) -> None:
        root, pkg = project
        analyzer = _analyze(root, [pkg, pkg / "a.py"])

        assert len(analyzer.filepaths) == len(set(analyzer.filepaths)) == 6

    def test_main_guard_only_followed_for_root_inputs(self, project: Tuple[Path, Path]) -> None:
        root, pkg = project

        single = _names(_analyze(root, pkg / "a.py"), ModuleCategory.STDLIB)
        assert "csv" in single  # a.py is the root, its __main__ guard is followed
        assert "gzip" not in single  # b.py is reached as a dependency, its __main__ guard is not

        both = _names(_analyze(root, [pkg / "a.py", pkg / "b.py"]), ModuleCategory.STDLIB)
        assert "csv" in both
        assert "gzip" in both  # b.py is now a root too, so its __main__ guard is followed

    def test_single_path_backward_compatible(self, project: Tuple[Path, Path]) -> None:
        root, pkg = project
        analyzer = _analyze(root, pkg / "a.py")

        assert analyzer.filepaths == [pkg / "a.py"]
        assert f"{PKG}.shared" in _names(analyzer, ModuleCategory.LOCAL)

    def test_explicit_source_root_controls_module_fqns(self, tmp_path: Path) -> None:
        project_root = tmp_path / "repo"
        source_root = project_root / "src"
        package = source_root / PKG
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
        (package / "a.py").write_text(f"import {PKG}.b\n")
        (package / "b.py").write_text("")

        analyzer = _analyze(project_root, package / "a.py", source_roots=(Path("src"),))

        local = _names(analyzer, ModuleCategory.LOCAL)
        assert {f"{PKG}.a", f"{PKG}.b"} <= local
        assert all(not name.startswith("src.") for name in local)

    def test_caching_and_refresh(self, project: Tuple[Path, Path]) -> None:
        root, pkg = project
        config = ModuleImportsAnalyzerConfig()
        analyzer = ModuleImportsAnalyzer(config, project_root=root, package=PKG)

        first = analyzer([pkg / "a.py", pkg / "b.py"])
        cached = analyzer([pkg / "a.py", pkg / "b.py"])
        refreshed = analyzer([pkg / "a.py", pkg / "b.py"], refresh=True)

        assert len(cached) == len(first)
        assert len(refreshed) == len(first)
        assert analyzer.filepaths == sorted([pkg / "a.py", pkg / "b.py"])

    def test_no_inputs_raises(self, project: Tuple[Path, Path]) -> None:
        root, _ = project
        analyzer = ModuleImportsAnalyzer(ModuleImportsAnalyzerConfig(), project_root=root, package=PKG)

        with pytest.raises(ValueError):
            analyzer()
