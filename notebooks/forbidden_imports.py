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
app = marimo.App(width="full", app_title="PDA Forbidden Imports")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Forbidden dependency check

    Enforce that a module `X` must not depend on a set of *anti-candidate* modules —
    **transitively**, not just directly. A direct-import check is fragile: `X` may import
    `Z`, and `Z` imports the forbidden `Y`, so `X` depends on `Y` without naming it.

    The dependency graph of the example project is shown first, so you can see what there is
    to choose from. Then pick `X` and its anti-candidates and read the result. The check runs
    `ModuleImportsAnalyzer` **once** on `X` — the returned `ModuleGraph` already is the
    transitive closure of everything `X` pulls in — and each anti-candidate is then a pure
    graph query (`graph.imports(...)` / `graph.import_path(...)`), not a fresh analysis.

    The fixture is a tiny synthetic project; the same code works against any project and makes
    a natural CI gate — see the generated snippet at the end.
    """)
    return


@app.cell
def _(mo):
    import sys
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from textwrap import dedent

    notebook_directory = mo.notebook_dir() or Path(__file__).parent
    project_src = notebook_directory.parent / "src"
    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))

    from pda.analyzer import ModuleImportsAnalyzer
    from pda.config import (
        ModuleImportsAnalyzerConfig,
        ModuleResolutionConfig,
        ModuleScanConfig,
    )
    from pda.models import module_pyvis_converter
    from pda.resolution import ModuleResolutionService, ProjectResolutionContext

    return (
        ModuleImportsAnalyzer,
        ModuleImportsAnalyzerConfig,
        ModuleResolutionConfig,
        ModuleResolutionService,
        ModuleScanConfig,
        Path,
        ProjectResolutionContext,
        TemporaryDirectory,
        dedent,
        module_pyvis_converter,
    )


@app.cell
def _(Path, TemporaryDirectory, dedent):
    workspace_handle = TemporaryDirectory(prefix="pda-forbidden-imports-")
    fixture_root = Path(workspace_handle.name) / "shop_project"
    fixture_src = fixture_root / "src"

    def write_module(relative_path: str, source: str) -> Path:
        path = fixture_src / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(source).lstrip(), encoding="utf-8")
        return path

    write_module("shop/__init__.py", "")
    checkout_file = write_module(
        "shop/checkout.py",
        """
        from .cart import Cart
        from .receipt import Receipt
        """,
    )
    cart_file = write_module(
        "shop/cart.py",
        """
        from .database import Session
        """,
    )
    database_file = write_module("shop/database.py", "Session = object\n")
    receipt_file = write_module("shop/receipt.py", "Receipt = object\n")
    email_file = write_module("shop/email.py", "send = print\n")

    fixture_files = {
        "shop.checkout": checkout_file,
        "shop.cart": cart_file,
        "shop.database": database_file,
        "shop.receipt": receipt_file,
        "shop.email": email_file,
    }

    return fixture_files, fixture_root, fixture_src, workspace_handle


@app.cell
def _(ModuleImportsAnalyzerConfig, ModuleResolutionConfig, ModuleScanConfig, fixture_src):
    analyzer_config = ModuleImportsAnalyzerConfig(
        module_scan=ModuleScanConfig(
            stdlib_depth=0,
            external_depth=0,
            hide_private=False,
            hide_unavailable=False,
        ),
        unify_nodes=True,
        qualified_names=True,
        resolution=ModuleResolutionConfig(source_roots=(fixture_src,)),
    )
    return (analyzer_config,)


@app.cell(hide_code=True)
def _(mo, module_pyvis_converter):
    import base64

    pyvis_converter = module_pyvis_converter(theme=mo.app_meta().theme)
    network_kwargs = {**(pyvis_converter.config.network or {}), "cdn_resources": "in_line"}
    pyvis_converter.config = pyvis_converter.config.model_copy(update={"network": network_kwargs})

    def render_graph(graph, height: str = "480px"):
        html = pyvis_converter(graph, html=True)
        source = base64.b64encode(html.encode()).decode()
        return mo.Html(
            f'<iframe src="data:text/html;base64,{source}" '
            f'width="100%" height="{height}" style="border: none;"></iframe>'
        )

    return (render_graph,)


@app.cell(hide_code=True)
def _(ModuleImportsAnalyzer, analyzer_config, fixture_root, fixture_src, mo, render_graph):
    overview_analyzer = ModuleImportsAnalyzer(
        config=analyzer_config,
        project_root=fixture_root,
        root_module_name="shop",
    )
    overview_graph = overview_analyzer([fixture_src / "shop"])

    mo.vstack(
        [
            mo.md("## The example project"),
            mo.md(
                "Every module in the `shop` package and the imports between them. Use this to "
                "decide which module to check (`X`) and which imports to forbid. A module drawn "
                "with no edges (e.g. `shop.email`) is imported by nothing."
            ),
            render_graph(overview_graph),
        ]
    )
    return


@app.cell
def _(ModuleResolutionService, ProjectResolutionContext, fixture_root, fixture_src):
    resolution_service = ModuleResolutionService(
        ProjectResolutionContext.create(
            fixture_root,
            source_roots=(fixture_src,),
            local_boundary=fixture_root,
        ).environment
    )
    return (resolution_service,)


@app.cell(hide_code=True)
def _(fixture_files, mo):
    source_module = mo.ui.dropdown(
        options=fixture_files,
        value="shop.checkout",
        label="source module X",
    )
    anti_candidates = mo.ui.multiselect(
        options=fixture_files,
        value=["shop.database", "shop.receipt", "shop.email"],
        label="anti-candidates (X must not import these)",
    )

    mo.vstack(
        [
            mo.md("## Controls"),
            source_module,
            anti_candidates,
        ]
    )
    return anti_candidates, source_module


@app.cell
def _(
    ModuleImportsAnalyzer,
    analyzer_config,
    fixture_root,
    resolution_service,
    source_module,
):
    analyzer = ModuleImportsAnalyzer(
        config=analyzer_config,
        project_root=fixture_root,
        root_module_name="shop",
    )
    imports_graph = analyzer([source_module.value])
    source_name = resolution_service.resolve_filesystem_path(source_module.value).identity.name

    return imports_graph, source_name


@app.cell(hide_code=True)
def _(anti_candidates, imports_graph, mo, resolution_service, source_name):
    result_rows = []
    target_names = []
    for anti_path in anti_candidates.value:
        target_name = resolution_service.resolve_filesystem_path(anti_path).identity.name
        if target_name == source_name:
            continue

        target_names.append(target_name)
        witness = imports_graph.import_path(source_name, target_name)
        result_rows.append(
            {
                "forbidden target": target_name,
                "imported by X": "yes" if imports_graph.imports(source_name, target_name) else "no",
                "how": "transitive" if witness and len(witness) > 2 else ("direct" if witness else ""),
                "witness path": " → ".join(witness) if witness else "",
            }
        )

    violations = [row for row in result_rows if row["imported by X"] == "yes"]
    status = (
        mo.callout(
            f"{source_name} violates {len(violations)} rule(s): "
            + ", ".join(row["forbidden target"] for row in violations),
            kind="danger",
        )
        if violations
        else mo.callout(f"{source_name} imports none of the anti-candidates.", kind="success")
    )

    mo.vstack(
        [
            mo.md(f"## Result for `{source_name}`"),
            status,
            mo.ui.table(result_rows, selection=None),
        ]
    )
    return (target_names,)


@app.cell(hide_code=True)
def _(Path, fixture_root, fixture_src, mo, source_module, source_name, target_names):
    root_module = source_name.split(".")[0]
    source_subdir = fixture_src.relative_to(fixture_root).as_posix()
    entry_subpath = Path(source_module.value).relative_to(fixture_root).as_posix()

    template = """from pathlib import Path

