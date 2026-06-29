# Coding Guidelines

These guidelines describe how PDA code should evolve. They are intentionally
stricter around module resolution because that area defines the facts used by
import graphs, scope analysis, and future call graphs.

## General

1. Keep code modularized around clear ownership boundaries.
2. If a function has several meaningful steps, split them into helpers with one clear responsibility.
3. Use explicit names. Do not abbreviate variable names unless the abbreviation is a standard Python name such as `ast`.
4. Avoid hardcoded semantic values. Prefer `Final` constants, and move them to a shared module when the concept is reused.
5. Use `pathlib.Path` instead of `os.path`.
6. Prefer protocols or focused collaborators over inheritance hierarchies.
7. Separate function options with `*`. Positional arguments should be intentionally chosen.
8. Prefer `match` statements for enum handling and clear structural dispatch.
9. Do not preserve backward compatibility for internal APIs, configs, or data shapes unless we explicitly decide to.
10. Avoid tramp data: do not pass broad objects through layers that only need one precise value.
11. Avoid unjustified `Optional` state. If a value is required in a code path, model that path with a type or collaborator where the value is non-optional.
12. Use default values only when the default is part of the intended contract. Otherwise require the value explicitly.
13. Be explicit about type expectations. Avoid dynamic `getattr` or `hasattr` except at system boundaries.
14. Prefer computable properties over stored boolean variables when the boolean can be derived from existing state.

## PDA Boundaries

1. `ModuleResolutionService` is the public facade for module resolution policy.
2. Resolution collaborators should own one repeated concern: spec lookup, filesystem identity, import candidates, classification, conversion, or path helpers.
3. Specification models should describe facts; they must not perform ambient project resolution as a validation side effect.
4. `ModuleSource` is source-file context only. It must not expose methods that call `find_spec` or create resolved modules.
5. `Module` describes stored module facts. Its compatibility `spec` view may reconstruct from stored facts, but must not call ambient `find_spec`.
6. Analyzer adapters such as `ImportResolver` translate analyzer inputs into central resolution calls. They should not grow independent resolution policy.
7. Runtime/environment compatibility paths must be named as such. Do not hide them behind nullable project collaborators.
8. Prefer explicit modes or strategy objects over branches like `if resolver is None` when the branch changes behavior.

## Shared Ownership

1. General-purpose helpers that are not model-specific belong in shared/common modules, not inside feature modules.
2. Import shared helpers directly from the module that owns their implementation.
3. Before adding a helper, search the repository for existing logic with `rg`.
4. If new code duplicates existing logic, extract the shared rule first and make both call sites use it.
5. `__init__.py` files may expose stable public API for their package, but internal code should import implementation modules directly.
6. Prefer subpackages over a flat directory when a concept has multiple focused collaborators.
7. Do not overload one module with unrelated responsibilities.

## Type Hints

1. Specify all input and return types in function signatures, including `None`.
2. Fill generic types.
3. Do not cast or silence type errors unless the boundary is an untyped or mistyped third-party API.
4. Avoid `Any` and `object` unless the boundary genuinely accepts arbitrary data.
5. Use `from __future__ import annotations` when it keeps annotations clean.
6. Use the type style already established in the surrounding package.
7. Validate with `mypy`.

## Error Handling

1. Let failures crash unless the code can recover meaningfully.
2. Handle errors at the execution boundary when possible.
3. Do not add `try`/`except` blocks that only repackage failures without recovery.
4. Bare `except` and broad `except Exception` are forbidden unless the code is at a deliberate compatibility boundary.
5. Error handling blocks should cover only the code subject to the expected failure.
6. Resolution failures should usually be represented as typed resolution results, not control-flow exceptions.

## Models

1. Prefer Pydantic models for validated or serialized data.
2. Use frozen models when instances are not meant to change.
3. Dataclasses are acceptable for small internal state objects that are not serialized or validated.
4. Models should not mutate global interpreter state.
5. Models should not depend on ambient `sys.path` unless the model explicitly represents the runtime environment.

## Documentation

1. Documentation should explain intention, context, and policy.
2. If a function makes a non-obvious decision, explain the decision in a docstring or design document.
3. Avoid comments and docstrings that restate code.
4. Use clear names instead of explanatory comments.
5. Code comments are acceptable for third-party API quirks or non-obvious invariants.
6. Code comments and docstrings are not for documenting change history or progress.

## Tests

1. Test files should mirror the ownership of the functionality under test.
2. When moving functionality between packages, move its direct unit tests in the same change.
3. Parametrize tests that share the same body.
4. Prefer fixtures over ad hoc factories when a scenario is shared.
5. Do not assert configuration defaults unless the default is a contract.
6. Unit tests may mock system boundaries, but must not mock the domain logic under test.
7. Integration tests should exercise real computation pipelines against real synthetic data.
8. When a test expectation diverges from production behavior, decide which is wrong before changing either side.
9. Resolution tests should avoid relying on the host Python environment except where the test is explicitly about built-in, frozen, stdlib, or runtime behavior.
