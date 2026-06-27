# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo",
#     "anytree",
#     "beautifulsoup4",
#     "networkx",
#     "pydantic",
#     "pyyaml",
#     "pyvis",
# ]
# ///
import marimo

__generated_with = "0.23.11"
app = marimo.App(width="medium", app_title="PDA — self analysis")


@app.cell
def _(mo):
    mo.md("""
    # Python Dependency Analyzer — on itself

    [Python Dependency Analyzer (PDA)](https://github.com/JakimPL/PythonDependencyAnalyzer)
    maps how the modules in a Python project depend on one another: it follows the imports
    between modules, labels each one by where it comes from (local, standard library,
    third-party, or unresolved), and produces a dependency graph you can explore or export.

    This notebook runs **PDA against its own source tree** (`src/pda`, package `pda`).

    Move the controls to reshape the import graph live; the module inventory sits
    directly below it. The raw node-link JSON export is collected at the very end.
    """)
    return


@app.cell
async def _():
    import sys
    from pathlib import Path
    from typing import Final

    import marimo as mo

    MAX_COLLAPSE_LEVEL: Final[int] = 3
    MAX_DEPTH: Final[int] = 3

    if sys.platform == "emscripten":
        import io
        import zipfile

        import micropip
        from pyodide.http import pyfetch

        await micropip.install(["anytree", "beautifulsoup4", "networkx", "pydantic", "pyyaml", "pyvis"])

        bundle_root = Path("/app")
        if not (bundle_root / "src" / "pda").exists():
            response = await pyfetch(f"{mo.notebook_location()}/pda-bundle.zip")
            zipfile.ZipFile(io.BytesIO(await response.bytes())).extractall(bundle_root)

        project_src = bundle_root / "src"
    else:
        notebook_directory = mo.notebook_dir() or Path(__file__).parent
        project_src = notebook_directory.parent / "src"

    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))

    from pda.analyzer import ModuleImportsAnalyzer, ModulesCollector
    from pda.config import ModuleImportsAnalyzerConfig, ModuleScanConfig, ModulesCollectorConfig
    from pda.models import module_pyvis_converter

    if sys.platform == "emscripten":
        import ast as _ast

        from pda.specification.modules.sys_paths import SysPaths

        candidates = SysPaths().paths
        for key, value in list(candidates.items()):
            candidates[key] = Path("/" + str(value).lstrip("/"))
        candidates.setdefault("stdlib_archive", Path(_ast.__file__).parent)

    package = "pda"
    return (
        MAX_COLLAPSE_LEVEL,
        MAX_DEPTH,
        ModuleImportsAnalyzer,
        ModuleImportsAnalyzerConfig,
        ModuleScanConfig,
        ModulesCollector,
        ModulesCollectorConfig,
        mo,
        module_pyvis_converter,
        package,
        project_src,
    )


@app.cell
def _(mo, module_pyvis_converter):
    import base64

    pyvis_converter = module_pyvis_converter(theme=mo.app_meta().theme)
    network_kwargs = {**(pyvis_converter.config.network or {}), "cdn_resources": "in_line"}
    pyvis_converter.config = pyvis_converter.config.model_copy(update={"network": network_kwargs})

    def render_graph(graph, height="600px"):
        html = pyvis_converter(graph, html=True)
        source = base64.b64encode(html.encode()).decode()
        return mo.Html(
            f'<iframe src="data:text/html;base64,{source}" '
            f'width="100%" height="{height}" style="border: none;"></iframe>'
        )

    return (render_graph,)


@app.cell
def _(MAX_COLLAPSE_LEVEL: "Final[int]", MAX_DEPTH: "Final[int]", mo):
    import_collapse_level = mo.ui.slider(0, MAX_COLLAPSE_LEVEL, value=1, label="collapse level")
    import_stdlib_depth = mo.ui.slider(0, MAX_DEPTH, value=0, label="stdlib depth")
    import_external_depth = mo.ui.slider(0, MAX_DEPTH, value=0, label="external depth")
    import_hide_private = mo.ui.switch(value=True, label="hide private")
    import_unify_nodes = mo.ui.switch(value=True, label="unify nodes")
    import_qualified_names = mo.ui.switch(value=True, label="qualified names")

    mo.vstack(
        [
            mo.md("### Import-graph controls"),
            import_collapse_level,
            import_stdlib_depth,
            import_external_depth,
            import_hide_private,
            import_unify_nodes,
            import_qualified_names,
        ]
    )
    return (
        import_collapse_level,
        import_external_depth,
        import_hide_private,
        import_qualified_names,
        import_stdlib_depth,
        import_unify_nodes,
    )


