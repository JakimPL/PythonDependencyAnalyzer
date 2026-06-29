# Module Resolution Policy

Status: draft for review

This document defines how PDA should understand Python modules, packages,
namespace packages, import paths, and fully qualified names. It is intentionally
written as a design document before implementation. The goal is to make future
changes to module resolution principled, testable, and aligned with Python's
import machinery.

## Why This Policy Exists

PDA analyzes Python projects without necessarily importing the analyzed project
as an installed distribution. That means PDA must answer questions that are
similar to Python's import system, but not always identical:

- What module does this import statement refer to?
- What module name belongs to this filesystem path?
- Is this module local to the analyzed project, part of the standard library,
  external, or unavailable?
- Which modules and submodules should be scanned recursively?
- What fully qualified name should be attached to a module or symbol?

These questions currently appear in several parts of the codebase. That is a
signal that "module resolution" is an explicit domain concept, not an incidental
helper. A robust design should centralize the policy while still allowing
different analyzers to ask different use-case questions.

The motivating failure case is a project containing a top-level `tests` package
or namespace package while another repository or installed distribution also
exposes `tests`. In a notebook or long-lived interpreter, `import tests` may
resolve to the wrong project because of ambient `sys.path`, `sys.modules`, or
both. PDA should not accidentally inherit that ambiguity when it is scanning a
specific target project.

## Design Goals

PDA's resolution policy should satisfy these goals:

1. Align with Python's concepts of modules, regular packages, namespace
   packages, module specs, package paths, and relative imports.
2. Distinguish the target project environment from the interpreter running PDA.
3. Avoid duplicate resolution rules scattered across analyzers and
   specifications.
4. Make every resolution result explainable: which name, path, root, category,
   and spec source produced it.
5. Support filesystem-first scans for local project inventory.
6. Support import-semantics scans for dependency analysis.
7. Avoid executing analyzed project code or populating `sys.modules` as a side
   effect of static analysis.
8. Keep tests deterministic across Python versions and machines by using
   synthetic temporary package layouts rather than depending on installed
   packages.
9. Preserve enough information to support later symbol-resolution and function
   call-graph analysis.

## Python Model PDA Should Respect

Python has one module object concept. Packages are modules that can contain
submodules because they have a package search path. Regular packages are usually
directories with `__init__.py`. Namespace packages are packages without a single
`__init__.py`; they can be composed from multiple portions found in different
locations.

Python import search starts with a fully qualified module name. For a dotted
name such as `foo.bar.baz`, Python resolves the parent path first: `foo`, then
`foo.bar`, then `foo.bar.baz`. Submodules are searched using the parent
package's path, not by restarting every component from the global import path.

Runtime imports also consult `sys.modules` first. If a module name is already
present there, the cached module may satisfy the import before any filesystem
search occurs. That is correct runtime behavior, but it is often the wrong
default for PDA's static project analysis.

`importlib.util.find_spec()` is a runtime-oriented convenience API. It consults
the import system and may return `sys.modules[name].__spec__`. For submodules,
it can import the parent module. This makes it useful for "what would this
interpreter import now?" checks, but risky as the sole primitive for static
analysis of another project.

`importlib.machinery.PathFinder.find_spec(fullname, path)` is closer to the
path-based part of Python's import machinery. It can search `sys.path` for
top-level names or a specific package path for submodules. PDA should prefer
this lower-level primitive when it needs deterministic resolution against an
explicit target environment.

## Terminology

### Module Name

A module name is a Python dotted name such as `pda.analyzer.modules.collector`.
PDA should use `DELIMITER` for module-name splitting and joining. The delimiter
belongs to Python module names; it is not the same concept as a filesystem file
extension separator.

### Fully Qualified Name

A fully qualified name, or FQN, is the complete dotted identity of a module or a
symbol relative to the importable Python namespace. For modules, the FQN is the
module name without implementation-only suffixes such as `.__init__`. For
symbols, the FQN is the containing module FQN plus the lexical scope path plus
the symbol name.

### Import Path