from pda.analyzer import ModuleImportsAnalyzer
from pda.config import ModuleImportsAnalyzerConfig, ModuleResolutionConfig, ModuleScanConfig

# Point these at your own project. This example uses a "{source_subdir}/" source layout;
# for a flat layout the source root is the project root itself.
PROJECT_ROOT = Path(".")
SOURCE_ROOTS = (PROJECT_ROOT / "{source_subdir}",)
ENTRY = PROJECT_ROOT / "{entry_subpath}"

config = ModuleImportsAnalyzerConfig(
    module_scan=ModuleScanConfig(stdlib_depth=0, external_depth=0),
    unify_nodes=True,
    resolution=ModuleResolutionConfig(source_roots=SOURCE_ROOTS),
)
graph = ModuleImportsAnalyzer(config=config, project_root=PROJECT_ROOT, root_module_name="{root_module}")([ENTRY])

source = "{source}"
forbidden = {forbidden}

violations = []
for target in forbidden:
    if graph.imports(source, target):
        witness = " -> ".join(graph.import_path(source, target))
        violations.append(f"{{source}} imports {{target}} (via {{witness}})")

if violations:
    raise ValueError("Forbidden imports: " + "; ".join(violations))

print(f"{{source}} imports none of the forbidden modules.")
"""
    code = template.format(
        source_subdir=source_subdir,
        entry_subpath=entry_subpath,
        root_module=root_module,
        source=source_name,
        forbidden=target_names,
    )

    mo.md(f"""
## Reproduce this check in code

The snippet below is generated from the current selection. It runs the analyzer once and
queries the graph — drop it into a script or a test to gate `{source_name}`. Adjust
`PROJECT_ROOT`, `SOURCE_ROOTS`, and `ENTRY` to match your project's layout.

```python
{code}
```
""")
    return


if __name__ == "__main__":
    app.run()
