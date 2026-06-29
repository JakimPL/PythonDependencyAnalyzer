from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from pda.resolution.models.environment import TargetEnvironment
from pda.types import Pathlike


@dataclass(frozen=True)
class ProjectResolutionContext:
    project_root: Path
    source_roots: tuple[Path, ...]
    local_boundary: Path

    @classmethod
    def create(
        cls,
        project_root: Pathlike,
        *,
        source_roots: Optional[Iterable[Pathlike]] = None,
        local_boundary: Optional[Pathlike] = None,
    ) -> ProjectResolutionContext:
        root = Path(project_root).resolve()
        raw_source_roots = (root,) if source_roots is None else source_roots
        roots = tuple(cls._resolve_project_path(root, source_root) for source_root in raw_source_roots)
        if not roots:
            raise ValueError("At least one source root is required")

        boundary = cls._resolve_project_path(root, local_boundary) if local_boundary is not None else root
        return cls(
            project_root=root,
            source_roots=roots,
            local_boundary=boundary,
        )

    @property
    def environment(self) -> TargetEnvironment:
        return TargetEnvironment.create(
            self.source_roots,
            local_boundary=self.local_boundary,
        )

    @staticmethod
    def _resolve_project_path(project_root: Path, path: Pathlike) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = project_root / candidate

        return candidate.resolve()