An import path is PDA's parsed representation of an import statement target. It
may be absolute, such as `import pda.config`, or relative, such as
`from ..models import ModuleGraph`. An import path is not necessarily already a
resolved module. It may point to a module, a package, a symbol inside a module,
or an unavailable target.

### Origin

An origin is the location or marker associated with a resolved module spec. For
source modules it is usually a `.py` file. For regular packages it is usually
the package's `__init__.py`. For namespace packages it is typically absent,
while package search locations identify the namespace portions. Built-in and
frozen modules use non-filesystem origin markers.

### Module Spec

A module spec is Python's import-system description of how a module would be
loaded. PDA should treat a spec as evidence from a resolver, not as the only
source of module identity. A known local filesystem path can produce a module
identity even when runtime `find_spec()` would choose a different already-loaded
module.

### Project Root

The project root is the local boundary of the analyzed project. It is used for
categorization: files under this boundary are local. The project root is not
automatically the same thing as an import search root.

Example: in a `src` layout, the project root may be the repository directory,
while the source root is `project_root/src`.

### Source Root

A source root is a filesystem directory that contributes top-level importable
modules for the target project environment. PDA should resolve local project
imports against source roots before external paths. A project may have zero,
one, or many source roots.

### Local Boundary

The local boundary is the set of paths considered part of the analyzed project.
Usually this is the project root. It may be broader than source roots because a
repository can contain tests, notebooks, scripts, and package code in separate
locations.

### Target Import Environment

The target import environment is the ordered search context PDA uses to answer
"what does this project import?" It should be explicit and reproducible:
configured source roots first, then configured or discovered external roots,
then standard-library roots as appropriate. It is not simply the current
process's ambient `sys.path`.

## Policy Overview

PDA should resolve modules through one central resolution service. That service
may expose different methods for different use cases, but those methods must
share the same vocabulary, result type, and categorization rules.

The central result should represent a resolved module candidate. It should
include at least:

- requested name or import path;
- resolved module name;
- containing package context, if any;
- origin, if any;
- origin type;
- submodule search locations;
- category;
- source root or external root that matched, if any;
- whether the result came from runtime import semantics or filesystem identity;
- error information when unavailable.

The `Module` model should represent resolved facts. It should not perform new
global module searches from properties such as `spec` or `base_path`. If a spec
or base path is needed later, it should come from the resolution result or be
derived deterministically from stored facts.

### Specification Versus Helper Types

PDA should distinguish durable domain facts from implementation helpers.

A type belongs in `pda.specification` when it is a stable PDA fact that may cross
analyzer boundaries, be stored in graph-facing models, appear in output, or be
consumed by later analysis phases. Specification types should describe facts
already known to PDA. They should not perform ambient resolution, mutate runtime
state, or depend on the current interpreter beyond values captured at creation
time.

A type belongs outside `pda.specification` when it is transient machinery for a
specific subsystem: candidate state, lookup results, factories, traversal
state, parser helpers, or DTOs used only to move data between collaborators.
These helper types may be public within their subsystem, but they should not be
presented as stable PDA facts.

Examples:

- `Module`, `ImportPath`, `ImportStatement`, `SourceSpan`, and
  `NamespacePortion` are specification facts.
- `ModuleLocation`, `ModuleResolution`, `SourceModuleContext`, and
  `TargetEnvironment` are resolution-layer facts or query context.
- `ModuleCoordinates`, `FilesystemModuleLookup`, `PendingNode`, parser scope
  helpers, and builder/factory classes are implementation helpers.

## Essential Primitive Types

The following primitive concepts should be specified before implementation. The
names below describe roles; exact class names can change during refactoring.

### Module Identity

Module identity is the importable dotted name of a module. It is the stable key
used by Python import semantics and by PDA graphs.

Required fields:

- module name;
- public module FQN;
- parent package name, if any;
- top-level import name.

Rules:

1. The module name uses `DELIMITER`.
2. `__init__` is an implementation detail of a package file, not part of the
   public package FQN.
3. A module identity does not imply that the module is available, readable, or
   local.

