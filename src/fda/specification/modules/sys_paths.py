import sysconfig
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from fda.exceptions import FDAPathResolutionError, FDARelativeBasePathError
from fda.specification.imports import ImportPath
from fda.specification.modules.spec import validate_spec_origin
from fda.tools.singleton import Singleton
from fda.types import Pathlike


class SysPaths(metaclass=Singleton):
    def __init__(self) -> None:
        self.paths: Dict[str, Path] = self.sys_paths()

    @staticmethod
    def sys_paths(keys: Tuple[str, ...] = ("purelib", "stdlib")) -> Dict[str, Path]:
        sys_paths = {key: Path(path) for key, path in sysconfig.get_paths().items() if key in keys}
        return dict(sorted(sys_paths.items(), key=lambda pair: (-len(Path(pair[1]).parts), pair[0])))

    @classmethod
    def get_candidates(cls, base_path: Optional[Pathlike] = None) -> List[Path]:
        candidates: List[Path] = []
        if base_path is not None:
            base_path = Path(base_path)
            if not base_path.is_absolute():
                raise FDARelativeBasePathError(f"Base path must be an absolute path, got: {base_path}")

            candidates.append(base_path)

        for path in cls().paths.values():
            candidates.append(path)

        return candidates

    @classmethod
    def resolve(
        cls,
        origin: Union[Path, ModuleSpec],
        base_path: Optional[Pathlike] = None,
    ) -> ImportPath:
        if isinstance(origin, ModuleSpec):
            validate_spec_origin(origin)
            assert origin.origin is not None
            origin = Path(origin.origin)

        if not origin.is_absolute():
            raise FDAPathResolutionError(f"Provided path must be absolute, got: {origin}")

        import_path: Optional[ImportPath] = None
        candidates = cls.get_candidates(base_path=base_path)
        for candidate in candidates:
            import_path = ImportPath.from_path(origin, candidate)
            if import_path is not None:
                return import_path

        raise FDAPathResolutionError(f"Could not resolve path '{origin}' against candidates: {candidates}")
