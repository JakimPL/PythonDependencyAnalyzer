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
text. Each resolved module is placed in one of four categories:

- **local** — code belonging to the project under analysis (the project root and package
  you point PDA at).
- **stdlib** — modules from the Python standard library that ship with the interpreter
  (`os`, `pathlib`, `json` etc.).
- **external** — installed third-party packages, i.e. dependencies that came from PyPI or
  a similar source.
- **unavailable** — names that an import refers to but that cannot be resolved in the
  current environment, for example an optional dependency that is not installed.

These categories colour the visualization and drive the depth controls below: you can,
for instance, show your own modules in full while including third-party packages only at
the point where your code first touches them.

## Installation

PDA targets Python 3.13+.

```bash
# with uv
uv sync --extra dev

# or with pip, editable
pip install -e ".[dev]"
```

This installs the library and the `pda` command-line tool.

## Usage

### Import dependency graph — `pda analyze`

The minimal form analyses the `pda` package rooted at `src/` and writes
`pda-imports.json`:

```bash
pda analyze src pda
```

The project root is added to the import search path, so the package does not need to be
installed. `--paths` chooses the entry points to start from (comma-separated files or
directories) and defaults to the whole project root.

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
`--external-depth`; a project root and package add that package's own modules.

```bash
# A package's own modules only (both category depths set to 0).
pda collect src pda \
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

A `package` is required when a `project-root` is given. Output defaults to
`<package>-imports.json` for `analyze`, and `<package>-modules.json` (or `modules.json`)
for `collect`. Run `pda analyze --help` / `pda collect --help` for the full list of
options.

## PDA Output

PDA writes the graph as **node-link JSON**: a list of `nodes` and a list of directed
`links`. Each node records its category, its depth from the entry point (`level`), and the
file it came from; modules that take part in an import cycle also carry `in_cycle` and a
shared `component` id (see [Cycles](#cycles)). The excerpt below is the result of analysing
`pda.cli`, trimmed to one node and its first two imports:

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
from pda.config import ModuleImportsAnalyzerConfig, ModuleScanConfig

config = ModuleImportsAnalyzerConfig(
    module_scan=ModuleScanConfig(stdlib_depth=0, external_depth=0, hide_private=True),
    unify_nodes=True,
    qualified_names=True,
    collapse_level=2,
)

analyzer = ModuleImportsAnalyzer(config=config, project_root=Path("src"), package="pda")
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

## Notebook

`notebooks/example.py` is a [marimo](https://marimo.io/) notebook that runs PDA
on its own source, with controls for the configuration so the graph updates as the
parameters change. Launch it from the repository root so it can locate `src/`:

```bash
pip install -e ".[notebook]"          # installs marimo
marimo edit notebooks/example.py
```

## Development

```bash
uv run --extra dev pytest -q
uv run --extra dev python -m mypy        # strict, over src/pda
uv run --extra dev python -m pylint --rcfile=.pylintrc src/pda
```
