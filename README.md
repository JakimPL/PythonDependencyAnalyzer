# Python Dependency Analyzer

Python Dependency Analyzer (PDA) helps you see and reason about how the modules in a
Python project depend on one another. You point it at a package and it produces a
dependency graph you can explore visually or export for further analysis — useful for
finding your way around an unfamiliar codebase, seeing what a package actually pulls in
and how heavily, or tracking how its structure changes over time.

PDA starts from one or more entry points, follows the imports between modules, and records
which module imports which. Every module it reaches is labelled by where it comes from —
your own code, the standard library, a third-party package, or something that could not be
resolved — so you can concentrate on the part of the picture you care about and keep the
rest out of the way.

## Module categories

PDA resolves each imported module the way Python itself does (through `importlib`), so the
result reflects what the interpreter would really load rather than a guess from reading
text. Each module is described along two independent axes.

**Category** — where the module comes from:

- **local** — code belonging to the project under analysis (the project root and package
  you point PDA at).
- **stdlib** — modules from the Python standard library that ship with the interpreter
  (`os`, `pathlib`, `json` etc.).
- **external** — installed third-party packages, i.e. dependencies that came from PyPI or
  a similar source.
- **unknown** — the origin could not be determined, e.g. an import that does not resolve in
  the current environment (an optional dependency that is not installed).

**Availability** — whether PDA could fully resolve and read the module. A module is
*unavailable* when it cannot be found, or when it is found but its source cannot be read for
analysis (for example a standard-library module shipped inside a zip, as in the Pyodide/WASM
build). Availability is orthogonal to category — a module can be, say, `stdlib` **and**
unavailable. The category drives the node colour; unavailable nodes are drawn dashed and
faded, and can be hidden with `--hide-unavailable`.

The category colours the visualization and drives the depth controls below: you can,
for instance, show your own modules in full while including third-party packages only at
the point where your code first touches them.

## Installation

PDA targets Python 3.13+.

```bash
# with uv
uv sync

# or with pip, editable
pip install -e .         # the package
pip install --group dev  # dev tooling (pip >= 25.1)
```

This installs the library and the `pda` command-line tool.

## Usage

### Import dependency graph — `pda analyze`

The minimal form analyses the `pda` root module under `src/` and writes
`pda-imports.json`:

```bash
pda analyze src pda
```

The project root is added to the import search path, so the module does not need to be
installed. `--paths` chooses the entry points to start from (comma-separated files or
directories) and defaults to the resolved local path for the root module.

For a repository-root invocation with a `src/` layout, keep the repository as the local
boundary and set the import source root explicitly:

```bash
pda analyze . pda --source-roots src
```

When `--source-roots` is provided and `--paths` is omitted, PDA resolves the root module
against those source roots and starts from the matching local package, namespace portion,
or module file. Multiple roots can be provided as a comma-separated list:

```bash
pda analyze . pda --source-roots packages/app,packages/lib
```

