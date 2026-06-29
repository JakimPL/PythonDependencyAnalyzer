# Python Dependency Analyzer

Python Dependency Analyzer describes Python code in terms of importable modules,
symbol bindings, and dependency edges. This language keeps static-analysis facts
separate from the interpreter process that happens to run the analyzer.

## Language

**Analyzed Project**:
The Python codebase whose dependencies are being examined.
_Avoid_: current project, running project

**Target Environment**:
The import environment PDA models for an analyzed project.
_Avoid_: current interpreter, host environment

**Source Root**:
A directory whose children form importable top-level module names for the
analyzed project.
_Avoid_: project root when the directory is only one import root

**Local Boundary**:
The filesystem boundary used to decide whether a resolved module belongs to the
analyzed project.
_Avoid_: package root, repository root

**Module Identity**:
The fully qualified import name by which a module is known in the target
environment.
_Avoid_: file name, path name

**Module Location**:
The origin file or package search locations associated with a module identity.
_Avoid_: module path when the value may be a search location

**Module Kind**:
The structural form of a resolved module, such as source module, regular
package, namespace package, built-in module, or frozen module.
_Avoid_: module type when referring to dependency category

**Module Category**:
The dependency role assigned to a module relative to the analyzed project:
local, standard library, external, or unknown.
_Avoid_: module kind

**Module Resolution**:
The result of mapping a requested import name, import path, or source path to a
module identity and location in the target environment.
_Avoid_: import, lookup

**Source Module Context**:
The module identity, package context, and source-root context attached to a
source file before resolving its imports or symbols.
_Avoid_: source file metadata

**Import Path**:
The parsed target shape of an import statement before it is resolved to a module
or symbol target.
_Avoid_: module name when the import includes relative level or imported name

**Symbol Binding**:
A name introduced in a scope and the target it may refer to.
_Avoid_: variable when the binding may name a module, class, function, or import

**Call Site**:
A syntactic function-call occurrence found in source code.
_Avoid_: callee

**Call Edge**:
A dependency-graph edge from a caller to one or more possible callees.
_Avoid_: call site