### Module Location

Module location describes where the module came from.

Required fields:

- origin, if there is a single origin;
- origin type;
- submodule search locations;
- source root or external root that matched, if known.

Rules:

1. A source module normally has a `.py` origin.
2. A regular package normally has an `__init__.py` origin and a submodule search
   location.
3. A namespace package has no single origin and one or more submodule search
   locations.
4. Built-in and frozen modules have non-filesystem origins.

### Module Kind

Module kind describes the Python primitive represented by the module:

- source module;
- regular package;
- namespace package;
- built-in module;
- frozen module;
- extension module;
- unknown or unavailable module.

Module kind is independent from category. A namespace package can be local,
external, or mixed. A regular package can be local or external. A built-in
module is usually standard library.

### Module Category

Module category describes PDA's relationship to the resolved module:

- local;
- standard library;
- external;
- unknown.

Category is an analyzer-facing classification. It should be derived from module
location, local boundary, standard-library knowledge, and resolution errors. It
should not replace module kind.

### Module Resolution

Module resolution is the result of attempting to answer a question about a
module name, import path, or filesystem path.

Required fields:

- requested input;
- resolution mode;
- resolved module identity, if available;
- module location, if available;
- module kind;
- category;
- availability;
- ambiguity or error reason, if any.

Rules:

1. Resolution is a first-class result, not just a `Module` or exception.
2. Unavailable modules should still preserve the requested input and error
   reason.
3. Ambiguous results should be representable without pretending they are fully
   resolved.

### Source Module Context

Source module context is the anchor used to resolve relative imports and symbol
FQNs.

Required fields:

- source module identity;
- source module location;
- containing package context;
- source root;
- local boundary;
- target import environment.

This replaces the overloaded use of `package` as both an analysis target and a
relative-import anchor.

### Scope Identity

Scope identity describes a lexical Python scope inside a source module.

Required fields:

- containing module identity;
- scope kind;
- lexical parent scope;
- defining AST node;
- source span;
- stable local scope path.

Rules:

1. Module scopes are anchored by resolved module identity, not only by file path.
2. Class and function scope paths should follow Python's lexical nesting model.
3. Lambda and comprehension scopes need stable generated names or node ids
   because Python source does not give them importable names.
4. Scope identity is not the same as runtime object identity. A function can be
   rebound, assigned through aliases, or returned from another function.

### Symbol Binding

A symbol binding records that a name is bound in a scope.

Required fields:

- local name;
- binding kind;
- defining AST node;
- defining scope identity;
- source span;
- resolved target, if known;
- confidence or resolution status.

Binding kinds should include at least:

- function definition;
- async function definition;
- class definition;
- import binding;
- assignment;
- parameter;
- loop target;
- with target;
- exception alias;
- pattern-match target;
- global declaration;
- nonlocal declaration;
- unknown or unsupported binding.

Rules:

1. Import bindings must retain both the local name and the resolved imported
   target.
2. Assignments should initially create local bindings even when their runtime
   value cannot be resolved.
3. `global` and `nonlocal` change the target scope of later bindings and cannot
   be treated as ordinary local assignments.
4. A binding can have a lexical FQN even when its runtime value is unknown.

### Name Reference

A name reference records a use of a name or attribute expression.

Required fields:

- referenced syntax;
- containing scope identity;
- source span;
- candidate binding or bindings;
- confidence or resolution status.

Rules:

1. `Name` references should be resolved through Python's lexical lookup rules as
   closely as possible.
2. Attribute references such as `pkg.mod.func` should be represented as a chain,
   not flattened immediately, because each prefix can resolve differently.
3. Unresolved references are expected in dynamic Python and must remain
   explainable.

### Call Site

A call site records a syntactic function or callable invocation.

Required fields:

- containing module identity;
- containing scope identity;
- caller symbol, if known;
- callee expression;
- source span;
- candidate callee symbols or modules;
- confidence or resolution status.

Rules:

1. Call extraction is syntactic; call resolution is semantic.
2. The graph should allow multiple candidate callees for one call site.
3. Dynamic calls must be represented as unresolved or partially resolved rather
   than dropped silently.
