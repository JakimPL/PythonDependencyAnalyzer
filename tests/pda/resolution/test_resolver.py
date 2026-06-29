from __future__ import annotations

import importlib
import sys
from importlib.machinery import FrozenImporter
from pathlib import Path

import pytest

from pda.resolution import (
    ModuleResolutionService,
    ProjectResolutionContext,
    ResolutionStatus,
    ResolvedModuleKind,
    TargetEnvironment,
)
from pda.specification import ImportPath, ModuleCategory, NamespacePortion
from pda.specification.imports.origin import OriginType


def _service(
    source_root: Path,
    *,
    local_boundary: Path | None = None,
    external_roots: tuple[Path, ...] = (),
    include_sys_path: bool = False,
) -> ModuleResolutionService:
    environment = TargetEnvironment.create(
        (source_root,),
        local_boundary=local_boundary,
        external_roots=external_roots,
        include_sys_path=include_sys_path,
    )
    return ModuleResolutionService(environment)


def test_filesystem_resolution_derives_modules_packages_and_namespace_portions(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    package = source_root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "module.py").write_text("")

    namespace = source_root / "namespace"
    namespace.mkdir()
    (namespace / "leaf.py").write_text("")

    empty = source_root / "empty"
    empty.mkdir()

    resolver = _service(source_root)

    package_resolution = resolver.resolve_filesystem_path(package)
    assert package_resolution.status == ResolutionStatus.RESOLVED
    assert package_resolution.identity is not None
    assert package_resolution.identity.public_fqn == "pkg"
    assert package_resolution.location is not None
    assert package_resolution.location.origin == package / "__init__.py"
    assert package_resolution.location.submodule_search_locations == (package,)
    assert package_resolution.kind == ResolvedModuleKind.REGULAR_PACKAGE
    assert package_resolution.category == ModuleCategory.LOCAL

    module_resolution = resolver.resolve_filesystem_path(package / "module.py")
    assert module_resolution.identity is not None
    assert module_resolution.identity.public_fqn == "pkg.module"
    assert module_resolution.kind == ResolvedModuleKind.SOURCE_MODULE
    assert module_resolution.category == ModuleCategory.LOCAL

    namespace_resolution = resolver.resolve_filesystem_path(namespace)
    assert namespace_resolution.identity is not None
    assert namespace_resolution.identity.public_fqn == "namespace"
    assert namespace_resolution.location is not None
    assert namespace_resolution.location.origin is None
    assert namespace_resolution.location.origin_type == OriginType.NONE
    assert namespace_resolution.location.submodule_search_locations == (namespace,)
    assert namespace_resolution.location.namespace_portions == (
        NamespacePortion(path=namespace, matched_root=source_root, category=ModuleCategory.LOCAL),
    )
    assert namespace_resolution.kind == ResolvedModuleKind.NAMESPACE_PACKAGE
    assert namespace_resolution.category == ModuleCategory.LOCAL

    empty_resolution = resolver.resolve_filesystem_path(empty)
    assert empty_resolution.status == ResolutionStatus.UNAVAILABLE


