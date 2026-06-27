from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path
from typing import Dict, Mapping

WASM_DEPENDENCIES = ("anytree", "beautifulsoup4", "networkx", "pydantic", "pyyaml", "pyvis")
BUNDLE_NAME = "pda-bundle.zip"
BUNDLE_ROOT = Path("/app")


async def bootstrap(notebook_location: str) -> Path:
    import micropip
    from pyodide.http import pyfetch

    await micropip.install(list(WASM_DEPENDENCIES))

    if not (BUNDLE_ROOT / "src" / "pda").exists():
        response = await pyfetch(f"{notebook_location}/{BUNDLE_NAME}")
        zipfile.ZipFile(io.BytesIO(await response.bytes())).extractall(BUNDLE_ROOT)

    project_src = BUNDLE_ROOT / "src"
    if str(project_src) not in sys.path:
        sys.path.insert(0, str(project_src))

    patch_module_resolution()
    return project_src


def patch_module_resolution() -> None:
    import ast

    from pda.specification.modules.sys_paths import SysPaths

    paths = SysPaths().paths
    paths.update(pyodide_candidates(paths, ast.__file__))


def pyodide_candidates(candidates: Mapping[str, Path], stdlib_origin: str) -> Dict[str, Path]:
    resolved: Dict[str, Path] = {key: Path("/" + str(value).lstrip("/")) for key, value in candidates.items()}
    resolved.setdefault("stdlib_archive", Path(stdlib_origin).parent)
    return resolved
