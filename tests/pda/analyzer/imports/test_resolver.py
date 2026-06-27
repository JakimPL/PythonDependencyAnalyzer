from __future__ import annotations

import importlib.util
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, Union
from unittest.mock import Mock, patch

import pytest

from pda.analyzer.imports.resolver import ModuleResolver
from pda.config import ModuleImportsAnalyzerConfig
from pda.exceptions import PDAFindSpecError, PDAImportPathError, PDAMissingModuleSpecError
from pda.models import ModuleNode
from pda.specification import CategorizedModule, ImportPath, ModuleCategory, ModuleSource, UnavailableModule


def make_test_path(name: str) -> Path:
    """Create a test file path."""
    return Path(f"/test/project/{name}.py")


def create_resolver(
    qualified_names: bool = False,
    project_root: Optional[Path] = None,
    package: str = "test_package",
) -> ModuleResolver:
    """Helper to create a ModuleResolver instance."""
    config = ModuleImportsAnalyzerConfig(qualified_names=qualified_names)
    root = project_root or Path("/test/project")
    return ModuleResolver(project_root=root, package=package, config=config)


PATHLIB_SPEC = importlib.util.find_spec("pathlib")
TYPING_SPEC = importlib.util.find_spec("typing")
PATHLIB_FILE = Path(sys.modules["pathlib"].__file__)  # type: ignore


def assert_called_if(mock: Mock, condition: bool, *args: Any, **kwargs: Any) -> None:
    """Assert mock was called (or not) based on condition."""
    if condition:
        if args or kwargs:
            mock.assert_called_once_with(*args, **kwargs)
        else:
            mock.assert_called_once()
    else:
        mock.assert_not_called()


def setup_mock_source(
    spec_return: Optional[ModuleSpec] = None,
    package_spec_name: Optional[str] = None,
    base_path: Path = Path("/test/project"),
) -> Mock:
    """Create a properly configured mock ModuleSource."""
    mock_source = Mock(spec=ModuleSource)
    mock_source.get_spec.return_value = spec_return
    mock_source.base_path = base_path

    if package_spec_name:
        package_spec = type("PackageSpec", (), {"name": package_spec_name})()
        mock_source.get_package_spec.return_value = package_spec
    else:
        mock_source.get_package_spec.return_value = None

    return mock_source


@contextmanager
def mock_create_root_dependencies() -> Iterator[Tuple[Mock, Mock]]:
    """Context manager for create_root test dependencies."""
    with (
        patch("pda.analyzer.imports.resolver.ModuleSource"),
        patch("pda.analyzer.imports.resolver.CategorizedModule.create") as mock_create,
        patch("pda.analyzer.imports.resolver.ModuleNode") as mock_node,
    ):
        yield mock_create, mock_node


@contextmanager
def mock_resolve_import_path_dependencies(
    is_namespace: bool,
    expected_path: Optional[ImportPath],
) -> Iterator[Tuple[Mock, Mock, Mock]]:
    """Context manager for resolve_import_path test dependencies."""
    with (
        patch("pda.analyzer.imports.resolver.is_namespace_package", return_value=is_namespace) as mock_is_namespace,
        patch(
            "pda.analyzer.imports.resolver.validate_spec_origin", return_value=make_test_path("test")
        ) as mock_validate,
        patch("pda.analyzer.imports.resolver.SysPaths.resolve", return_value=expected_path) as mock_resolve,
    ):
        yield mock_is_namespace, mock_validate, mock_resolve


@contextmanager
def mock_resolve_to_module_dependencies(
    side_effect: Optional[Exception] = None,
) -> Iterator[Mock]:
    """Context manager for resolve_to_module test dependencies."""
    with patch("pda.analyzer.imports.resolver.CategorizedModule.from_spec") as mock_from_spec:
        if side_effect:
            mock_from_spec.side_effect = side_effect
        yield mock_from_spec


class TestModuleResolverInit:
    """Test ModuleResolver initialization."""

    def test_project_root_is_resolved(self) -> None:
        config = ModuleImportsAnalyzerConfig()
        relative_path = Path(".")
        resolver = ModuleResolver(project_root=relative_path, package="test", config=config)

        assert resolver._project_root.is_absolute()

    def test_stores_package_and_config(self) -> None:
        config = ModuleImportsAnalyzerConfig(qualified_names=True)
        resolver = ModuleResolver(project_root=Path("/test"), package="my_package", config=config)

        assert resolver._package == "my_package"
        assert resolver._config.qualified_names is True


