# Using PDA components

The two analyzers documented in the [README](../README.md#using-pda-from-python) —
`ModuleImportsAnalyzer` and `ModulesCollector` — are orchestrations. Each one runs the
same underlying steps in sequence: walk the filesystem, parse files to ASTs, read their
imports, resolve every name against a target environment, and assemble a graph.

Those steps are public components in their own right. If you only need to parse one module
to AST nodes, list the imports of a single file, resolve one name, or enumerate the Python
files under a directory, you can call the relevant component directly without building a
graph.

This document treats those components as an API. Every example is runnable and its output
is real; the sample input throughout is PDA's own source file
`src/pda/resolution/models/identity.py`, analysed from the repository root. The examples
assume PDA is importable (`pip install -e .`).

## The pipeline at a glance

| Concern | Component(s) | Input | Output |
| --- | --- | --- | --- |
| Filesystem tree | `build_path_tree`, `PathForest`, `gather_python_files` | path(s) | `PathNode` / `PathForest` / `list[Path]` |
| AST parsing | `parse_python_file`, `build_ast_tree`, `ASTForest` | `.py` file | `ast.Module` / `ASTNode` / `ASTForest` |
| Imports of one module | `ImportStatementParser` | `.py` file | `list[ImportStatement]` |
| Scopes & symbols | `ScopeAnalyzer` | `.py` file(s) | `ScopeForest` of `ScopeNode` / `Symbol` |
| Module resolution | `ModuleResolutionService` | name / path / `ImportPath` | `ModuleResolution` |
| Module collection | `ModulesCollector` | project root + root module | `ModuleGraph` |
| Import graph | `ModuleImportsAnalyzer` | entry paths | `ModuleGraph` |
| Rendering | `module_pyvis_converter`, `Graph.to_dict` | graph | HTML / node-link JSON |

## Shared conventions

Three base types recur across the components. Knowing their surface once is enough for all
of them.

**Node** (`AnyNode`) — a single tree node. Common members: `node.item` (the wrapped value),
`node.label`, `node.children`, `node.parent`, `node.root`, `node.ancestors`, `node.depth`.

**Forest** (`Forest`) — a set of trees keyed by their wrapped items. Iterating a forest
yields every node in level order; `forest.roots` is the set of root nodes; `forest[item]`
and `forest.get(item)` look a node up by its wrapped value; `forest.nx` is a
[NetworkX](https://networkx.org/) `DiGraph`; `forest.graph` is a structural `Graph`.

**Graph** (`Graph`) — a directed graph of nodes. `graph.to_dict()` produces the node-link
JSON described in the [README](../README.md#pda-output); `graph.save(path)` writes it to
disk; `graph.nodes` / `graph.edges` expose the underlying views; `graph.has_cycles`,
`graph.find_cycle()`, and `graph.find_cycles()` report cycles.

## Filesystem trees

`pda.models` turns a directory into a tree of `PathNode`s. Use it to inspect package layout
or to enumerate the Python files under a set of inputs.

```python
from pathlib import Path

from pda.models import build_path_tree, PathForest, gather_python_files

root = build_path_tree(Path("src/pda/parser"))
for child in sorted(root.children, key=lambda node: node.filepath.name):
    print(child.label, child.is_python_file, child.group)
```

```text
__init__.py True '.py'
parser.py True '.py'
```

`build_path_tree` returns a bare `PathNode`; wrapping the inputs in a `PathForest` also
marks directories as packages (`node.is_package`) and lets you pull out just the source
files:

```python
forest = PathForest([Path("src/pda/parser")])
print(sorted(str(path) for path in forest.get_python_files()))
```

`gather_python_files` is the convenience wrapper the CLI uses to expand entry-point
arguments — it accepts a single path or an iterable, walks directories recursively,
deduplicates overlapping inputs, drops non-Python files, and returns a sorted list:

```python
print(gather_python_files(Path("src/pda/parser")))
```

```text
[PosixPath('.../src/pda/parser/__init__.py'), PosixPath('.../src/pda/parser/parser.py')]
```

**Key members** — `PathNode`: `.filepath`, `.is_file`, `.is_dir`, `.is_python_file`,
`.is_package`, `.has_init`. `PathForest`: `.get_python_files()`, `.graph` (a `PathGraph`),
plus the shared forest API.

## AST parsing

`pda.parser` reads a file to a standard-library `ast.Module`; `pda.models` wraps that AST in
`ASTNode`s that carry a readable label, a group, and a fully qualified name.

```python
from pda.parser import parse_python_file
from pda.models import build_ast_tree

tree = parse_python_file("src/pda/resolution/models/identity.py")
node = build_ast_tree(tree)
print(node.label, node.type.__name__)
print([child.label for child in node.children])
```

```text
Module Module
['ImportFrom(__future__)', 'ImportFrom(dataclasses)', 'ImportFrom(typing)', 'ImportFrom(pda.constants)', 'ClassDef(ModuleIdentity)']
```

For more than one file, or when you want to walk every node and recover which file it came
from, use `ASTForest`. It accepts file paths, `PathNode`s, or already-built `ASTNode`s:

```python
from pda.models import ASTForest

forest = ASTForest(["src/pda/resolution/models/identity.py"])
for node in forest:
    if node.type.__name__ == "FunctionDef":
        print(node.fqn)
```

```text
ModuleIdentity.parts
ModuleIdentity.public_fqn
ModuleIdentity.parent_name
ModuleIdentity.top_level_name
```

`forest.get_origin(node)` returns the source file a node's tree was parsed from.

**Key members** — `ASTNode`: `.ast` (the wrapped `ast.AST`), `.type`, `.label`, `.fqn`,
`.details`, `.group`. `ASTForest`: `.get_origin()`, `.root_origins`, `.graph` (an
`ASTGraph`). Helpers: `get_ast(node)` (accepts an `ASTNode` or a raw `ast.AST` and returns
the `ast.AST`), `ast_label`, `ast_dump`, `ast_group`.

> The `.fqn` here is a lexical prefix built from enclosing `name` attributes. It does not
> yet model Python's full `__qualname__` rules — see [Fully qualified names](#fully-qualified-names-planned).

## Imports of a single module

`ImportStatementParser` parses one file and returns an `ImportStatement` per imported name,
each carrying the parsed `ImportPath`, the source span, and the scopes the import executes
in.

```python
from pda.analyzer import ImportStatementParser

for statement in ImportStatementParser()("src/pda/resolution/models/identity.py"):
    print(str(statement.path), statement.span.lineno, statement.scopes)
```

```text
__future__.annotations 1 []
dataclasses.dataclass 3 []
typing.Optional 4 []
typing.Tuple 4 []
pda.constants.DELIMITER 6 []
```

`scopes` is empty for module-level imports. Imports nested inside branches, loops, or
definitions carry an `ImportScope` flag per enclosing construct, innermost first. Given a
file with `import sys` under an `if`, `import json` inside a function, and a
`TYPE_CHECKING`-guarded import, the parser reports:

```text
sys          scopes=[<ImportScope.IF: 1>]
json         scopes=[<ImportScope.FUNCTION: 4096>]
OrderedDict  scopes=[<ImportScope.IF|TYPE_CHECKING: 32769>]
```

Use `statement.in_scope(ImportScope.TYPE_CHECKING)` to test membership; it matches when any
of the statement's scopes contain the requested flag.

`ImportPath` is the parsed shape of an import target and is useful on its own:

```python
from pda.specification import ImportPath

absolute = ImportPath.from_string("pda.resolution.models")
print(absolute.parts, absolute.base, absolute.relative, absolute.top_level)

relative = ImportPath.from_string("..models.identity", is_module=False)
print(str(relative), relative.level, relative.module, relative.name)
```

```text
['pda', 'resolution', 'models'] pda False pda
..models.identity 2 models identity
```

**Key members** — `ImportStatement`: `.origin`, `.span`, `.path`, `.scopes`, `.in_scope()`.
`ImportPath`: `.module`, `.level`, `.name`, `.asname`, `.parts`, `.base`, `.absolute`,
`.relative`, `.top_level`, and the constructors `from_string`, `from_ast`, `from_path`.
`SourceSpan`: `.lineno`, `.col_offset`, `.end_lineno`, `.end_col_offset`.

## Scopes and symbols

`ScopeAnalyzer` builds the scope hierarchy for one or more files and populates each scope's
symbol table. It orchestrates two collaborators you can also use directly — `ScopeBuilder`
(creates the scope structure) and `SymbolCollector` (extracts symbol definitions) — but for
most uses a single call is enough.

```python
from pda.analyzer import ScopeAnalyzer

forest = ScopeAnalyzer()(["src/pda/resolution/models/identity.py"])
for scope in forest:
    print(scope.scope_type.value, repr(scope.fqn), list(scope.symbols))
```

```text
module       '' ['annotations', 'dataclass', 'Optional', 'Tuple', 'DELIMITER', 'ModuleIdentity']
class        'ModuleIdentity' ['name', 'parts', 'public_fqn', 'parent_name', 'top_level_name']
function     'ModuleIdentity.parts' ['self']
function     'ModuleIdentity.public_fqn' ['self']
...
```

Each scope's `symbols` maps a name to a `Symbol`, and `scope.lookup(name)` walks the scope
chain following Python's LEGB rule:

```python
module_scope = next(iter(forest.roots))
symbol = module_scope.symbols["ModuleIdentity"]
print(symbol.kind.value, symbol.span.lineno, symbol.fqn)
print(module_scope.lookup("ModuleIdentity").fqn)
```

```text
class 10 ModuleIdentity
ModuleIdentity
```

**Key members** — `ScopeNode`: `.scope_type`, `.symbols`, `.imports`, `.fqn`,
`.lookup(name)`, `.lookup_local(name)`. `Symbol`: `.fqn`, `.kind` (a `SymbolKind`: `module`,
`class`, `function`, `variable`), `.span`, `.origin`, `.node`. `ScopeForest` is a forest of
module-scope roots.

## Module resolution

Resolution is the policy layer that maps a name, a filesystem path, or an `ImportPath` to a
module identity, kind, and category. `ModuleResolutionService` is the public facade; it
takes a `TargetEnvironment`, which you usually build through `ProjectResolutionContext`.

```python
from pathlib import Path

from pda.resolution import ProjectResolutionContext, ModuleResolutionService

context = ProjectResolutionContext.create(
    Path("."),
    source_roots=(Path("src"),),
    local_boundary=Path("."),
)
service = ModuleResolutionService(context.environment)

for name in ("pda.resolution", "pda.resolution.models.identity", "os", "nonexistent_pkg"):
    resolution = service.resolve_name(name)
    print(name, resolution.status.value, resolution.kind.value, resolution.category.value)
```

```text
pda.resolution                 resolved    regular_package  local
pda.resolution.models.identity resolved    source_module    local
os                             resolved    frozen           stdlib
nonexistent_pkg                unavailable unknown          unknown
```

Kind (the Python primitive: source module, regular/namespace package, builtin, frozen…) and
category (local / stdlib / external / unknown) are independent axes, which is why `os`
resolves as `frozen` **and** `stdlib`. A failed resolution carries a typed `diagnostic`
rather than raising.

The service also resolves filesystem paths and import paths:

```python
resolution = service.resolve_filesystem_path("src/pda/resolution/models/identity.py")
print(resolution.identity.name, resolution.category.value)
```

```text
pda.resolution.models.identity local
```

To resolve the imports written *inside* a file, obtain a `SourceModuleContext` for it first
and pass parsed `ImportPath`s to `resolve_import_path`:

```python
context_for_file = service.source_context("src/pda/resolution/models/identity.py")
resolution = service.resolve_import_path(context_for_file, ImportPath.from_string(".location"))
print(resolution.status.value, resolution.identity.name)
```

```text
resolved pda.resolution.models.location
```

A `from .helper import util` form — where the name could be either a submodule or an
exported object — resolves to `ambiguous`, with both candidates recorded in
`resolution.alternatives`.

For resolution against the running interpreter instead of a project, use
`RuntimeModuleLookup.create()` (from `pda.analyzer.modules.lookup`); its `.resolver` is a
`ModuleResolutionService` bound to a runtime `TargetEnvironment`.

**Key members** — `ModuleResolutionService`: `.resolve_name()`, `.resolve_filesystem_path()`,
`.resolve_import_path()`, `.source_context()`, `.to_categorized_module()`, `.environment`.
`ModuleResolution`: `.status` (`ResolutionStatus`), `.kind` (`ModuleKind`), `.category`
(`ModuleCategory`), `.identity`, `.location`, `.diagnostic`, `.resolved`, `.mode`
(`ResolutionMode`).

## Module collection scanners

`ModulesCollector` (see the [README](../README.md#using-pda-from-python)) assembles a
containment graph. Below it sit two scanners you can use to enumerate modules yourself.

`FileSystemScanner` lists the submodule files of a package directory and converts a file to
its import path relative to a source root:

```python
from pathlib import Path

from pda.analyzer import FileSystemScanner

scanner = FileSystemScanner(project_root=Path("."), source_roots=(Path("src"),))
print([path.name for path in scanner.get_submodule_paths(Path("src/pda/parser"))])
print(str(scanner.path_to_import_path(Path("src/pda/resolution/models/identity.py"), Path("src"))))
```

```text
['parser.py']
pda.resolution.models.identity
```

`PkgModuleScanner` discovers installed top-level packages under a set of search paths
(external roots, stdlib roots, `sys.path`); `ModulesCollector` uses it to seed stdlib and
external modules.

## Rendering

Any `Graph` serialises to node-link JSON with `graph.to_dict()` / `graph.save(path)`.
`ModuleGraph`s additionally render to a self-contained interactive HTML view through
`module_pyvis_converter`:

```python
from pda.models import module_pyvis_converter

converter = module_pyvis_converter(theme="dark")
html = converter(module_graph, html=True)
```

`module_pyvis_converter` accepts `theme` (`"light"` / `"dark"`), `layout`
(`"hierarchical"` / `"package_ring"`), and pass-through `network_kwargs` / `vis_options`.

## Fully qualified names (planned)

A dedicated component for computing Python-accurate fully qualified names is in development
on the `fqn` branch and is **not yet shipped**. The intended behaviour is to reproduce the
`__qualname__` the interpreter assigns to each definition — including the `<locals>` and
`<lambda>` tokens that mark a name as non-importable — so that a definition's runtime FQN
(`f"{module}.{qualname}"`) can be derived statically. The ground-truth corpus for this work
lives in `tests/examples/names/qualnames.py`.

Until then, the `.fqn` properties on `ASTNode`, `ScopeNode`, and `Symbol` provide a simpler
lexical prefix: they join the `name` attributes of enclosing definitions and do not model
`<locals>`, `<lambda>`, or decorator rewrites.