4. Calls at module top level have the module as caller context, not a function
   caller.

## Resolution Modes

PDA has at least three legitimate resolution modes. They must be explicit.

Spec discovery is allowed in static analysis. The boundary is code execution
and runtime module-cache dependence. A path-based finder may inspect filesystem
entries and return a `ModuleSpec` without executing the target module. A runtime
import, or a convenience API that imports parent packages or trusts
`sys.modules`, belongs to runtime resolution unless explicitly requested.

### Project Resolution

Project resolution answers: "What module would this target project environment
resolve?"

Rules:

1. Search explicit source roots before external roots.
2. Use Python's parent-path traversal for dotted names.
3. Do not let `sys.modules` override the target environment.
4. Do not execute target project code or populate `sys.modules` as a side
   effect.
5. Use `PathFinder.find_spec()` or an equivalent path-based mechanism against
   explicit paths.
6. Preserve namespace package portions instead of collapsing them to a fake
   single origin.
7. Fall back to built-in/frozen recognition where appropriate.

This should be the default mode for import dependency analysis.

### Filesystem Resolution

Filesystem resolution answers: "What module identity does this known local path
represent?"

Rules:

1. Start from a known filesystem path and a selected source root or local root.
2. Derive the module name by relative path conversion.
3. Use `DELIMITER` to join module-name components.
4. Treat `__init__.py` as the package module for its directory.
5. Treat a directory without `__init__.py` as a namespace package portion only
   when policy permits namespace packages in that location.
6. Do not ask runtime import discovery to rediscover the same name before
   creating the local module identity.
7. Use runtime specs only as optional compatibility evidence, not as the source
   of truth.

This should be the default mode for collecting local project modules from the
filesystem.

### Runtime Resolution

Runtime resolution answers: "What would the interpreter running PDA resolve
right now?"

Rules:

1. It may consult `sys.modules`.
2. It may use `importlib.util.find_spec()`.
3. It may import parent packages as Python's convenience APIs do.
4. It must be opt-in for static analysis because it can observe notebook state,
   test-runner state, editable installs, and unrelated repositories.

This mode is useful for diagnostics and compatibility checks, but should not be
the default for project-local analysis.

### Environment Resolution

Environment resolution answers: "What modules are visible in the current Python
environment?"

This mode may use runtime import machinery, `sys.modules`, package metadata,
`pkgutil`, and importlib. It is appropriate for standard-library and external
inventory, where exact static scanning of all possible packages is not
realistic. It must still report when a module cannot be read or safely scanned.

Environment resolution is allowed to observe interpreter state. Project
resolution should not silently inherit that state unless the user asks for this
mode.

## Import Path Resolution Policy

Import path resolution starts from a source module context. The source module
context must provide:

- source module FQN;
- source module origin;
- source module containing package context;
- source root;
- local boundary;
- target import environment.

Absolute import paths are resolved from the target environment's top-level
search roots.

Relative import paths are first absolutized against the source module context:

1. Determine the containing package of the source module.
2. Apply the relative level to find the parent package.
3. Join remaining module components using `DELIMITER`.
4. If the relative import escapes the containing package, the result is
   unavailable with a resolution error.
5. Resolve the resulting absolute module name using project resolution.

`import x.y` and `from x import y` are not equivalent in all cases. PDA should
preserve the parsed shape long enough to decide whether `y` is expected to be a
submodule, an object exported by `x`, or ambiguous. When static analysis cannot
distinguish an exported object from a submodule without executing code, it
should record the ambiguity explicitly rather than silently pretending both are
the same.

## Filesystem Name and FQN Policy

When deriving a module FQN from a path:

1. Choose the source root that makes the path importable.
2. Compute the relative path from that source root.
3. Remove only recognized Python module suffixes from file modules.
4. Convert path components to module-name components with `DELIMITER`.
5. If the last component is `__init__`, remove it from the public module FQN.
6. For a package directory, the FQN is the directory's relative path.
7. For a namespace package portion, the FQN is also the directory's relative
   path, but the result has no single origin file.