@app.cell
def _(
    ModuleImportsAnalyzer,
    ModuleImportsAnalyzerConfig,
    ModuleScanConfig,
    import_collapse_level,
    import_external_depth,
    import_hide_private,
    import_qualified_names,
    import_stdlib_depth,
    import_unify_nodes,
    package,
    project_src,
    render_graph,
):
    import_config = ModuleImportsAnalyzerConfig(
        module_scan=ModuleScanConfig(
            stdlib_depth=import_stdlib_depth.value,
            external_depth=import_external_depth.value,
            hide_private=import_hide_private.value,
            hide_unavailable=True,
        ),
        unify_nodes=import_unify_nodes.value,
        qualified_names=import_qualified_names.value,
        collapse_level=import_collapse_level.value,
    )
    import_analyzer = ModuleImportsAnalyzer(config=import_config, project_root=project_src, package=package)
    import_graph = import_analyzer(project_src / package)

    render_graph(import_graph)
    return (import_graph,)


@app.cell
def _(mo):
    mo.md("""
    ## Module inventory

    `pda collect` enumerates a package's modules as a containment graph instead of
    following imports. Use the controls below to choose how far to descend into the
    standard library and external packages — both default to `0` (the package's own
    modules only).
    """)
    return


@app.cell
def _(MAX_COLLAPSE_LEVEL: "Final[int]", MAX_DEPTH: "Final[int]", mo):
    collect_collapse_level = mo.ui.slider(0, MAX_COLLAPSE_LEVEL, value=1, label="collapse level")
    collect_stdlib_depth = mo.ui.slider(0, MAX_DEPTH, value=0, label="stdlib depth")
    collect_external_depth = mo.ui.slider(0, MAX_DEPTH, value=0, label="external depth")
    collect_hide_private = mo.ui.switch(value=True, label="hide private")
    collect_qualified_names = mo.ui.switch(value=True, label="qualified names")

    mo.vstack(
        [
            mo.md("### Module-inventory controls"),
            collect_collapse_level,
            collect_stdlib_depth,
            collect_external_depth,
            collect_hide_private,
            collect_qualified_names,
        ]
    )
    return (
        collect_collapse_level,
        collect_external_depth,
        collect_hide_private,
        collect_qualified_names,
        collect_stdlib_depth,
    )


@app.cell
def _(collect_external_depth, collect_stdlib_depth, mo):
    (
        mo.callout(
            "Including standard-library or external modules makes collection considerably "
            "slower; keep both depths at 0 for a quick inventory of the package itself.",
            kind="warn",
        )
        if collect_stdlib_depth.value or collect_external_depth.value
        else None
    )
    return


@app.cell
def _(
    ModuleScanConfig,
    ModulesCollector,
    ModulesCollectorConfig,
    collect_collapse_level,
    collect_external_depth,
    collect_hide_private,
    collect_qualified_names,
    collect_stdlib_depth,
    package,
    project_src,
    render_graph,
):
    collect_config = ModulesCollectorConfig(
        module_scan=ModuleScanConfig(
            stdlib_depth=collect_stdlib_depth.value,
            external_depth=collect_external_depth.value,
            hide_private=collect_hide_private.value,
            hide_unavailable=True,
        ),
        qualified_names=collect_qualified_names.value,
        collapse_level=collect_collapse_level.value,
    )
    collector = ModulesCollector(config=collect_config, project_root=project_src, package=package)
    modules_graph = collector()

    render_graph(modules_graph)
    return


@app.cell
def _(
    collect_collapse_level,
    collect_external_depth,
    collect_hide_private,
    collect_qualified_names,
    collect_stdlib_depth,
    import_collapse_level,
    import_external_depth,
    import_hide_private,
    import_qualified_names,
    import_stdlib_depth,
    import_unify_nodes,
    mo,
    package,
):
    def _flag(name, enabled):
        return f"--{name}" if enabled else f"--no-{name}"

    analyze_command = "\n".join(
        [
            f"pda analyze src {package}",
            f"--collapse-level {import_collapse_level.value}",
            f"--stdlib-depth {import_stdlib_depth.value}",
            f"--external-depth {import_external_depth.value}",
            _flag("hide-private", import_hide_private.value),
            "--hide-unavailable",
            _flag("unify-nodes", import_unify_nodes.value),
            _flag("qualified-names", import_qualified_names.value),
            f"-o {package}-imports.json",
        ]
    )

    collect_command = "\n".join(
        [
            f"pda collect src {package}",
            f"--collapse-level {collect_collapse_level.value}",
            f"--stdlib-depth {collect_stdlib_depth.value}",
            f"--external-depth {collect_external_depth.value}",
            _flag("hide-private", collect_hide_private.value),
            _flag("qualified-names", collect_qualified_names.value),
            f"-o {package}-modules.json",
        ]
    )

    mo.md(f"""
        ## The same thing from the command line

        These commands reproduce the two graphs above with the current control values:

    ```bash
    {analyze_command}
    ```

    ```bash
    {collect_command}
    ```
        """)
    return


@app.cell
def _(import_graph, mo):
    data = import_graph.to_dict()
    mo.md(f"""
        ## Raw export

        The import graph as **node-link JSON** — `{len(data['nodes'])}` nodes,
        `{len(data['links'])}` links. Persist it with `import_graph.save("pda-imports.json")`
        or straight from the CLI with `pda analyze`. The full structure is rendered below:
        """)
    return (data,)


@app.cell
def _(data):
    data
    return


if __name__ == "__main__":
    app.run()
