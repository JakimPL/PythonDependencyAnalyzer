import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium", app_title="PDA — self analysis")


@app.cell
def _(mo):
    mo.md("""
        # Python Dependency Analyzer — on itself

        This notebook runs **PDA against its own source tree** (`src/pda`, package `pda`).

        Move the controls to reshape the import graph live, then scroll down for the raw
        node-link JSON export and the module inventory.
        """)
    return


@app.cell
def _():
    import sys
    from pathlib import Path

    import marimo as mo

    project_src = next(
        (c for c in (Path.cwd() / "src", Path.cwd().parent / "src") if (c / "pda").is_dir()),
        Path.cwd() / "src",
    )
    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))

    from pda.analyzer import ModuleImportsAnalyzer, ModulesCollector
    from pda.config import ModuleImportsAnalyzerConfig, ModuleScanConfig, ModulesCollectorConfig
    from pda.models import module_pyvis_converter

    package = "pda"
    return (
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
    pyvis_converter = module_pyvis_converter(theme=mo.app_meta().theme)
    return (pyvis_converter,)


@app.cell
def _(mo):
    collapse_level = mo.ui.slider(0, 3, value=1, label="collapse level")
    stdlib_depth = mo.ui.slider(0, 3, value=0, label="stdlib depth")
    external_depth = mo.ui.slider(0, 3, value=0, label="external depth")
    hide_private = mo.ui.switch(value=True, label="hide private")
    unify_nodes = mo.ui.switch(value=True, label="unify nodes")
    qualified_names = mo.ui.switch(value=True, label="qualified names")

    mo.vstack(
        [
            mo.md("### Import-graph controls"),
            collapse_level,
            stdlib_depth,
            external_depth,
            hide_private,
            unify_nodes,
            qualified_names,
        ]
    )
    return (
        collapse_level,
        external_depth,
        hide_private,
        qualified_names,
        stdlib_depth,
        unify_nodes,
    )


@app.cell
def _(
    ModuleImportsAnalyzer,
    ModuleImportsAnalyzerConfig,
    ModuleScanConfig,
    collapse_level,
    external_depth,
    hide_private,
    mo,
    package,
    project_src,
    pyvis_converter,
    qualified_names,
    stdlib_depth,
    unify_nodes,
):
    import_config = ModuleImportsAnalyzerConfig(
        module_scan=ModuleScanConfig(
            stdlib_depth=stdlib_depth.value,
            external_depth=external_depth.value,
            hide_private=hide_private.value,
            hide_unavailable=True,
        ),
        unify_nodes=unify_nodes.value,
        qualified_names=qualified_names.value,
        collapse_level=collapse_level.value,
    )
    import_analyzer = ModuleImportsAnalyzer(config=import_config, project_root=project_src, package=package)
    import_graph = import_analyzer(project_src / package)

    mo.iframe(pyvis_converter(import_graph, html=True))
    return (import_graph,)


@app.cell
def _(import_graph, mo):
    data = import_graph.to_dict()
    mo.md(f"""
        ### Export

        The same graph as **node-link JSON** — `{len(data['nodes'])}` nodes,
        `{len(data['links'])}` links. Persist it with `import_graph.save("pda-imports.json")`
        or straight from the CLI with `pda analyze`. The structure below is rendered live:
        """)
    return (data,)


@app.cell
def _(data):
    data
    return


@app.cell
def _(mo):
    mo.md("""
        ## Module inventory

        `pda collect` enumerates a package's modules as a containment graph instead of
        following imports. Standard-library and external modules are excluded here by
        setting their depth to `0`.
        """)
    return


@app.cell
def _(
    ModuleScanConfig,
    ModulesCollector,
    ModulesCollectorConfig,
    collapse_level,
    mo,
    package,
    project_src,
    pyvis_converter,
    qualified_names,
):
    collect_config = ModulesCollectorConfig(
        module_scan=ModuleScanConfig(stdlib_depth=0, external_depth=0, hide_private=True),
        qualified_names=qualified_names.value,
        collapse_level=collapse_level.value,
    )
    collector = ModulesCollector(config=collect_config, project_root=project_src, package=package)
    modules_graph = collector()

    mo.iframe(pyvis_converter(modules_graph, html=True))
    return


@app.cell
def _(mo):
    mo.md(r"""
        ## The same thing from the command line

        ```bash
        pda analyze src pda --collapse-level 1 --stdlib-depth 0 --external-depth 0 \
          --hide-private --hide-unavailable --unify-nodes --qualified-names -o pda-imports.json

        pda collect src pda --stdlib-depth 0 --external-depth 0 --hide-private -o pda-modules.json
        ```
        """)
    return


if __name__ == "__main__":
    app.run()
