import importlib
import sys
from pathlib import Path
from typing import Set

import pytest

from pda.analyzer import ModulesCollector
from pda.config import ModuleScanConfig, ModulesCollectorConfig
from pda.specification import ModuleCategory, clear_module_spec_cache

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


def _collect(project_root: Path, package: str = PKG, **config_kwargs: object) -> ModulesCollector:
    # stdlib_depth/external_depth = 0 keeps the collector to local modules only (fast).
    module_scan = ModuleScanConfig(
        stdlib_depth=0,
        external_depth=0,
        hide_private=False,
        hide_unavailable=False,
    )
    config = ModulesCollectorConfig(module_scan=module_scan, **config_kwargs)
    collector = ModulesCollector(config, project_root=project_root, package=package)
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

    def test_project_root_takes_precedence_over_loaded_shadow_module(self, tmp_path: Path) -> None:
        module_name = "loaded_shadowed_pkg"
        external_root = tmp_path / "external"
        external_package = external_root / module_name
        external_package.mkdir(parents=True)
        (external_package / "__init__.py").write_text("")

        project_root = tmp_path / "project"
        project_package = project_root / module_name
        project_package.mkdir(parents=True)
        (project_package / "__init__.py").write_text("")

        sys.path.insert(0, str(external_root))
        clear_module_spec_cache()
        try:
            loaded = importlib.import_module(module_name)
            assert loaded.__spec__.origin == str(external_package / "__init__.py")

            collector = _collect(project_root, package=module_name)

            module = collector.modules[module_name]
            assert module.category == ModuleCategory.LOCAL
            assert module.origin == project_package / "__init__.py"
        finally:
            while str(external_root) in sys.path:
                sys.path.remove(str(external_root))
            for module in list(sys.modules):
                if module == module_name or module.startswith(f"{module_name}."):
                    del sys.modules[module]
            clear_module_spec_cache()

    def test_collects_local_namespace_package_portion(self, tmp_path: Path) -> None:
        project_root = tmp_path / "project"
        namespace = project_root / "namespace_pkg"
        namespace.mkdir(parents=True)
        (namespace / "leaf.py").write_text("")

        collector = _collect(project_root, package="namespace_pkg")

        module = collector.modules["namespace_pkg"]
        assert module.category == ModuleCategory.LOCAL
        assert module.is_namespace_package is True
        assert module.origin is None
        assert module.submodule_search_locations == (namespace,)
        assert "namespace_pkg.leaf" in collector.modules


class TestCollectorCollapse:
    def test_collapse_level_zero_merges_to_top_level(self, project: Path) -> None:
        assert _labels(_collect(project, collapse_level=0)) == {PKG}

    def test_collapse_level_one_keeps_second_order(self, project: Path) -> None:
        labels = _labels(_collect(project, collapse_level=1, qualified_names=True))

        # pdadepthcollector.sub.c and .sub.d merge into 'pdadepthcollector.sub'.
        assert f"{PKG}.sub" in labels
        assert f"{PKG}.a" in labels
        assert f"{PKG}.sub.c" not in labels
