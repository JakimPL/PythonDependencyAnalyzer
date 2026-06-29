from __future__ import annotations

from pathlib import Path

import pytest

from pda.resolution import ProjectResolutionContext


def test_project_resolution_context_defaults_source_root_and_boundary_to_project_root(tmp_path: Path) -> None:
    context = ProjectResolutionContext.create(tmp_path)

    assert context.project_root == tmp_path.resolve()
    assert context.source_roots == (tmp_path.resolve(),)
    assert context.local_boundary == tmp_path.resolve()


def test_project_resolution_context_environment_excludes_ambient_sys_path(tmp_path: Path) -> None:
    context = ProjectResolutionContext.create(tmp_path)

    assert context.environment.include_sys_path is False
    assert context.environment.stdlib_roots


def test_project_resolution_context_resolves_relative_source_roots_and_boundary(tmp_path: Path) -> None:
    context = ProjectResolutionContext.create(
        tmp_path,
        source_roots=(Path("src"), Path("packages/app")),
        local_boundary=Path("."),
    )

    assert context.source_roots == (
        (tmp_path / "src").resolve(),
        (tmp_path / "packages" / "app").resolve(),
    )
    assert context.local_boundary == tmp_path.resolve()


def test_project_resolution_context_rejects_empty_source_roots(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="At least one source root"):
        ProjectResolutionContext.create(tmp_path, source_roots=())
