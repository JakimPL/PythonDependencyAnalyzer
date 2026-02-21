from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pda.models import PathForest, PathNode
from pda.specification import ImportPath, SysPaths
from pda.tools.logger import logger


class FileSystemScanner:
    """Scans filesystem for Python modules and converts paths to ImportPaths."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        paths: List[Path] = SysPaths.get_candidates(base_path=project_root)
        self._path_forest: PathForest = PathForest(paths)

    def get_submodule_paths(self, origin: Optional[Path] = None) -> List[Path]:
        """
        Get all Python files and packages in a directory.

        Args:
            origin: Directory path to scan.

        Returns:
            Sorted list of paths to Python files and package directories.
        """
        if origin is None:
            return []

        origin_node = self._path_forest.get(origin)
        if origin_node is None:
            return []

        paths: List[Path] = []
        child: PathNode
        for child in origin_node.children:
            if (child.is_python_file and not child.is_init) or (child.is_dir and child.is_package):
                paths.append(child.filepath)

        return sorted(paths)

    def path_to_import_path(self, path: Path, base_path: Path) -> Optional[ImportPath]:
        """
        Convert a filesystem path to an ImportPath.

        Args:
            path: Filesystem path to convert.
            base_path: Base path for relative resolution.

        Returns:
            ImportPath if successful, None otherwise.
        """
        import_path = ImportPath.from_path(path, base_path)
        if import_path is None:
            logger.warning(
                "Could not determine import path for '%s' relative to '%s'",
                path,
                base_path,
            )

        return import_path

    def paths_to_import_paths(self, paths: List[Path], base_path: Path) -> List[ImportPath]:
        """
        Convert multiple filesystem paths to ImportPaths.

        Args:
            paths: List of filesystem paths to convert.
            base_path: Base path for relative resolution.

        Returns:
            List of successfully converted ImportPaths.
        """
        import_paths: List[ImportPath] = []
        for path in paths:
            import_path = self.path_to_import_path(path, base_path)
            if import_path is not None:
                import_paths.append(import_path)

        return import_paths
