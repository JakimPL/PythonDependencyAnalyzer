# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "anytree",
#     "beautifulsoup4",
#     "marimo",
#     "networkx",
#     "pydantic",
#     "pyvis",
#     "pyyaml",
# ]
# ///
import marimo

__generated_with = "0.23.11"
app = marimo.App(width="full", app_title="PDA Resolution Check")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # PDA Resolution Check

    This notebook is a strict inspection surface for module resolution. It
    creates a controlled project layout, shows raw resolution facts, and
    asserts the policy expectations that should hold.

    It intentionally does not catch resolver or analyzer errors. If an
    invariant is broken, the notebook should fail at the failing cell.
    """)
    return


@app.cell
def _(mo):
    import sys
    from collections import Counter
    from enum import Enum
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from textwrap import dedent
    from typing import Any, Iterable

    notebook_directory = mo.notebook_dir() or Path(__file__).parent
    repo_root = notebook_directory.parent
    project_src = repo_root / "src"
    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))

    from pda.analyzer import ModuleImportsAnalyzer, ModulesCollector
    from pda.analyzer.modules.lookup import RuntimeModuleLookup
    from pda.config import (
        ModuleImportsAnalyzerConfig,
        ModuleScanConfig,
        ModulesCollectorConfig,
    )
    from pda.models import module_pyvis_converter
    from pda.resolution import (
        ModuleResolution,
        ModuleResolutionService,
        ProjectResolutionContext,
        ResolutionDiagnosticCode,
        ResolutionMode,
        ResolutionStatus,
        ResolvedModuleKind,
        SourceModuleContext,
        TargetEnvironment,
    )
    from pda.specification import ImportPath, ModuleCategory

    return (
        Any,
        Counter,
        Enum,
        ImportPath,
        Iterable,
        ModuleCategory,
        ModuleImportsAnalyzer,
        ModuleImportsAnalyzerConfig,
        ModuleResolution,
        ModuleResolutionService,
        ModuleScanConfig,
        ModulesCollector,
        ModulesCollectorConfig,
        Path,
        ProjectResolutionContext,
        ResolutionDiagnosticCode,
        ResolutionMode,
        ResolutionStatus,
        ResolvedModuleKind,
        RuntimeModuleLookup,
        SourceModuleContext,
        TargetEnvironment,
        TemporaryDirectory,
        dedent,
        module_pyvis_converter,
        project_src,
        repo_root,
    )


@app.cell
def _(Path, TemporaryDirectory, dedent):
    workspace_handle = TemporaryDirectory(prefix="pda-resolution-check-")
    workspace = Path(workspace_handle.name)
    fixture_root = workspace / "fixture_project"
    fixture_src = fixture_root / "src"
    fixture_external = workspace / "external"

    demo_pkg_dir = fixture_src / "demo_pkg"
    demo_core_file = demo_pkg_dir / "core.py"
    demo_helper_file = demo_pkg_dir / "helper.py"
    tests_dir = fixture_src / "tests"
    namespace_dir = fixture_src / "ns_pkg"
    empty_namespace_dir = fixture_src / "empty_namespace"
    notes_file = fixture_src / "notes.txt"
    external_namespace_dir = fixture_external / "ns_pkg"
    external_pkg_dir = fixture_external / "external_pkg"

    def write_file(path: Path, source: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(source).lstrip(), encoding="utf-8")
        return path

    write_file(
        demo_pkg_dir / "__init__.py",
        """
        from .core import entry
        """,
    )
    write_file(
        demo_core_file,
        """
        import os
        from . import helper
        from .helper import util
        from ns_pkg import local_mod


        def entry():
            return util()
        """,
    )
    write_file(
        demo_helper_file,
        """
        def util():
            return "fixture"
        """,
    )
    write_file(
        tests_dir / "test_local.py",
        """
        VALUE = "local tests namespace"
        """,
    )
    write_file(
        namespace_dir / "local_mod.py",
        """
        VALUE = "local namespace portion"
        """,
    )
    write_file(
        external_namespace_dir / "external_mod.py",
        """
        VALUE = "external namespace portion"
        """,
    )
    write_file(
        external_pkg_dir / "__init__.py",
        """
        VALUE = "external package"
        """,
    )
    write_file(
        notes_file,
        """
        This file is intentionally not a Python module.
        """,
    )
    empty_namespace_dir.mkdir(parents=True, exist_ok=True)

    return (
        demo_core_file,
        demo_helper_file,
        demo_pkg_dir,
        empty_namespace_dir,
        external_namespace_dir,
        external_pkg_dir,
        fixture_external,
        fixture_root,
        fixture_src,
        namespace_dir,
        notes_file,
        tests_dir,
        workspace,
        workspace_handle,
    )


@app.cell
def _(
    ModuleResolutionService,
    ProjectResolutionContext,
    RuntimeModuleLookup,
    TargetEnvironment,
    fixture_external,
    fixture_root,
    fixture_src,
    project_src,
    repo_root,
):
    project_context = ProjectResolutionContext.create(
        fixture_root,
        source_roots=(fixture_src,),
        local_boundary=fixture_root,
    )
    project_service = ModuleResolutionService(project_context.environment)

    environment_with_external = TargetEnvironment.create(
        (fixture_src,),
        local_boundary=fixture_root,
        external_roots=(fixture_external,),
        include_sys_path=False,
    )
    service_with_external = ModuleResolutionService(environment_with_external)

    runtime_lookup = RuntimeModuleLookup.create()
    runtime_service = runtime_lookup.resolver

    repo_context = ProjectResolutionContext.create(
        repo_root,
        source_roots=(project_src,),
        local_boundary=repo_root,
    )
    repo_service = ModuleResolutionService(repo_context.environment)

    return (
        environment_with_external,
        project_context,
        project_service,
        repo_context,
        repo_service,
        runtime_lookup,
        runtime_service,
        service_with_external,
    )


@app.cell
def _(Any, Counter, Enum, Iterable, ModuleResolution, SourceModuleContext):
    def display_value(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, Enum):
            return str(value.value)

        return str(value)

    def display_paths(paths: Iterable[Any]) -> str:
        return "\n".join(display_value(path) for path in paths)

    def diagnostic_details(resolution: ModuleResolution) -> str:
        if resolution.diagnostic is None:
            return ""

        return ", ".join(f"{detail.key}={detail.value}" for detail in resolution.diagnostic.details)

    def resolution_row(label: str, resolution: ModuleResolution) -> dict[str, Any]:
        identity = resolution.identity
        location = resolution.location
        diagnostic = resolution.diagnostic
        portions = location.namespace_portions if location is not None else ()

        return {
            "case": label,
            "requested": resolution.requested,
            "mode": display_value(resolution.mode),
            "status": display_value(resolution.status),
            "identity": identity.name if identity is not None else "",
            "public_fqn": identity.public_fqn if identity is not None else "",
            "kind": display_value(resolution.kind),
            "category": display_value(resolution.category),
            "origin": display_value(location.origin if location is not None else None),
            "origin_type": display_value(location.origin_type if location is not None else None),
            "matched_root": display_value(location.matched_root if location is not None else None),
            "search_locations": display_paths(location.submodule_search_locations if location is not None else ()),
            "namespace_portions": display_paths(portion.path for portion in portions),
            "portion_categories": ", ".join(display_value(portion.category) for portion in portions),
            "diagnostic_code": display_value(diagnostic.code if diagnostic is not None else None),
            "diagnostic_message": diagnostic.message if diagnostic is not None else "",
            "diagnostic_details": diagnostic_details(resolution),
        }

    def context_row(label: str, context: Any, environment: Any) -> dict[str, Any]:
        return {
            "context": label,
            "project_root": display_value(getattr(context, "project_root", None)),
            "source_roots": display_paths(environment.source_roots),
            "local_boundary": display_value(environment.local_boundary),
            "external_roots": display_paths(environment.external_roots),
            "stdlib_roots": display_paths(environment.stdlib_roots),
            "include_sys_path": environment.include_sys_path,
        }

    def graph_summary_rows(label: str, graph: Any) -> list[dict[str, Any]]:
        data = graph.to_dict()
        categories = Counter(node["category"] for node in data["nodes"])
        unavailable = sum(1 for node in data["nodes"] if not node.get("available", True))
        rows = [
            {
                "graph": label,
                "metric": "nodes",
                "value": len(data["nodes"]),
            },
            {
                "graph": label,
                "metric": "links",
                "value": len(data["links"]),
            },
            {
                "graph": label,
                "metric": "unavailable",
                "value": unavailable,
            },
        ]
        rows.extend(
            {
                "graph": label,
                "metric": f"category:{category}",
                "value": count,
            }
            for category, count in sorted(categories.items())
        )
        return rows

    def require_resolved(label: str, resolution: ModuleResolution) -> None:
        assert resolution.resolved, f"{label} did not resolve: {resolution}"
        assert resolution.identity is not None, f"{label} resolved without identity: {resolution}"
        assert resolution.location is not None, f"{label} resolved without location: {resolution}"

    def require_source_context(label: str, context: SourceModuleContext | None) -> SourceModuleContext:
        assert context is not None, f"{label} did not produce a source context"
        return context

    return (
        context_row,
        graph_summary_rows,
        require_resolved,
        require_source_context,
        resolution_row,
    )


@app.cell(hide_code=True)
def _(mo, module_pyvis_converter):
    import base64

    pyvis_converter = module_pyvis_converter(theme=mo.app_meta().theme)
    network_kwargs = {**(pyvis_converter.config.network or {}), "cdn_resources": "in_line"}
    pyvis_converter.config = pyvis_converter.config.model_copy(update={"network": network_kwargs})

    def render_graph(graph, height: str = "520px"):
        html = pyvis_converter(graph, html=True)
        source = base64.b64encode(html.encode()).decode()
        return mo.Html(
            f'<iframe src="data:text/html;base64,{source}" '
            f'width="100%" height="{height}" style="border: none;"></iframe>'
        )

    return (render_graph,)


@app.cell
def _(
    ModuleCategory,
    ModuleImportsAnalyzer,
    ModuleImportsAnalyzerConfig,
    ModuleScanConfig,
    ModulesCollector,
    ModulesCollectorConfig,
    demo_pkg_dir,
    fixture_root,
    fixture_src,
):
    import_scan_config = ModuleScanConfig(
        stdlib_depth=1,
        external_depth=1,
        hide_private=False,
        hide_unavailable=False,
    )
    collect_scan_config = ModuleScanConfig(
        stdlib_depth=0,
        external_depth=0,
        hide_private=False,
        hide_unavailable=False,
    )
    collect_config = ModulesCollectorConfig(
        module_scan=collect_scan_config,
        qualified_names=True,
    )
    collector = ModulesCollector(
        config=collect_config,
        project_root=fixture_root,
        root_module_name="demo_pkg",
        source_roots=(fixture_src,),
    )
    modules_graph = collector()

    import_config = ModuleImportsAnalyzerConfig(
        module_scan=import_scan_config,
        qualified_names=True,
    )
    import_analyzer = ModuleImportsAnalyzer(
        config=import_config,
        project_root=fixture_root,
        root_module_name="demo_pkg",
        source_roots=(fixture_src,),
    )
    imports_graph = import_analyzer(demo_pkg_dir)

    collector_categories = collector.categories
    assert ModuleCategory.LOCAL in collector_categories

    return import_analyzer, imports_graph, modules_graph


@app.cell(hide_code=True)
def _(imports_graph, mo, modules_graph, render_graph):
    mo.vstack(
        [
            mo.md("## Fixture Graphs"),
            mo.md("### Import dependency graph"),
            render_graph(imports_graph),
            mo.md("### Module inventory graph"),
            render_graph(modules_graph),
        ]
    )
    return


@app.cell(hide_code=True)
def _(context_row, environment_with_external, mo, project_context, repo_context):
    mo.vstack(
        [
            mo.md("## Resolution Contexts"),
            mo.ui.table(
                [
                    context_row("fixture project", project_context, project_context.environment),
                    context_row("fixture project with external root", project_context, environment_with_external),
                    context_row("current repository", repo_context, repo_context.environment),
                ]
            ),
        ]
    )
    return


@app.cell
def _(project_service, service_with_external):
    project_name_resolutions = {
        "regular package": project_service.resolve_project_name("demo_pkg"),
        "source module": project_service.resolve_project_name("demo_pkg.core"),
        "local namespace package": project_service.resolve_project_name("tests"),
        "local namespace module": project_service.resolve_project_name("tests.test_local"),
        "stdlib module": project_service.resolve_project_name("os"),
        "missing module": project_service.resolve_project_name("missing_dependency"),
    }
    external_name_resolutions = {
        "mixed namespace package": service_with_external.resolve_project_name("ns_pkg"),
        "mixed namespace local module": service_with_external.resolve_project_name("ns_pkg.local_mod"),
        "mixed namespace external module": service_with_external.resolve_project_name("ns_pkg.external_mod"),
        "external regular package": service_with_external.resolve_project_name("external_pkg"),
    }
    return external_name_resolutions, project_name_resolutions


@app.cell(hide_code=True)
def _(external_name_resolutions, mo, project_name_resolutions, resolution_row):
    mo.vstack(
        [
            mo.md("## Name Resolution"),
            mo.ui.table(
                [
                    *(resolution_row(label, resolution) for label, resolution in project_name_resolutions.items()),
                    *(resolution_row(label, resolution) for label, resolution in external_name_resolutions.items()),
                ]
            ),
        ]
    )
    return


@app.cell
def _(
    demo_core_file,
    demo_pkg_dir,
    empty_namespace_dir,
    external_pkg_dir,
    notes_file,
    project_service,
    tests_dir,
):
    filesystem_resolutions = {
        "regular package directory": project_service.resolve_filesystem_path(demo_pkg_dir),
        "source module file": project_service.resolve_filesystem_path(demo_core_file),
        "local namespace directory": project_service.resolve_filesystem_path(tests_dir),
        "empty namespace directory": project_service.resolve_filesystem_path(empty_namespace_dir),
        "non-python file under source root": project_service.resolve_filesystem_path(notes_file),
        "path outside source roots": project_service.resolve_filesystem_path(external_pkg_dir / "__init__.py"),
    }
    return (filesystem_resolutions,)


@app.cell(hide_code=True)
def _(filesystem_resolutions, mo, resolution_row):
    mo.vstack(
        [
            mo.md("## Filesystem Resolution"),
            mo.ui.table([resolution_row(label, resolution) for label, resolution in filesystem_resolutions.items()]),
        ]
    )
    return


@app.cell
def _(
    ImportPath,
    demo_core_file,
    project_service,
    require_source_context,
):
    demo_core_context = require_source_context(
        "demo_pkg.core",
        project_service.source_context(demo_core_file),
    )
    import_path_resolutions = {
        "absolute stdlib import": project_service.resolve_import_path(
            demo_core_context,
            ImportPath.from_string("os"),
        ),
        "relative module import": project_service.resolve_import_path(
            demo_core_context,
            ImportPath.from_string(".helper"),
        ),
        "relative object import": project_service.resolve_import_path(
            demo_core_context,
            ImportPath(module="helper", level=1, name="util"),
        ),
        "from namespace import module": project_service.resolve_import_path(
            demo_core_context,
            ImportPath(module="ns_pkg", name="local_mod"),
        ),
        "relative import escaping package": project_service.resolve_import_path(
            demo_core_context,
            ImportPath.from_string("....outside"),
        ),
    }
    return demo_core_context, import_path_resolutions


@app.cell(hide_code=True)
def _(import_path_resolutions, mo, resolution_row):
    mo.vstack(
        [
            mo.md("## Import Path Resolution"),
            mo.ui.table([resolution_row(label, resolution) for label, resolution in import_path_resolutions.items()]),
        ]
    )
    return


@app.cell(hide_code=True)
def _(graph_summary_rows, imports_graph, mo, modules_graph):
    mo.vstack(
        [
            mo.md("## Analyzer Graph Summaries"),
            mo.ui.table(
                [
                    *graph_summary_rows("modules collector", modules_graph),
                    *graph_summary_rows("imports analyzer", imports_graph),
                ]
            ),
        ]
    )
    return


@app.cell
def _(repo_service):
    repo_resolutions = {
        "pda": repo_service.resolve_project_name("pda"),
        "pda.resolution": repo_service.resolve_project_name("pda.resolution"),
        "pda.resolution.resolver": repo_service.resolve_project_name("pda.resolution.resolver"),
        "tests outside configured source roots": repo_service.resolve_project_name("tests"),
    }
    return (repo_resolutions,)


@app.cell(hide_code=True)
def _(mo, repo_resolutions, resolution_row):
    mo.vstack(
        [
            mo.md("## Current Repository Name Resolution"),
            mo.ui.table([resolution_row(label, resolution) for label, resolution in repo_resolutions.items()]),
        ]
    )
    return


@app.cell
def _(
    ModuleCategory,
    ResolutionDiagnosticCode,
    ResolutionMode,
    ResolutionStatus,
    ResolvedModuleKind,
    external_name_resolutions,
    filesystem_resolutions,
    project_name_resolutions,
    require_resolved,
):
    require_resolved("demo_pkg", project_name_resolutions["regular package"])
    require_resolved("demo_pkg.core", project_name_resolutions["source module"])
    require_resolved("tests", project_name_resolutions["local namespace package"])
    require_resolved("tests.test_local", project_name_resolutions["local namespace module"])
    require_resolved("os", project_name_resolutions["stdlib module"])

    assert project_name_resolutions["regular package"].mode == ResolutionMode.PROJECT
    assert project_name_resolutions["source module"].category == ModuleCategory.LOCAL
    assert project_name_resolutions["local namespace package"].kind == ResolvedModuleKind.NAMESPACE_PACKAGE
    assert project_name_resolutions["local namespace package"].category == ModuleCategory.LOCAL
    assert project_name_resolutions["stdlib module"].category == ModuleCategory.STDLIB
    assert project_name_resolutions["missing module"].status == ResolutionStatus.UNAVAILABLE
    assert project_name_resolutions["missing module"].diagnostic is not None
    assert project_name_resolutions["missing module"].diagnostic.code == ResolutionDiagnosticCode.MODULE_SPEC_NOT_FOUND

    mixed_namespace = external_name_resolutions["mixed namespace package"]
    require_resolved("ns_pkg", mixed_namespace)
    assert mixed_namespace.kind == ResolvedModuleKind.NAMESPACE_PACKAGE
    assert mixed_namespace.category == ModuleCategory.LOCAL
    assert mixed_namespace.location is not None
    assert {portion.category for portion in mixed_namespace.location.namespace_portions} == {
        ModuleCategory.LOCAL,
        ModuleCategory.EXTERNAL,
    }

    assert filesystem_resolutions["regular package directory"].mode == ResolutionMode.FILESYSTEM
    assert filesystem_resolutions["source module file"].mode == ResolutionMode.FILESYSTEM
    assert filesystem_resolutions["local namespace directory"].kind == ResolvedModuleKind.NAMESPACE_PACKAGE
    assert filesystem_resolutions["empty namespace directory"].status == ResolutionStatus.UNAVAILABLE
    assert filesystem_resolutions["empty namespace directory"].diagnostic is not None
    assert (
        filesystem_resolutions["empty namespace directory"].diagnostic.code
        == ResolutionDiagnosticCode.NAMESPACE_WITHOUT_PYTHON_CHILD
    )
    assert filesystem_resolutions["non-python file under source root"].diagnostic is not None
    assert (
        filesystem_resolutions["non-python file under source root"].diagnostic.code
        == ResolutionDiagnosticCode.PATH_NOT_PYTHON_MODULE
    )
    assert filesystem_resolutions["path outside source roots"].diagnostic is not None
    assert (
        filesystem_resolutions["path outside source roots"].diagnostic.code
        == ResolutionDiagnosticCode.PATH_OUTSIDE_SOURCE_ROOTS
    )
    return


@app.cell
def _(runtime_service):
    runtime_sys_resolution = runtime_service.resolve_runtime_name("sys")
    return (runtime_sys_resolution,)


@app.cell(hide_code=True)
def _(mo, resolution_row, runtime_sys_resolution):
    mo.vstack(
        [
            mo.md("## Runtime Resolution"),
            mo.ui.table([resolution_row("runtime sys", runtime_sys_resolution)]),
        ]
    )
    return


@app.cell
def _(ResolutionMode, runtime_sys_resolution):
    assert runtime_sys_resolution.mode == ResolutionMode.RUNTIME, (
        "Runtime lookup must preserve ResolutionMode.RUNTIME; "
        f"got mode={runtime_sys_resolution.mode!r} for {runtime_sys_resolution!r}"
    )
    return


@app.cell
def _(ResolutionStatus, import_path_resolutions):
    relative_object_import = import_path_resolutions["relative object import"]
    assert relative_object_import.status == ResolutionStatus.AMBIGUOUS, (
        "from .helper import util should preserve ambiguity between a submodule, "
        "an exported object, and an unavailable binding; "
        f"got status={relative_object_import.status!r} for {relative_object_import!r}"
    )
    return


if __name__ == "__main__":
    app.run()