When deriving a symbol FQN:

1. Start with the containing module FQN.
2. Append lexical scope components for classes, functions, and nested scopes
   that PDA models as part of the symbol identity.
3. Append the symbol name.
4. Use `DELIMITER` for the final FQN string.

Open point: PDA should decide whether local variables inside functions should
receive public-looking FQNs, internal scope FQNs, or a separate qualified symbol
path. The policy should not let module-resolution changes accidentally define
symbol semantics.

## Symbol and Call-Graph Readiness

PDA's long-term goal includes function call graphs. Module resolution should
therefore produce enough context for later symbol and call analysis. The
pipeline should be staged so each stage owns a clear type of fact:

1. Parse source files into ASTs.
2. Attach each AST module to a resolved source module context.
3. Build lexical scopes and symbol bindings.
4. Resolve imports into import bindings.
5. Resolve name references against lexical scopes and import bindings.
6. Extract call sites from AST.
7. Resolve call sites to candidate callees when possible.
8. Build a call graph with confidence and unresolved-edge metadata.

An AST by itself cannot provide a correct module FQN. The AST knows lexical
structure and source locations, but not the importable module name of the file
that contains it. PDA must attach module identity before finalizing symbol FQNs.

### Symbol FQN Policy

Symbol FQNs should be modeled in two layers:

1. Lexical FQN: module FQN plus lexical scope path plus local name.
2. Runtime target FQN: the resolved object or module that a binding/reference
   points to, when known.

For definitions that naturally create named Python objects, such as modules,
classes, functions, and async functions, the lexical FQN should be close to
Python's module plus qualified-name model.

For ordinary local variables, parameters, loop targets, exception aliases, and
pattern-match targets, Python does not provide importable object FQNs. PDA may
still assign stable lexical FQNs for analysis, but these should not be confused
with importable runtime names.

Examples:

```text
module: pda.example
function: pda.example.outer
nested function: pda.example.outer.inner
class method: pda.example.Widget.render
local variable: pda.example.outer.<locals>.value or an equivalent internal path
```

Open point: the exact spelling for internal local scope components, such as
`<locals>`, lambdas, and comprehensions, should be chosen once and tested. The
important rule is that internal symbol paths are stable and clearly marked as
non-importable when they are not valid module-level names.

### Import Binding Policy

Imports create bindings in the current scope. PDA should preserve the local
binding shape and the resolved target separately.

Examples:

```python
import package.module as alias
from package import module
from package.module import function as local_function
```

These may create local names `alias`, `module`, and `local_function`, but their
targets can be modules, symbols exported by modules, or unresolved/ambiguous
objects. A later call such as `local_function()` should resolve through the
local binding, not by reparsing the text of the original import statement.

When a `from package import name` target cannot be proven to be a submodule
without executing code, PDA should keep the ambiguity:

- `name` may be a submodule;
- `name` may be an object assigned or exported by `package`;
- `name` may be unavailable in the target environment.

### Call Resolution Policy

Call graph analysis should distinguish syntactic call extraction from semantic
callee resolution.

The AST can reliably identify call sites such as:

```python
func()
module.func()
obj.method()
factory()()
callbacks[name]()
```

It cannot always determine the runtime callee. PDA should resolve calls in
tiers:

1. Direct lexical functions in the same module.
2. Imported functions or modules with known bindings.
3. Attribute calls on known modules or classes.
4. Methods where the receiver type can be inferred from local construction or
   simple assignments.
5. Dynamic, unknown, or multiple candidate callees.

The call graph should preserve unresolved and partially resolved calls. Dropping
them would make the graph look more certain than the analysis allows.

### Python Machinery for Symbol Analysis

PDA should prefer Python's own parser and symbol-table machinery where it helps
without executing code. The standard `ast` module provides syntax and source
locations. The standard `symtable` module can expose scope and binding
information without running the analyzed module. These tools should inform PDA's
scope model, but PDA still needs its own module identity, import resolution,
and cross-module binding model.

