from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Iterator, Tuple

import pytest

from pda.analyzer.imports.resolver import ImportResolver
from pda.config import ModuleImportsAnalyzerConfig
from pda.models import ModuleNode
from pda.resolution import ProjectResolutionContext
from pda.specification import ImportPath, ModuleCategory, ModuleSource, clear_module_spec_cache
from pda.specification.modules.module.unavailable import UnavailableModule

PKG = "pdaresolvercase"


@pytest.fixture
def project(tmp_path: Path) -> Iterator[Tuple[Path, Path]]:
    source_root = tmp_path / "src"
    package = source_root / PKG
    subpackage = package / "sub"
    namespace = source_root / "plugins"

    subpackage.mkdir(parents=True)
    namespace.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "app.py").write_text("")
    (package / "shared.py").write_text("")
    (subpackage / "__init__.py").write_text("")
    (subpackage / "module.py").write_text("")
    (namespace / "leaf.py").write_text("")

    clear_module_spec_cache()
    try:
        yield source_root, package
    finally:
        for module in list(sys.modules):
            if module == PKG or module.startswith(f"{PKG}.") or module == "plugins" or module.startswith("plugins."):
                del sys.modules[module]
        clear_module_spec_cache()
        importlib.invalidate_caches()


def _resolver(
    source_root: Path,
    *,
    qualified_names: bool = False,
    package: str = PKG,
) -> ImportResolver:
    config = ModuleImportsAnalyzerConfig(qualified_names=qualified_names)
    context = ProjectResolutionContext.create(source_root)
    return ImportResolver(project_context=context, package=package, config=config)


def _source(
    resolver: ImportResolver,
    source_root: Path,
    origin: Path,
    *,
    package: str = PKG,
) -> ModuleSource:
    return ModuleSource(
        origin=origin,
        base_path=source_root,
        package=package,
    )


class TestImportResolverInit:
    def test_project_root_is_resolved(self, tmp_path: Path) -> None:
        resolver = _resolver(tmp_path)

        assert resolver._project_root == tmp_path.resolve()


class TestCreateRoot:
    def test_create_root_uses_filesystem_identity(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)

        root = resolver.create_root(package / "app.py")

        assert isinstance(root, ModuleNode)
        assert root.module.name == f"{PKG}.app"
        assert root.module.category == ModuleCategory.LOCAL
        assert root.module.origin == package / "app.py"
        assert root.label == "app"

    def test_create_root_can_label_with_qualified_names(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root, qualified_names=True)

        root = resolver.create_root(package / "app.py")

        assert root.label == f"{PKG}.app"


class TestResolveImportPath:
    def test_absolute_local_import_resolves_to_fqn(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")

        result = resolver.resolve_import_path(source, ImportPath(module=f"{PKG}.shared"))

        assert result == ImportPath(module=f"{PKG}.shared")

    def test_relative_from_import_name_prefers_local_submodule(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")

        result = resolver.resolve_import_path(source, ImportPath(module=None, level=1, name="shared"))

        assert result == ImportPath(module=f"{PKG}.shared")

    def test_relative_from_import_object_falls_back_to_containing_package(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")

        result = resolver.resolve_import_path(source, ImportPath(module=None, level=1, name="exported_object"))

        assert result == ImportPath(module=PKG)

    def test_namespace_package_boundary_is_not_returned_as_import_path(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")

        result = resolver.resolve_import_path(source, ImportPath(module="plugins"))

        assert result is None

    def test_missing_import_path_is_kept_for_unavailable_categorization(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")
        import_path = ImportPath(module="missing_module_xyz123")

        result = resolver.resolve_import_path(source, import_path)

        assert result is import_path


class TestResolveToModule:
    def test_relative_import_resolves_to_local_module(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")

        result = resolver.resolve_to_module(source, ImportPath(module=None, level=1, name="shared"))

        assert result.name == f"{PKG}.shared"
        assert result.category == ModuleCategory.LOCAL
        assert result.origin == package / "shared.py"

    def test_namespace_submodule_resolves_from_namespace_portion(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")

        result = resolver.resolve_to_module(source, ImportPath(module="plugins", name="leaf"))

        assert result.name == "plugins.leaf"
        assert result.category == ModuleCategory.LOCAL
        assert result.origin == source_root / "plugins" / "leaf.py"

    def test_missing_module_becomes_unavailable_module(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")

        result = resolver.resolve_to_module(source, ImportPath(module="missing_module_xyz123"))

        assert result.category == ModuleCategory.UNKNOWN
        assert isinstance(result.module, UnavailableModule)
        assert result.name == "missing_module_xyz123"

    def test_builtin_module_is_categorized_as_stdlib(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")

        result = resolver.resolve_to_module(source, ImportPath(module="sys"))

        assert result.name == "sys"
        assert result.category == ModuleCategory.STDLIB

    def test_project_source_root_takes_precedence_over_loaded_shadow_module(self, tmp_path: Path) -> None:
        module_name = "shadowedresolver"
        source_root = tmp_path / "src"
        external_root = tmp_path / "external"
        source_package = source_root / module_name
        external_package = external_root / module_name
        source_package.mkdir(parents=True)
        external_package.mkdir(parents=True)
        (source_package / "__init__.py").write_text("")
        (source_package / "consumer.py").write_text("")
        (external_package / "__init__.py").write_text("")

        importlib.invalidate_caches()
        sys.path.insert(0, str(external_root))
        try:
            loaded = importlib.import_module(module_name)
            assert loaded.__spec__ is not None
            assert loaded.__spec__.origin == str(external_package / "__init__.py")

            resolver = _resolver(source_root, package=module_name)
            source = _source(resolver, source_root, source_package / "consumer.py", package=module_name)

            result = resolver.resolve_to_module(source, ImportPath(module=module_name))

            assert result.name == module_name
            assert result.category == ModuleCategory.LOCAL
            assert result.origin == source_package / "__init__.py"
        finally:
            while str(external_root) in sys.path:
                sys.path.remove(str(external_root))
            for module in list(sys.modules):
                if module == module_name or module.startswith(f"{module_name}."):
                    del sys.modules[module]
            clear_module_spec_cache()
            importlib.invalidate_caches()


class TestResolveBatch:
    def test_batch_resolution_indexes_by_module_name(self, project: Tuple[Path, Path]) -> None:
        source_root, package = project
        resolver = _resolver(source_root)
        source = _source(resolver, source_root, package / "app.py")

        result = resolver.resolve_batch(
            source,
            [
                ImportPath(module=f"{PKG}.shared"),
                ImportPath(module="sys"),
            ],
        )

        assert set(result) == {f"{PKG}.shared", "sys"}
        assert result[f"{PKG}.shared"].category == ModuleCategory.LOCAL
        assert result["sys"].category == ModuleCategory.STDLIB
