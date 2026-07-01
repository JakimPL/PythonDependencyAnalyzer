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
app = marimo.App(width="full", app_title="PDA AST & Scope Explorer")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # AST & scope explorer

    Pick any Python module with the file browser and inspect it two ways:

    - the **module AST** — every syntax node (`ASTForest` / `ASTNode`), drawn as a pyvis tree, and
    - a node **explorer** — browse the AST or the scope hierarchy (`ScopeAnalyzer` /
      `ScopeNode` / `Symbol`) and select any node to see its properties. For an AST node the
      panel also shows the **enclosing scope** (via `ScopeBuilder`'s node→scope map) — that is
      "AST parsing *with* scope".

    Selecting a file that is not valid Python raises a parse error rather than failing silently.
    """)
    return


@app.cell
def _(mo):
    import sys
    from pathlib import Path

    notebook_directory = mo.notebook_dir() or Path(__file__).parent
    repo_root = notebook_directory.parent
    project_src = repo_root / "src"
    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))

    from pda.analyzer import ScopeAnalyzer, ScopeBuilder
    from pda.models import ASTForest
    from pda.structures import PyVisConverter

    default_module = project_src / "pda" / "specification" / "modules" / "module" / "kind.py"

    return (
        ASTForest,
        Path,
        PyVisConverter,
        ScopeAnalyzer,
        ScopeBuilder,
        default_module,
    )


@app.cell(hide_code=True)
def _(default_module, mo):
    mo.md(f"""
    ## Choose a module

    Browse to any `.py` file below and select it. Until you pick one, the explorer uses
    `{default_module.name}`.

    The browser talks to the kernel to list directories, so its cell must have run in the
    session. Under marimo's default (autorun) that happens on open; if you see
    *"run the cell first"*, run this notebook (or that cell) once.
    """)
    return


@app.cell(hide_code=True)
def _(default_module, mo):
    file_browser = mo.ui.file_browser(
        initial_path=default_module.parent,
        filetypes=[".py"],
        selection_mode="file",
        multiple=False,
        label="module to inspect",
    )
    file_browser
    return (file_browser,)


@app.cell
def _(ASTForest, Path, ScopeAnalyzer, ScopeBuilder, default_module, file_browser):
    selection = file_browser.value
    module_path = Path(selection[0].path) if selection else default_module

    try:
        ast_forest = ASTForest([module_path])
    except (SyntaxError, ValueError, FileNotFoundError) as error:
        raise ValueError(f"Cannot parse '{module_path}': {error}") from error

    for ast_node in ast_forest:
        ast_node.level = ast_node.depth

    scope_forest = ScopeAnalyzer()([module_path])
    for scope_node in scope_forest:
        scope_node.level = scope_node.depth

    scope_builder = ScopeBuilder()
    scope_builder(ast_forest)
    node_to_scope = scope_builder.node_to_scope

    return ast_forest, module_path, node_to_scope, scope_forest


@app.cell(hide_code=True)
def _(PyVisConverter, mo):
    import base64

    tree_converter = PyVisConverter(theme=mo.app_meta().theme)
    network_kwargs = {**(tree_converter.config.network or {}), "cdn_resources": "in_line"}
    tree_converter.config = tree_converter.config.model_copy(update={"network": network_kwargs})

    def render_tree(graph, height: str = "560px"):
        html = tree_converter(graph, html=True)
        source = base64.b64encode(html.encode()).decode()
        return mo.Html(
            f'<iframe src="data:text/html;base64,{source}" '
            f'width="100%" height="{height}" style="border: none;"></iframe>'
        )

    return (render_tree,)


@app.cell(hide_code=True)
def _(ast_forest, mo, module_path, render_tree):
    mo.vstack(
        [
            mo.md(f"## Module AST — `{module_path.name}`"),
            mo.md("Every syntax node of the module, laid out top-down by tree depth and coloured by node group."),
            render_tree(ast_forest.graph),
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    view_selection = mo.ui.radio(
        options=["AST tree", "Scope tree"],
        value="AST tree",
        label="explorer view",
    )

    mo.vstack(
        [
            mo.md("## Explore nodes"),
            mo.md("Choose a view, then select a node below to inspect its properties."),
            view_selection,
        ]
    )
    return (view_selection,)


@app.cell(hide_code=True)
def _(ast_forest, mo, scope_forest, view_selection):
    is_ast_view = view_selection.value == "AST tree"
    active_forest = ast_forest if is_ast_view else scope_forest

    node_by_key = {}
    for index, node in enumerate(active_forest):
        key = f"{index:03d}  {'· ' * node.depth}{node.label}"
        node_by_key[key] = node

    node_selection = mo.ui.dropdown(
        options=list(node_by_key.keys()),
        value=next(iter(node_by_key)),
        label="node",
    )

    node_selection
    return is_ast_view, node_by_key, node_selection


@app.cell(hide_code=True)
def _(is_ast_view, mo, node_by_key, node_selection, node_to_scope):
    selected_node = node_by_key[node_selection.value]

    if is_ast_view:
        ast_object = selected_node.ast
        enclosing_scope = node_to_scope.get(selected_node)
        properties = {
            "label": selected_node.label,
            "ast type": selected_node.type.__name__,
            "fqn": selected_node.fqn or "(module root)",
            "group": selected_node.group,
            "line": getattr(ast_object, "lineno", None),
            "column": getattr(ast_object, "col_offset", None),
            "enclosing scope": (
                f"{enclosing_scope.scope_type.value}: {enclosing_scope.fqn or '(module)'}"
                if enclosing_scope is not None
                else ""
            ),
            "dump": selected_node.details,
        }
        panel = mo.vstack(
            [
                mo.md(f"### AST node — `{selected_node.label}`"),
                mo.ui.table(
                    [{"property": key, "value": str(value)} for key, value in properties.items()],
                    selection=None,
                ),
            ]
        )
    else:
        symbol_rows = [
            {"name": name, "kind": symbol.kind.value, "line": symbol.span.lineno}
            for name, symbol in selected_node.symbols.items()
        ]
        properties = {
            "scope type": selected_node.scope_type.value,
            "fqn": selected_node.fqn or "(module)",
            "ast node": selected_node.node.label,
            "origin": selected_node.origin.name,
            "symbols": len(selected_node.symbols),
            "imports": len(selected_node.imports),
        }
        panel = mo.vstack(
            [
                mo.md(f"### Scope — `{selected_node.scope_type.value}`"),
                mo.ui.table(
                    [{"property": key, "value": str(value)} for key, value in properties.items()],
                    selection=None,
                ),
                mo.md("**Symbols in this scope**"),
                mo.ui.table(symbol_rows, selection=None) if symbol_rows else mo.md("_none_"),
            ]
        )

    panel
    return


if __name__ == "__main__":
    app.run()