## Category Policy

Categories describe PDA's relationship to a resolved module, not merely where
Python found it.

### Local

A module is local if its origin or namespace portion is under the configured
local boundary. A module discovered by filesystem resolution under a local
source root is local even if runtime import discovery would choose another
module with the same name.

### Standard Library

A module is standard library if it is resolved as part of the Python standard
library or identified by Python's standard-library module metadata. Built-in and
frozen modules can be standard-library modules even when they do not have a
source file to scan.

### External

A module is external if it resolves outside the local boundary and is not
standard library. External does not necessarily mean installed via a package
manager; another checkout on the import path is external relative to the target
project.

### Unknown

A module is unknown when PDA cannot resolve it, when resolution is ambiguous in
a way the current policy cannot represent, or when validation fails. Unknown
should preserve enough error context for diagnostics.

## Namespace Package Policy

Namespace packages need explicit handling because they are not a single file and
may be made from multiple portions.

Rules:

1. A namespace package may have multiple search locations.
2. Each location should be represented as a `NamespacePortion` specification
   fact that retains its relationship to local, external, or stdlib roots.
3. If any portion is local, PDA may categorize the namespace package as local
   for local scanning, but it should preserve non-local portions explicitly.
4. Scanning local modules should recurse into local namespace portions.
5. Import dependency analysis should resolve submodules using all portions that
   participate in the target environment, ordered by the target environment.
6. A regular package with `__init__.py` found later on an import path can
   prevent creation of a top-level namespace package in normal Python import
   behavior. PDA's filesystem collection mode may still represent a local
   namespace portion, but project import resolution must state whether that
   namespace portion is actually importable in the target environment.

This distinction is important. "Exists under the project tree" and "wins during
Python import resolution" are different facts.

Example of mixed namespace portions:

```text
project_root/
    src/
        acme/
            local_mod.py

site-packages/
    acme/
        external_mod.py
```

If neither `acme/` directory has `__init__.py`, and both `project_root/src` and
`site-packages` participate in the target environment, Python can treat `acme`
as one namespace package with two portions. The `acme` namespace is partly local
and partly external, while `acme.local_mod` is local and `acme.external_mod` is
external. If PDA is only scanning paths under the local boundary, it should not
pretend the external portion is local, but it may need to remember that the
namespace has more than one portion for import resolution.

## Source Roots and Project Roots

PDA should stop assuming that the project root is always a source root.

Examples:

```text
flat layout:
project_root/
    mypkg/
        __init__.py

source roots: [project_root]
local boundary: project_root
```

```text
src layout:
project_root/
    src/
        mypkg/
            __init__.py
    tests/

source roots: [project_root / "src"]
local boundary: project_root
```

```text
multi-root layout:
project_root/
    packages/
        app/
            app_pkg/
        lib/
            lib_pkg/

source roots:
    project_root / "packages" / "app"
    project_root / "packages" / "lib"
local boundary: project_root
```

The CLI accepts `project_root` and a root module name. Internally PDA uses a
normalized `ProjectResolutionContext` with explicit source roots and a local
boundary, and an `AnalysisTarget` for the import root being examined.

The current public API and README examples use `project_root` as an import
search root:

```bash
pda analyze src pda
pda collect src pda
```

In these examples, `src` is functionally a source root. To avoid breaking users,
the existing argument remains accepted and is interpreted as the default source
root. Workflows that need repository-level classification can pass the
repository as `project_root` and use `--source-roots`:

```bash
pda analyze src pda
# source roots: [src]
# local boundary: src by default

pda analyze . pda --source-roots src
# source roots: [./src]
# local boundary: repository root
```

`--local-boundary` can override the classification boundary when it should differ
from the project root. Explicit `source_roots` take precedence over any future
layout inference.

When an analyzer has an `AnalysisTarget`, omitted entry paths should be derived
from that target rather than from the whole source root. A target may resolve to
a source module file, a regular package directory, or one or more local
namespace package portions.

## Expected Resolver Responsibilities

