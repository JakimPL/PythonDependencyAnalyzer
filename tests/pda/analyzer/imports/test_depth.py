import importlib
import sys
from pathlib import Path
from typing import Set, Tuple

import pytest

from pda.analyzer import ModuleImportsAnalyzer
from pda.config import ModuleImportsAnalyzerConfig, ModuleScanConfig
from pda.specification import ModuleCategory

PKG = "pdadepthimports"


@pytest.fixture
def project(tmp_path: Path) -> Tuple[Path, Path]:
    pkg_dir = tmp_path / PKG
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "a.py").write_text(f"import json\nimport {PKG}.b\n")
    (pkg_dir / "b.py").write_text("import json\n")

    importlib.invalidate_caches()
    try:
        yield tmp_path, pkg_dir / "a.py"
    finally:
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
        for module in list(sys.modules):
            if module == PKG or module.startswith(f"{PKG}."):
                del sys.modules[module]
        importlib.invalidate_caches()


def _analyze(project_root: Path, filepath: Path, **scan_kwargs: object) -> ModuleImportsAnalyzer:
    config = ModuleImportsAnalyzerConfig(module_scan=ModuleScanConfig(**scan_kwargs))
    analyzer = ModuleImportsAnalyzer(config, project_root=project_root, root_module_name=PKG)
    analyzer(filepath)
    return analyzer


def _names(analyzer: ModuleImportsAnalyzer, category: ModuleCategory) -> Set[str]:
    return {node.module.qualified_name for node in analyzer.graph if node.module.category == category}


class TestExternalEnvironmentSearch:
    def test_external_depth_uses_active_sys_path_when_enabled(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_root = tmp_path / "project"
        package = project_root / "app_pkg"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
        (package / "main.py").write_text("import ambient_dep\n")

        external_root = tmp_path / "site-packages"
        external_package = external_root / "ambient_dep"
        external_package.mkdir(parents=True)
        (external_package / "__init__.py").write_text("")
        monkeypatch.syspath_prepend(str(external_root))
        importlib.invalidate_caches()

        config = ModuleImportsAnalyzerConfig(module_scan=ModuleScanConfig(stdlib_depth=0, external_depth=1))
        analyzer = ModuleImportsAnalyzer(
            config,
            project_root=project_root,
            root_module_name="app_pkg",
            include_sys_path=True,
        )
        analyzer(package / "main.py")

        assert "ambient_dep" in _names(analyzer, ModuleCategory.EXTERNAL)

    def test_external_depth_does_not_use_sys_path_when_disabled(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        project_root = tmp_path / "project"
        package = project_root / "strict_app_pkg"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
        (package / "main.py").write_text("import strict_ambient_dep\n")

        external_root = tmp_path / "site-packages"
        external_package = external_root / "strict_ambient_dep"
        external_package.mkdir(parents=True)
        (external_package / "__init__.py").write_text("")
        monkeypatch.syspath_prepend(str(external_root))
        importlib.invalidate_caches()

        config = ModuleImportsAnalyzerConfig(
            module_scan=ModuleScanConfig(stdlib_depth=0, external_depth=1, hide_unavailable=False)
        )
        analyzer = ModuleImportsAnalyzer(
            config,
            project_root=project_root,
            root_module_name="strict_app_pkg",
            include_sys_path=False,
        )
        analyzer(package / "main.py")

        assert "strict_ambient_dep" not in _names(analyzer, ModuleCategory.EXTERNAL)
        assert "strict_ambient_dep" in _names(analyzer, ModuleCategory.UNKNOWN)


class TestStdlibDepth:
    def test_depth_zero_hides_stdlib(self, project: Tuple[Path, Path]) -> None:
        root, filepath = project
        analyzer = _analyze(root, filepath, stdlib_depth=0, external_depth=0)

        assert _names(analyzer, ModuleCategory.STDLIB) == set()
        assert {f"{PKG}.a", f"{PKG}.b"} <= _names(analyzer, ModuleCategory.LOCAL)

    def test_depth_one_shows_boundary_only(self, project: Tuple[Path, Path]) -> None:
        root, filepath = project
        analyzer = _analyze(root, filepath, stdlib_depth=1, external_depth=0)

        # 'json' appears as a boundary node; none of its own submodules are followed.
        assert _names(analyzer, ModuleCategory.STDLIB) == {"json"}

    def test_depth_two_follows_one_level_in(self, project: Tuple[Path, Path]) -> None:
        root, filepath = project
        analyzer = _analyze(root, filepath, stdlib_depth=2, external_depth=0)

        stdlib = _names(analyzer, ModuleCategory.STDLIB)
        assert "json" in stdlib
        # json's own imports are now followed one level deep.
        assert len(stdlib) > 1
