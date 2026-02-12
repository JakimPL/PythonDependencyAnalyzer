from __future__ import annotations

from pathlib import Path
from typing import Optional

from anytree import NodeMixin


class PathNode(NodeMixin):  # type: ignore[misc]
    def __init__(
        self,
        path: Path,
        parent: Optional[PathNode] = None,
    ) -> None:
        self.path: Path = path
        self.parent: Optional[PathNode] = parent

        self._is_package: Optional[bool] = None
        self._has_init: bool = (path / "__init__.py").exists() if path.is_dir() else False

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def is_file(self) -> bool:
        return self.path.is_file()

    @property
    def is_dir(self) -> bool:
        return self.path.is_dir()

    @property
    def is_init(self) -> bool:
        return self.path.name == "__init__.py"

    @property
    def is_python_file(self) -> bool:
        return self.is_file and self.path.suffix.lower() == ".py"

    @property
    def has_init(self) -> bool:
        return self._has_init

    def is_package(self) -> bool:
        if self._is_package is not None:
            return self._is_package

        if self.is_file:
            self._is_package = False
            return False

        if self._has_init:
            self._is_package = True
            return True

        self._is_package = self._has_python_files_in_tree()
        return self._is_package

    def _has_python_files_in_tree(self) -> bool:
        if self.is_python_file:
            return True

        return any(child._has_python_files_in_tree() for child in self.children)