The public resolver should be a facade over focused resolution services. It
should coordinate the following use cases:

- module-name resolution;
- import-path resolution from source context;
- filesystem-path-to-module identity;
- source module context lookup;
- unavailable result creation;
- namespace portion representation.

Focused collaborators should own the repeated lower-level responsibilities:

- target search path construction;
- Python `ModuleSpec` lookup;
- import-path absolutization and candidate module names;
- filesystem source-root identity;
- module kind and dependency category classification;
- conversion to compatibility models such as `Module` and `CategorizedModule`.

Recursive filesystem pruning is a scanner responsibility. PDA can keep using
tree-oriented structures such as `PathForest`/`PathNode` when collecting files,
while single-path resolution may use lighter path helpers that implement the
same package-like directory rule.

The resolver should not own:

- graph traversal;
- import statement parsing;
- AST scope construction;
- local lexical name lookup;
- visualization labels;
- analyzer-specific depth policy.

Analyzer code should ask the resolver questions, then decide how to traverse or
present the answers.

## Expected Model Responsibilities

`Module` should own:

- resolved module name;
- origin and origin type;
- submodule search locations;
- module type;
- metadata captured at resolution time.

`Module` should not own:

- global import discovery;
- mutation of `sys.path`;
- categorization against a changing project root;
- `ModuleSpec` reconstruction or lazy recomputation from ambient interpreter
  state.

`ModuleSource` should describe the source file and source root context only. It
may derive path-based names such as the relative import path or top-level source
name, but it should not expose `get_spec`, `get_package_spec`, or `module`
helpers that perform resolution. Source files become resolved modules through a
`SourceModuleContext` created by the resolution layer.

`ImportResolver` is an analyzer adapter for import dependency analysis. It
translates `ModuleSource` and parsed `ImportPath` values into central
`ModuleResolutionService` queries. It should not grow module-resolution policy
that belongs in the central resolution layer.

Runtime/environment collection should also use `ModuleResolutionService`, but
with a runtime target environment that has no source roots or local boundary and
does include the active interpreter search path. Specification models should not
offer factory methods that perform ambient `find_spec` lookup.

Scope and symbol models should own lexical facts:

- scope kind and lexical parent;
- symbols bound in a scope;
- source spans for definitions and references;
- lexical FQNs or stable internal symbol paths.

Scope and symbol models should not own cross-module import resolution directly.
They should reference resolver results or binding results produced by a separate
resolution phase.

## Caching Policy

PDA may cache resolution results, but the cache key must include the target
environment:

- ordered source roots;
- local boundary;
- external roots, if configured;
- Python executable or stdlib identity when stdlib detection matters;
- resolution mode;
- validation options.

A cache keyed only by module name is not safe. The same name can resolve
differently under different source roots or after a notebook mutates `sys.path`.

## Error and Ambiguity Policy

Resolution failures should be first-class results, not only warnings.

Unavailable results should distinguish:

- module not found;
- relative import escaped package;
- source file outside source root;
- non-Python origin;
- namespace package without scan-eligible local portions;
- ambiguous exported object vs submodule;
- import system error;
- validation error.

Warnings are useful for user-facing diagnostics, but internal control flow
should use typed results or errors.

## Test Policy

Tests for this area should avoid relying on the host Python environment except
where the test is explicitly about built-in or standard-library behavior.

Use temporary package layouts for:

- flat local package;
- `src` layout;
- duplicate package name in two roots;
- local package shadowing external package;
- external package shadowing local package when source roots are not configured;
- namespace package with one local portion;
- namespace package with local and external portions;
- regular package competing with namespace portion;
- dotted submodule through parent package path;
- relative import within package;
- relative import escaping package;
- loaded wrong module in `sys.modules`;
- missing module;
- built-in module;
- frozen module if stable for the running Python version.

Use source snippets for symbol and call-graph tests:

- module-level function calling another module-level function;
- nested function calling an enclosing-scope function;
- class method calling another method through `self`;
- imported function called directly;
- imported module attribute call;
- alias imports;
- local reassignment shadowing an imported name;
- `global` and `nonlocal` bindings;
- lambda and comprehension scopes;
- dynamically indexed or attribute-computed calls that must remain unresolved.

