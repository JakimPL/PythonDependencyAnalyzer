import sys
from pathlib import Path
from typing import Set

import pytest

from pda.analyzer import ModulesCollector
from pda.config import ModuleScanConfig, ModulesCollectorConfig
from pda.specification import clear_module_spec_cache

PKG = "pdadepthcollector"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    pkg_dir = tmp_path / PKG
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "a.py").write_text("")
    sub = pkg_dir / "sub"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "c.py").write_text("")
    (sub / "d.py").write_text("")

    clear_module_spec_cache()
    try:
        yield tmp_path
    finally:
        if str(tmp_path) in sys.path:
            sys.path.remove(str(tmp_path))
        for module in list(sys.modules):
            if module == PKG or module.startswith(f"{PKG}."):
                del sys.modules[module]
        clear_module_spec_cache()


def _collect(project_root: Path, **config_kwargs: object) -> ModulesCollector:
    # stdlib_depth/external_depth = 0 keeps the collector to local modules only (fast).
    module_scan = ModuleScanConfig(
        stdlib_depth=0,
        external_depth=0,
        hide_private=False,
        hide_unavailable=False,
    )
    config = ModulesCollectorConfig(module_scan=module_scan, **config_kwargs)
    collector = ModulesCollector(config, project_root=project_root, package=PKG)
    collector()
    return collector


def _qualified_names(collector: ModulesCollector) -> Set[str]:
    return {node.module.qualified_name for node in collector.graph}


def _labels(collector: ModulesCollector) -> Set[str]:
    return {node.label for node in collector.graph}


class TestCollectorMaxDepth:
    def test_unlimited_collects_full_tree(self, project: Path) -> None:
        names = _qualified_names(_collect(project))

        assert {PKG, f"{PKG}.a", f"{PKG}.sub", f"{PKG}.sub.c", f"{PKG}.sub.d"} <= names

    def test_max_depth_bounds_recursion(self, project: Path) -> None:
        names = _qualified_names(_collect(project, max_depth=1))

        assert f"{PKG}.sub" in names
        assert f"{PKG}.sub.c" not in names
        assert f"{PKG}.sub.d" not in names


class TestCollectorCollapse:
    def test_collapse_level_zero_merges_to_top_level(self, project: Path) -> None:
        assert _labels(_collect(project, collapse_level=0)) == {PKG}

    def test_collapse_level_one_keeps_second_order(self, project: Path) -> None:
        labels = _labels(_collect(project, collapse_level=1, qualified_names=True))

        # pdadepthcollector.sub.c and .sub.d merge into 'pdadepthcollector.sub'.
        assert f"{PKG}.sub" in labels
        assert f"{PKG}.a" in labels
        assert f"{PKG}.sub.c" not in labels
