import pkgutil
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Dict, Optional

from fda.specification import ImportPath, Module, find_module_spec
from fda.tools import logger
from fda.types import Pathlike


class ModulesCollector:
    def __init__(self, project_root: Pathlike) -> None:
        self.project_root = Path(project_root).resolve()
        self.pkg_modules: Dict[str, pkgutil.ModuleInfo] = {module.name: module for module in pkgutil.iter_modules()}
        self.modules: Dict[str, Module] = {}

    def _add_module(self, name: str, package: Optional[str] = None) -> None:
        spec = find_module_spec(name, package=package)
        if not spec:
            logger.warning("Module '%s' not found", name)
            return

        if not spec.origin:
            raise FileNotFoundError(f"Module '{name}' has no origin path")

        if spec.origin == "frozen":
            logger.debug("Skipping frozen module: %s", name)
            return

        assert spec.origin is not None, f"Module '{name}' has no origin path"
        origin = Path(spec.origin).resolve()
        if origin.suffix.lower() != ".py":
            logger.debug("Module %s has non-Python origin: %s", name, origin)

        module = Module.from_spec(spec, package=package)
        self.modules[name] = module
        self._add_submodules(spec, package=name)

    def _add_submodules(self, spec: ModuleSpec, package: Optional[str] = None) -> None:
        if not spec.submodule_search_locations:
            return

        for location in spec.submodule_search_locations:
            origin = Path(location).resolve()
            files = list(origin.glob("*.py"))
            for path in files:
                import_path = str(ImportPath.from_path(path, origin.parent))
                spec = find_module_spec(import_path, package=package)
                self._add_module(import_path, package=package)

    def get_modules(self) -> Dict[str, Module]:
        self.modules.clear()
        self._add_pkg_modules()
        self._add_internal_modules()
        return self.modules

    def _add_pkg_modules(self) -> None:
        for pkg_module in self.pkg_modules.values():
            name = pkg_module.name
            is_package = pkg_module.ispkg
            package = name if is_package else None
            self._add_module(name, package=package)

    def _add_internal_modules(self) -> None:
        for path in self.project_root.rglob("*.py"):
            import_path = ImportPath.from_path(path, self.project_root)
            package = str(import_path.base)
            name = str(import_path)
            spec = find_module_spec(name, package=package)
            if spec:
                module = Module.from_spec(spec, package=package)
                self.modules[name] = module