class TestCreateRootMocked:
    """Test create_root method with fully mocked dependencies."""

    @dataclass
    class TestCase:
        __test__ = False

        label: str
        qualified_names: bool
        mock_module_name: str
        expected: Union[Mock, Type[Exception]]

    test_cases = [
        TestCase(
            label="qualified_names_true",
            qualified_names=True,
            mock_module_name="test_module",
            expected=Mock(spec=ModuleNode),
        ),
        TestCase(
            label="qualified_names_false",
            qualified_names=False,
            mock_module_name="test_module",
            expected=Mock(spec=ModuleNode),
        ),
        TestCase(
            label="missing_module_spec_raises",
            qualified_names=False,
            mock_module_name="",
            expected=PDAMissingModuleSpecError,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    def test_create_root(self, test_case: TestCase) -> None:
        resolver = create_resolver(qualified_names=test_case.qualified_names)
        test_file = make_test_path("test_module")

        with mock_create_root_dependencies() as (mock_create, mock_node):
            if isinstance(test_case.expected, type) and issubclass(test_case.expected, Exception):
                mock_create.side_effect = test_case.expected("Could not create root module")
                with pytest.raises(test_case.expected):
                    resolver.create_root(test_file)
            else:
                mock_categorized = Mock(spec=CategorizedModule)
                mock_categorized.name = test_case.mock_module_name
                mock_create.return_value = mock_categorized
                mock_node_instance = Mock(spec=ModuleNode)
                mock_node.return_value = mock_node_instance

                result = resolver.create_root(test_file)

                assert result == mock_node_instance
                mock_node.assert_called_once_with(mock_categorized, qualified_name=test_case.qualified_names)


class TestCreateRootReal:
    """Test create_root with real file paths."""

    def test_create_root_with_pathlib_file(self) -> None:
        test_file = PATHLIB_FILE
        project_root = test_file.parent.parent

        resolver = create_resolver(
            project_root=project_root,
            package="pathlib",
            qualified_names=False,
        )

        root = resolver.create_root(test_file)

        assert isinstance(root, ModuleNode)
        assert root.module.name == "pathlib.__init__"
        assert root.item is not None


class TestResolveImportPathMocked:
    """Test resolve_import_path with mocks to verify each code path."""

    @dataclass
    class TestCase:
        __test__ = False

        label: str
        spec_return: Optional[ModuleSpec]
        is_namespace: bool
        expected: Optional[ImportPath]
        is_namespace_called: bool
        validate_origin_called: bool
        resolve_called: bool

    test_cases = [
        TestCase(
            label="namespace_package_returns_none",
            spec_return=Mock(spec=ModuleSpec, name="test"),
            is_namespace=True,
            expected=None,
            is_namespace_called=True,
            validate_origin_called=False,
            resolve_called=False,
        ),
        TestCase(
            label="successful_resolution",
            spec_return=Mock(spec=ModuleSpec, name="test"),
            is_namespace=False,
            expected=ImportPath(module="test.resolved"),
            is_namespace_called=True,
            validate_origin_called=True,
            resolve_called=True,
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    def test_resolve_import_path(self, test_case: TestCase) -> None:
        resolver = create_resolver()
        mock_import_path = Mock(spec=ImportPath)

        mock_source = setup_mock_source(spec_return=test_case.spec_return)

        with mock_resolve_import_path_dependencies(test_case.is_namespace, test_case.expected) as (
            mock_is_namespace,
            mock_validate,
            mock_resolve,
        ):
            result = resolver.resolve_import_path(mock_source, mock_import_path)

        assert result == test_case.expected
        assert_called_if(mock_is_namespace, test_case.is_namespace_called, test_case.spec_return)
        assert_called_if(mock_validate, test_case.validate_origin_called)
        assert_called_if(mock_resolve, test_case.resolve_called)


class TestResolveToModuleMocked:
    """Test resolve_to_module with mocked dependencies."""

    @dataclass
    class TestCase:
        __test__ = False

        label: str
        spec_return: Optional[ModuleSpec]
        package_spec_name: Optional[str]
        expected: CategorizedModule
        from_spec_called: bool

    test_cases = [
        TestCase(
            label="spec_none_returns_unavailable",
            spec_return=None,
            package_spec_name=None,
            expected=CategorizedModule(
                module=UnavailableModule(
                    name="test.module",
                    package=None,
                    error=PDAFindSpecError(ImportPath(module="test.module")),
                ),
                category=ModuleCategory.UNAVAILABLE,
            ),
            from_spec_called=False,
        ),
        TestCase(
            label="spec_none_with_package",
            spec_return=None,
            package_spec_name="test_package",
            expected=CategorizedModule(
                module=UnavailableModule(
                    name="test.module",
                    package="test_package",
                    error=PDAFindSpecError(ImportPath(module="test.module")),
                ),
                category=ModuleCategory.UNAVAILABLE,
            ),
            from_spec_called=False,
        ),
        TestCase(
            label="attribute_error_returns_unavailable",
            spec_return=Mock(spec=ModuleSpec, name="test.module.spec"),
            package_spec_name=None,
            expected=CategorizedModule(
                module=UnavailableModule(
                    name="test.module",
                    package=None,
                    error=AttributeError("test"),
                ),
                category=ModuleCategory.UNAVAILABLE,
            ),
            from_spec_called=True,
        ),
        TestCase(
            label="key_error_returns_unavailable",
            spec_return=Mock(spec=ModuleSpec, name="test.module.spec"),
            package_spec_name=None,
            expected=CategorizedModule(
                module=UnavailableModule(
                    name="test.module",
                    package=None,
                    error=KeyError("test"),
                ),
                category=ModuleCategory.UNAVAILABLE,
            ),
            from_spec_called=True,
        ),
        TestCase(
            label="index_error_returns_unavailable",
            spec_return=Mock(spec=ModuleSpec, name="test.module.spec"),
            package_spec_name=None,
            expected=CategorizedModule(
                module=UnavailableModule(
                    name="test.module",
                    package=None,
                    error=IndexError("test"),
                ),
                category=ModuleCategory.UNAVAILABLE,
            ),
            from_spec_called=True,
        ),
        TestCase(
            label="import_path_error_returns_unavailable",
            spec_return=Mock(spec=ModuleSpec, name="test.module.spec"),
            package_spec_name=None,
            expected=CategorizedModule(
                module=UnavailableModule(
                    name="test.module",
                    package=None,
                    error=PDAImportPathError("test"),
                ),
                category=ModuleCategory.UNAVAILABLE,
            ),
            from_spec_called=True,
        ),
    ]

    exception_map = {
        "attribute_error_returns_unavailable": AttributeError("test"),
        "key_error_returns_unavailable": KeyError("test"),
        "index_error_returns_unavailable": IndexError("test"),
        "import_path_error_returns_unavailable": PDAImportPathError("test"),
    }

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    def test_resolve_to_module(self, test_case: TestCase) -> None:
        resolver = create_resolver()
        mock_import_path = ImportPath(module="test.module")

        mock_source = setup_mock_source(
            spec_return=test_case.spec_return,
            package_spec_name=test_case.package_spec_name,
        )

        if test_case.spec_return is not None:
            test_case.spec_return.name = "test.module"

        side_effect = self.exception_map.get(test_case.label)

        with mock_resolve_to_module_dependencies(side_effect) as mock_from_spec:
            result = resolver.resolve_to_module(mock_source, mock_import_path)

        assert result.category == test_case.expected.category
        assert result.module.name == test_case.expected.module.name
        assert result.module.package == test_case.expected.module.package
        assert type(result.module) == type(test_case.expected.module)
        if isinstance(result.module, UnavailableModule) and isinstance(test_case.expected.module, UnavailableModule):
            assert type(result.module.error) == type(test_case.expected.module.error)
            assert str(result.module.error) == str(test_case.expected.module.error)

        assert_called_if(
            mock_from_spec,
            test_case.from_spec_called,
            test_case.spec_return,
            project_root=resolver._project_root,
            package=test_case.package_spec_name,
        )


class TestResolveToModuleReal:
    """Test resolve_to_module with real stdlib module specs."""

    def test_pathlib_resolution(self) -> None:
        resolver = create_resolver()
        mock_import_path = ImportPath(module="pathlib")
        mock_source = setup_mock_source(spec_return=PATHLIB_SPEC)

        result = resolver.resolve_to_module(mock_source, mock_import_path)

        assert result.name == "pathlib"
        assert result.category == ModuleCategory.STDLIB

    def test_typing_resolution(self) -> None:
        resolver = create_resolver()
        mock_import_path = ImportPath(module="typing")
        mock_source = setup_mock_source(spec_return=TYPING_SPEC)

        result = resolver.resolve_to_module(mock_source, mock_import_path)

        assert result.name == "typing"
        assert result.category == ModuleCategory.STDLIB

    def test_nonexistent_module(self) -> None:
        resolver = create_resolver()
        mock_import_path = ImportPath(module="nonexistent_module_xyz123")
        mock_source = setup_mock_source(spec_return=None)

        result = resolver.resolve_to_module(mock_source, mock_import_path)

        module = UnavailableModule(
            name="nonexistent_module_xyz123",
            package=None,
            error=PDAFindSpecError(mock_import_path),
        )
        expected = CategorizedModule(
            module=module,
            category=ModuleCategory.UNAVAILABLE,
        )

        assert result.category == expected.category
        assert result.module.name == module.name
        assert result.module.package == module.package
        assert type(result.module) == type(module)
        assert isinstance(result.module, UnavailableModule)
        assert type(result.module.error) == type(module.error)
        assert str(result.module.error) == str(module.error)


class TestResolveBatchMocked:
    """Test resolve_batch with mocked resolve_to_module."""

    @dataclass
    class TestCase:
        __test__ = False

        label: str
        import_paths: List[ImportPath]
        expected: Dict[str, CategorizedModule]

    test_cases = [
        TestCase(label="empty", import_paths=[], expected={}),
        TestCase(
            label="single",
            import_paths=[ImportPath(module="test")],
            expected={
                "test": CategorizedModule(
                    module=UnavailableModule(name="test", package=None),
                    category=ModuleCategory.UNAVAILABLE,
                )
            },
        ),
        TestCase(
            label="multiple",
            import_paths=[
                ImportPath(module="test1"),
                ImportPath(module="test2"),
                ImportPath(module="test3"),
            ],
            expected={
                "test1": CategorizedModule(
                    module=UnavailableModule(name="test1", package=None),
                    category=ModuleCategory.UNAVAILABLE,
                ),
                "test2": CategorizedModule(
                    module=UnavailableModule(name="test2", package=None),
                    category=ModuleCategory.UNAVAILABLE,
                ),
                "test3": CategorizedModule(
                    module=UnavailableModule(name="test3", package=None),
                    category=ModuleCategory.UNAVAILABLE,
                ),
            },
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.label)
    def test_batch_resolution(self, test_case: TestCase) -> None:
        resolver = create_resolver()
        mock_source = Mock(spec=ModuleSource)

        with patch.object(resolver, "resolve_to_module") as mock_resolve:

            def create_module(source: ModuleSource, path: ImportPath) -> CategorizedModule:
                return CategorizedModule(
                    module=UnavailableModule(name=path.module or "unknown", package=None),
                    category=ModuleCategory.UNAVAILABLE,
                )

            mock_resolve.side_effect = create_module
            result = resolver.resolve_batch(mock_source, test_case.import_paths)

        assert result == test_case.expected


class TestResolveBatchReal:
    """Test resolve_batch with real modules."""

    def test_batch_with_pathlib_and_typing(self) -> None:
        resolver = create_resolver()
        import_paths = [ImportPath(module="pathlib"), ImportPath(module="typing")]
        mock_source = setup_mock_source()
        mock_source.get_spec.side_effect = [PATHLIB_SPEC, TYPING_SPEC]

        result = resolver.resolve_batch(mock_source, import_paths)

        assert len(result) == 2
        assert "pathlib" in result
        assert "typing" in result
        assert result["pathlib"].name == "pathlib"
        assert result["pathlib"].category == ModuleCategory.STDLIB
        assert result["typing"].name == "typing"
        assert result["typing"].category == ModuleCategory.STDLIB


class TestModuleValidationOptionsProperty:
    """Test the module_validation_options property."""

    def test_returns_correct_options(self) -> None:
        resolver = create_resolver()
        options = resolver.module_validation_options

        assert options.allow_missing_spec is True
        assert options.validate_origin is True
        assert options.expect_python is False
        assert options.raise_error is False


def test_resolve_import_path_keeps_missing_spec_for_categorization() -> None:
    resolver = create_resolver()
    import_path = ImportPath(module="missing_module")
    source = setup_mock_source(spec_return=None)

    result = resolver.resolve_import_path(source, import_path)

    assert result is import_path


def test_resolve_import_path_falls_back_when_origin_outside_known_roots() -> None:
    resolver = create_resolver()
    import_path = ImportPath(module="yaml")
    source = setup_mock_source(spec_return=Mock(spec=ModuleSpec))

    with (
        patch("pda.analyzer.imports.resolver.is_namespace_package", return_value=False),
        patch("pda.analyzer.imports.resolver.validate_spec_origin", return_value=Path("/cache/yaml/__init__.py")),
        patch("pda.analyzer.imports.resolver.SysPaths.resolve", return_value=None),
    ):
        result = resolver.resolve_import_path(source, import_path)

    assert result is import_path


def test_resolve_import_path_drops_unresolvable_builtin_origin() -> None:
    resolver = create_resolver()
    import_path = ImportPath(module="sys")
    source = setup_mock_source(spec_return=Mock(spec=ModuleSpec))

    with (
        patch("pda.analyzer.imports.resolver.is_namespace_package", return_value=False),
        patch("pda.analyzer.imports.resolver.validate_spec_origin", return_value=Path("built-in")),
        patch("pda.analyzer.imports.resolver.SysPaths.resolve", return_value=None),
    ):
        result = resolver.resolve_import_path(source, import_path)

    assert result is None