Most of the work is in shaping the graph to the question you are asking. The extended form
below keeps only your own modules, merges them to two name components, and labels nodes
with their full dotted path (each option is explained under [Options](#options)):

```bash
# Local modules only, merged to two dotted-name components, full dotted-path labels.
pda analyze src pda \
    --stdlib-depth 0 \
    --external-depth 0 \
    --hide-private \
    --qualified-names \
    --collapse-level 2 \
    --output pda-imports.json
```

### Package structure — `pda collect`

`pda collect` lists the modules that exist rather than following imports between them.
Standard-library and external modules are included according to `--stdlib-depth` /
`--external-depth`; a project root and root module name add that root's own modules.

```bash
# A root module's own modules only (both category depths set to 0).
pda collect src pda \
    --stdlib-depth 0 \
    --external-depth 0
```

For `src/` layout collection from the repository root:

```bash
pda collect . pda \
    --source-roots src \
    --stdlib-depth 0 \
    --external-depth 0
```

With the default (unlimited) depths, a bare `pda collect` inventories the entire installed
environment. That is a supported way to use it; on a large environment it can take a
while.

```bash
# The installed environment, one level into each category.
pda collect \
    --stdlib-depth 1 \
    --external-depth 1 \
    --output environment-modules.json
```

A root module name is required when a `project-root` is given. Output defaults to
`<root-module>-imports.json` for `analyze`, and `<root-module>-modules.json` (or
`modules.json`) for `collect`. Run `pda analyze --help` / `pda collect --help` for the
full list of options.

## PDA Output

PDA writes the graph as **node-link JSON**: a list of `nodes` and a list of directed
`links`. Each node records its category, its depth from the entry point (`level`), and the
file it came from; a module that could not be fully resolved also carries `"available":
false` (its `category` is its origin where known, or `unknown`), and modules that take part
in an import cycle carry `in_cycle` and a shared `component` id (see [Cycles](#cycles)). The
excerpt below is the result of analysing `pda.cli`, trimmed to one node and its first two
imports:

```json
{
  "directed": true,
  "nodes": [
    {
      "id": "pda.cli",
      "label": "pda.cli",
      "category": "local",
      "level": 0,
      "origin": ".../PythonDependencyAnalyzer/src/pda/cli.py"
    }
  ],
  "links": [
    {"source": "pda.cli", "target": "pda.analyzer"},
    {"source": "pda.cli", "target": "pda.config"}
  ]
}
```

This is a widely understood format: it loads directly into NetworkX
(`networkx.node_link_graph(..., edges="links")`), Cytoscape.js, D3, and sigma.js, so you
can lay it out, query it, or feed it into your own tooling.

### Interactive HTML

`pda analyze` and `pda collect` can also write an interactive
[pyvis](https://pyvis.readthedocs.io/) visualization. Pass `--format html`, or give
`--output` a `.html`/`.htm` path:

```bash
pda analyze src pda --format html --theme dark --layout package_ring
```

The file is self-contained — the vis-network assets are inlined, so it opens in any browser
with no network access or sidecar files. The format follows `--format` when given, otherwise
the `--output` extension (`.html`/`.htm` → HTML, `.json` → JSON); any other extension is an
error, and a `--format` that disagrees with the extension wins with a warning. When
`--output` is omitted the default name follows the chosen format (for example
`pda-imports.html`). `--theme` selects `light` or `dark`; `--layout` selects `hierarchical`
(laid out by vis.js, the default) or `package_ring` (positions computed by PDA, the better
choice for cyclic graphs). Both options apply to HTML output only.

## Options

A raw import graph of a real project is large and noisy. These controls trade detail for
legibility; all are available both as CLI flags and as configuration fields.

- **Category depth** (`--stdlib-depth`, `--external-depth`) — how far to follow imports
  *after* crossing into the standard library or a third-party package. `0` leaves the
  category out, `1` shows the module you first reach without descending into it, a larger
  number goes that many levels deep, and unlimited follows it all the way. This is how you
  keep third-party detail from drowning out your own code.
- **Collapsing** (`--collapse-level N`) — merge modules that share the start of their
  dotted name into a single node, after the graph is built. At level `0` everything under
  a top-level package becomes one node (all `pda.*` collapse into `pda`); at level `1` two
  components are kept (`pda.models.module` and `pda.models.scope` both become
  `pda.models`); higher levels keep more detail. This is separate from how far PDA scans —
  it restructures the finished graph.
- **Node unification** (`--unify-nodes`, on by default) — represent a module reached
  through several import paths as a single node, giving a true dependency graph.
  `--no-unify-nodes` instead emits one node per path (a tree-like view), which cannot
  contain cycles.
- **Visibility** (`--hide-private`, `--hide-unavailable`) and **labels**
  (`--qualified-names`) — drop modules whose names begin with `_` or that fail to resolve,
  and choose between short and fully-qualified names on nodes.

## Cycles

Circular imports are kept in the graph rather than treated as errors. When PDA finds a
cycle it:

- leaves the cycle's edges in place, so the dependency graph is faithful. A topological
  order is then impossible, so PDA falls back to a layered order grouped by
  strongly-connected component.
- tags every module in a cycle with `in_cycle` and a shared `component` id in the export.
- prints a report of the cycle groups, each with an example loop.

Write that report to a file with `--cycles-output`:

```bash
pda analyze src pda --cycles-output cycles.json
```

To treat cycles as a failure instead — for example as a CI gate — pass `--fail-on-cycle`,
which prints the same report and exits non-zero:

```bash
pda analyze src pda --fail-on-cycle
```

Cycles are a property of the unified dependency graph (the default); under
`--no-unify-nodes` the graph is a tree and has none. In the interactive visualization the
hierarchical layout assumes an acyclic graph, so for cyclic graphs PDA warns and the
`package_ring` layout is the better choice.

## Using PDA from Python

The CLI is a thin wrapper over the library, which exposes the same configuration and the
graph object directly:

```python
from pathlib import Path

from pda.analyzer import ModuleImportsAnalyzer
from pda.config import ModuleImportsAnalyzerConfig, ModuleResolutionConfig, ModuleScanConfig

config = ModuleImportsAnalyzerConfig(
    module_scan=ModuleScanConfig(stdlib_depth=0, external_depth=0, hide_private=True),
    resolution=ModuleResolutionConfig(source_roots=(Path("src"),)),
    unify_nodes=True,
    qualified_names=True,
    collapse_level=2,
)

analyzer = ModuleImportsAnalyzer(
    config=config,
    project_root=Path("."),
    root_module_name="pda",
)
graph = analyzer(Path("src/pda"))

graph.save("pda-imports.json")     # node-link JSON on disk
data = graph.to_dict()             # the same structure in memory
```

To render the interactive HTML view:

```python
from pda.models import module_pyvis_converter

converter = module_pyvis_converter(theme="dark")
html = converter(graph, html=True)  # interactive HTML string
```

### Using individual components

The two analyzers are orchestrations over smaller public components: filesystem-tree
walking, AST parsing, per-file import extraction, scope and symbol analysis, and module
resolution. Each can be used on its own — to parse a single module to AST nodes, list one
file's imports, or resolve a single name — without building a graph.
[docs/components.md](docs/components.md) documents these components as an API, with runnable
examples.

## Notebook

The [marimo](https://marimo.io/) notebooks under `notebooks/` are interactive walkthroughs.
Launch them from the repository root so they can locate `src/`:

```bash
pip install -e ".[notebook]"          # installs marimo
marimo edit notebooks/example.py
```

- `example.py` — runs PDA on its own source, with controls for the configuration so the graph
  updates as the parameters change.
- `forbidden_imports.py` — a transitive "forbidden dependency" check: pick a module and a set
  of anti-candidates and see whether it (directly or indirectly) imports any of them, with the
  witness import path. Uses the component API from [docs/components.md](docs/components.md).
- `ast_scope_explorer.py` — parses a single module and lets you browse its AST tree and scope
  tree, selecting any node to inspect its properties.

## Development

```bash
uv run pytest -q
uv run python -m mypy        # strict, over src/pda
uv run python -m pylint --rcfile=.pylintrc src/pda
```
