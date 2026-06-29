from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pda.constants import DELIMITER
from pda.resolution.models import (
    ModuleCoordinates,
    ModuleIdentity,
    ModuleLocation,
    TargetEnvironment,
)
from pda.resolution.paths import has_python_file_in_tree, longest_containing_root
from pda.specification.imports.origin import OriginType
from pda.tools.paths import is_dir, is_file, is_python_file
from pda.types import Pathlike


@dataclass(frozen=True)
class FilesystemModuleLookup:
    requested: Path
    coordinates: Optional[ModuleCoordinates] = None
    reason: Optional[str] = None

    @property
    def resolved(self) -> bool:
        return self.coordinates is not None


class FilesystemModuleLocator:
    def __init__(self, environment: TargetEnvironment) -> None:
        self._environment = environment

    def locate(
        self,
        path: Pathlike,
        *,
        source_root: Optional[Pathlike] = None,
    ) -> FilesystemModuleLookup:
        filepath = Path(path).resolve()
        root = Path(source_root).resolve() if source_root is not None else self._select_source_root(filepath)
        if root is None:
            return FilesystemModuleLookup(
                requested=filepath,
                reason=f"Path '{filepath}' is outside configured source roots",
            )

        name = self._module_name_from_path(filepath, root)
        if name is None:
            return FilesystemModuleLookup(
                requested=filepath,
                reason=f"Path '{filepath}' is not a Python module, package, or namespace portion",
            )

        return FilesystemModuleLookup(
            requested=filepath,
            coordinates=ModuleCoordinates(
                identity=ModuleIdentity(name),
                location=self._location_from_path(filepath, root),
            ),
        )

    def _select_source_root(self, path: Path) -> Optional[Path]:
        return longest_containing_root(path, self._environment.source_roots)

    def _module_name_from_path(self, path: Path, source_root: Path) -> Optional[str]:
        try:
            relative = path.relative_to(source_root)
        except ValueError:
            return None

        if is_dir(path):
            if not self._is_package_like_directory(path):
                return None

            parts = relative.parts
        elif is_python_file(path):
            stem = relative.with_suffix("")
            parts = stem.parts
            if parts[-1] == "__init__":
                parts = parts[:-1]
        else:
            return None

        if not parts:
            return None

        return DELIMITER.join(parts)

    def _location_from_path(self, path: Path, root: Path) -> ModuleLocation:
        locations: tuple[Path, ...]
        if is_dir(path):
            init_file = path / "__init__.py"
            origin = init_file if is_file(init_file) else None
            origin_type = OriginType.PYTHON if origin is not None else OriginType.NONE
            locations = (path,)
        else:
            origin = path
            origin_type = OriginType.PYTHON if is_python_file(path) else OriginType.NO_PYTHON
            locations = ()

        return ModuleLocation(
            origin=origin,
            origin_type=origin_type,
            submodule_search_locations=locations,
            matched_root=root,
        )

    def _is_package_like_directory(self, path: Path) -> bool:
        if is_file(path / "__init__.py"):
            return True

        return has_python_file_in_tree(path)
