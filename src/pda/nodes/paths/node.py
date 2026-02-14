from __future__ import annotations

from pathlib import Path
from typing import Optional

from pda.nodes.base import BaseNode
from pda.tools.paths import exists, is_dir, is_file, is_python_file


class PathNode(BaseNode[Path]):
    def __init__(
        self,
        filepath: Path,
        parent: Optional[PathNode] = None,
    ) -> None:
        super().__init__(item=filepath, parent=parent)
        self.filepath: Path = filepath

        self._has_init: bool = exists(filepath / "__init__.py") if is_dir(filepath) else False
        self._is_package: bool = False

    def __repr__(self) -> str:
        return f"PathNode(filepath={self.filepath})"

    @property
    def name(self) -> str:
        return self.filepath.name

    @property
    def is_file(self) -> bool:
        return is_file(self.filepath)

    @property
    def is_python_file(self) -> bool:
        return is_python_file(self.filepath)

    @property
    def is_dir(self) -> bool:
        return is_dir(self.filepath)

    @property
    def is_init(self) -> bool:
        return self.filepath.name == "__init__.py"

    @property
    def is_package(self) -> bool:
        return self._is_package

    @is_package.setter
    def is_package(self, value: bool) -> None:
        self._is_package = value

    @property
    def has_init(self) -> bool:
        return self._has_init

    def mark_as_package_if_applicable(self) -> None:
        if not self.is_dir:
            return

        if self._has_init:
            self._is_package = True
            return

        if self.has_python_files_in_tree():
            self._is_package = True
            return

        self._is_package = False

    def has_python_files_in_tree(self) -> bool:
        for child in self.children:
            if child.is_python_file:
                return True

            if child.is_dir and child.is_package:
                return True

        return False