def test_filesystem_resolution_treats_nested_python_tree_as_namespace_portion(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    nested = source_root / "namespace" / "nested"
    nested.mkdir(parents=True)
    (nested / "leaf.py").write_text("")

    resolver = _service(source_root)

    namespace_resolution = resolver.resolve_filesystem_path(source_root / "namespace")
    assert namespace_resolution.status == ResolutionStatus.RESOLVED
    assert namespace_resolution.identity is not None
    assert namespace_resolution.identity.public_fqn == "namespace"
    assert namespace_resolution.kind == ResolvedModuleKind.NAMESPACE_PACKAGE
    assert namespace_resolution.category == ModuleCategory.LOCAL


def test_project_resolution_prefers_source_root_over_loaded_shadow_module(tmp_path: Path) -> None:
    module_name = "shadowed_pkg"
    source_root = tmp_path / "src"
    external_root = tmp_path / "external"

    source_package = source_root / module_name
    external_package = external_root / module_name
    source_package.mkdir(parents=True)
    external_package.mkdir(parents=True)
    (source_package / "__init__.py").write_text("")
    (external_package / "__init__.py").write_text("")

    sys.path.insert(0, str(external_root))
    try:
        loaded = importlib.import_module(module_name)
        assert loaded.__spec__.origin == str(external_package / "__init__.py")

        resolver = _service(source_root, include_sys_path=True)
        resolution = resolver.resolve_project_name(module_name)

        assert resolution.status == ResolutionStatus.RESOLVED
        assert resolution.location is not None
        assert resolution.location.origin == source_package / "__init__.py"
        assert resolution.category == ModuleCategory.LOCAL
    finally:
        while str(external_root) in sys.path:
            sys.path.remove(str(external_root))
        for module in list(sys.modules):
            if module == module_name or module.startswith(f"{module_name}."):
                del sys.modules[module]


def test_project_context_resolution_ignores_sys_path_regular_package_over_local_namespace(tmp_path: Path) -> None:
    module_name = "shadowed_namespace"
    project_root = tmp_path / "project"
    external_root = tmp_path / "external"

    local_namespace = project_root / module_name
    external_package = external_root / module_name
    local_namespace.mkdir(parents=True)
    external_package.mkdir(parents=True)
    (local_namespace / "test_app.py").write_text("")
    (external_package / "__init__.py").write_text("")

    sys.path.insert(0, str(external_root))
    importlib.invalidate_caches()
    try:
        context = ProjectResolutionContext.create(project_root)
        resolver = ModuleResolutionService(context.environment)
        resolution = resolver.resolve_project_name(module_name)

        assert resolution.status == ResolutionStatus.RESOLVED
        assert resolution.kind == ResolvedModuleKind.NAMESPACE_PACKAGE
        assert resolution.location is not None
        assert resolution.location.origin is None
        assert resolution.location.submodule_search_locations == (local_namespace,)
        assert resolution.category == ModuleCategory.LOCAL
    finally:
        while str(external_root) in sys.path:
            sys.path.remove(str(external_root))
        for module in list(sys.modules):
            if module == module_name or module.startswith(f"{module_name}."):
                del sys.modules[module]
        importlib.invalidate_caches()


def test_project_resolution_preserves_mixed_namespace_portions(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    external_root = tmp_path / "site-packages"
    local_namespace = source_root / "acme"
    external_namespace = external_root / "acme"
    local_namespace.mkdir(parents=True)
    external_namespace.mkdir(parents=True)
    (local_namespace / "local_mod.py").write_text("")
    (external_namespace / "external_mod.py").write_text("")

    resolver = _service(source_root, external_roots=(external_root,))

    namespace_resolution = resolver.resolve_project_name("acme")
    assert namespace_resolution.status == ResolutionStatus.RESOLVED
    assert namespace_resolution.kind == ResolvedModuleKind.NAMESPACE_PACKAGE
    assert namespace_resolution.location is not None
    assert namespace_resolution.location.origin is None
    assert namespace_resolution.location.submodule_search_locations == (local_namespace, external_namespace)
    assert namespace_resolution.location.namespace_portions == (
        NamespacePortion(path=local_namespace, matched_root=source_root, category=ModuleCategory.LOCAL),
        NamespacePortion(path=external_namespace, matched_root=external_root, category=ModuleCategory.EXTERNAL),
    )
    assert namespace_resolution.category == ModuleCategory.LOCAL

    module = resolver.to_categorized_module(namespace_resolution)
    assert module.namespace_portions == namespace_resolution.location.namespace_portions

    local_resolution = resolver.resolve_project_name("acme.local_mod")
    assert local_resolution.location is not None
    assert local_resolution.location.origin == local_namespace / "local_mod.py"
    assert local_resolution.category == ModuleCategory.LOCAL

    external_resolution = resolver.resolve_project_name("acme.external_mod")
    assert external_resolution.location is not None
    assert external_resolution.location.origin == external_namespace / "external_mod.py"
    assert external_resolution.category == ModuleCategory.EXTERNAL


def test_relative_import_resolution_uses_source_module_context(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    package = source_root / "pkg"
    subpackage = package / "sub"
    subpackage.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "shared.py").write_text("")
    (subpackage / "__init__.py").write_text("")
    (subpackage / "module.py").write_text("")

    resolver = _service(source_root)
    context = resolver.source_context(subpackage / "module.py")
    assert context is not None

    resolution = resolver.resolve_import_path(context, ImportPath(module="shared", level=2))

    assert resolution.status == ResolutionStatus.RESOLVED
    assert resolution.identity is not None
    assert resolution.identity.public_fqn == "pkg.shared"
    assert resolution.location is not None
    assert resolution.location.origin == package / "shared.py"


def test_from_import_name_prefers_submodule_then_falls_back_to_package(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    package = source_root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "module.py").write_text("")
    (package / "shared.py").write_text("")

    resolver = _service(source_root)
    context = resolver.source_context(package / "module.py")
    assert context is not None

    submodule = resolver.resolve_import_path(context, ImportPath(module=None, level=1, name="shared"))
    assert submodule.status == ResolutionStatus.RESOLVED
    assert submodule.identity is not None
    assert submodule.identity.public_fqn == "pkg.shared"
    assert submodule.location is not None
    assert submodule.location.origin == package / "shared.py"

    exported_object = resolver.resolve_import_path(context, ImportPath(module=None, level=1, name="missing_symbol"))
    assert exported_object.status == ResolutionStatus.RESOLVED
    assert exported_object.identity is not None
    assert exported_object.identity.public_fqn == "pkg"
    assert exported_object.kind == ResolvedModuleKind.REGULAR_PACKAGE


def test_relative_import_escaping_package_is_unavailable(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    package = source_root / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "module.py").write_text("")

    resolver = _service(source_root)
    context = resolver.source_context(package / "module.py")
    assert context is not None

    resolution = resolver.resolve_import_path(context, ImportPath(module="outside", level=2))

    assert resolution.status == ResolutionStatus.UNAVAILABLE


def test_project_resolution_handles_builtin_modules(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()

    resolver = _service(source_root)
    resolution = resolver.resolve_project_name("sys")

    assert resolution.status == ResolutionStatus.RESOLVED
    assert resolution.identity is not None
    assert resolution.identity.public_fqn == "sys"
    assert resolution.kind == ResolvedModuleKind.BUILTIN
    assert resolution.category == ModuleCategory.STDLIB


def test_project_resolution_handles_stdlib_packages_without_ambient_sys_path(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()

    resolver = _service(source_root)
    resolution = resolver.resolve_project_name("json")

    assert resolution.status == ResolutionStatus.RESOLVED
    assert resolution.identity is not None
    assert resolution.identity.public_fqn == "json"
    assert resolution.location is not None
    assert resolution.location.origin is not None
    assert resolution.category == ModuleCategory.STDLIB


def test_project_resolution_handles_frozen_stdlib_without_fake_local_origin(tmp_path: Path) -> None:
    source_root = tmp_path / "src"
    source_root.mkdir()

    resolver = _service(source_root)
    resolution = resolver.resolve_project_name("os")

    assert resolution.status == ResolutionStatus.RESOLVED
    assert resolution.category == ModuleCategory.STDLIB
    if resolution.kind == ResolvedModuleKind.FROZEN:
        assert resolution.location is not None
        assert resolution.location.origin is None


def test_project_resolution_handles_dotted_frozen_stdlib_alias(tmp_path: Path) -> None:
    if FrozenImporter.find_spec("os.path") is None:
        pytest.skip("os.path is not a dotted frozen module in this Python version")

    source_root = tmp_path / "src"
    source_root.mkdir()

    resolver = _service(source_root)
    resolution = resolver.resolve_project_name("os.path")

    assert resolution.status == ResolutionStatus.RESOLVED
    assert resolution.identity is not None
    assert resolution.identity.public_fqn == "os.path"
    assert resolution.kind == ResolvedModuleKind.FROZEN
    assert resolution.category == ModuleCategory.STDLIB
