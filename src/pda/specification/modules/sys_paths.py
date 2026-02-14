import sysconfig
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from pda.config import ValidationOptions
from pda.exceptions import PDAPathResolutionError, PDARelativeBasePathError
from pda.specification.imports import ImportPath
from pda.specification.modules.spec import validate_spec_origin
from pda.tools.singleton import Singleton
from pda.types import Pathlike


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
                raise PDARelativeBasePathError(f"Base path must be an absolute path, got: {base_path}")

            candidates.append(base_path)

        for path in cls().paths.values():
            candidates.append(path)

        return candidates

    @classmethod
    def resolve(
        cls,
        spec_or_origin: Optional[Union[Pathlike, ModuleSpec]],
        base_path: Optional[Pathlike] = None,
        validation_options: Optional[ValidationOptions] = None,
    ) -> Optional[ImportPath]:
        origin: Optional[Path] = None
        options: ValidationOptions = validation_options or ValidationOptions.strict()
        if isinstance(spec_or_origin, ModuleSpec):
            if options.validate_origin:
                origin = validate_spec_origin(
                    spec_or_origin,
                    expect_python=options.expect_python,
                )

        elif isinstance(spec_or_origin, (str, Path)):
            origin = Path(spec_or_origin)

        else:
            raise TypeError(f"Expected ModuleSpec or path-like object, got: {type(spec_or_origin)}")

        if origin is None or not origin.is_absolute():
            return None

        return cls.resolve_import_path(origin, base_path)

    @classmethod
    def resolve_import_path(cls, origin: Path, base_path: Optional[Pathlike]) -> ImportPath:
        import_path: Optional[ImportPath] = None
        candidates = cls.get_candidates(base_path=base_path)
        if not candidates:
            raise PDAPathResolutionError("No candidate paths available for resolving the origin path")

        for candidate in candidates:
            import_path = ImportPath.from_path(origin, candidate)
            if import_path is not None:
                return import_path

        raise PDAPathResolutionError(f"Could not resolve path '{origin}' against candidates: {candidates}")