Assertions should target PDA policy results:

- resolved name;
- origin or absence of origin;
- search locations;
- category;
- source root/local boundary match;
- unavailable reason;
- FQN.
- lexical binding target;
- call-site caller context;
- candidate callee set;
- resolution confidence or unresolved reason.

Avoid asserting exact installed package inventories, exact stdlib filesystem
layouts, or Python-version-specific frozen-module sets.

## Open Decisions

These should be resolved before implementation:

1. How should users configure source roots?
   - Decision: keep the current positional path as a backward-compatible default
     source root.
   - Add explicit `source_roots` API/CLI configuration for one or more source
     roots.
   - Add `local_boundary` API/CLI configuration for classification.
   - Layout inference such as `src/` may be added later, but explicit
     configuration takes precedence.

2. Should local filesystem collection include directories without
   `__init__.py` as namespace packages by default?
   - Recommendation: yes, but only when the pruned filesystem tree sees at
     least one Python file or package-like child below that directory.
   - Empty non-Python directories should not be scanned.

3. How should PDA categorize a namespace package with both local and external
   portions?
   - Recommendation: keep module kind and category separate.
   - Record namespace portions individually.
   - Categorize the module for local scanning as local when at least one
     portion is under the local boundary.
   - Preserve external portions in metadata for environment/import analysis.

4. Should project resolution ignore `sys.modules` entirely, or should it allow
   an opt-in compatibility mode that observes it?
   - Recommendation: project resolution should not let `sys.modules` silently
     override explicit source roots.
   - Runtime/environment resolution should be allowed to observe `sys.modules`
     because some PDA workflows intentionally inspect the active interpreter
     environment.

5. Should `ModuleSpec` be stored directly in PDA models, or should PDA store a
   serializable import descriptor derived from the spec?
   - Decision: `ModuleSpec` stays inside the resolution layer as transient
     import-system evidence. PDA models store serializable facts: identity,
     origin, origin type, submodule search locations, kind, and category.

6. What is the exact symbol FQN policy for function-local assignments,
   comprehensions, lambdas, and exception aliases?
   - Recommendation: model a lexical symbol path for every binding PDA tracks.
   - Mark paths as importable or internal.
   - Keep runtime target resolution separate from lexical symbol identity.

7. Should `package` mean top-level distribution/import package, current package
   context for relative imports, or both? The current term is overloaded and may
   need replacement by more specific names.
   - Decision: do not use `package` for the analyzer target. Use
     `AnalysisTarget.root_module_name` for the requested import root,
     `ModuleIdentity.top_level_name` for the first FQN component, and
     `SourceModuleContext.containing_package` for relative import resolution.

8. How precise should first-generation call resolution be?
   - Recommendation: start with direct lexical calls, import-bound calls, and
     module attribute calls.
   - Represent dynamic or object-dependent calls as unresolved or partially
     resolved.
   - Add type/value inference incrementally instead of making it part of module
     resolution.

9. Should PDA use Python's `symtable` module as an authority for lexical scopes?
   - Recommendation: evaluate it in the test-harness phase.
   - Prefer it where it matches Python semantics better than hand-rolled AST
     traversal.
   - Keep PDA's own source spans, import binding model, and cross-module
     resolution because `symtable` does not solve those parts.

## Migration Shape

The implementation should proceed in small reviewable steps:

1. Add tests around the policy with temporary project layouts.
2. Introduce a central resolver and result type without removing current
   callers.
3. Migrate import analysis to the central resolver.
4. Migrate module collection to the central resolver.
5. Move `Module` away from ambient lazy resolution.
6. Remove duplicated resolver/creator behavior.
7. Add an ADR once the policy is accepted and the trade-offs are final.

## References

- Python Language Reference: "The import system"
  https://docs.python.org/3/reference/import.html
- Python Library Reference: `importlib`
  https://docs.python.org/3/library/importlib.html
