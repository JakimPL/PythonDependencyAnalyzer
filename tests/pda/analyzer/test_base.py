from __future__ import annotations

import importlib
import sys
from pathlib import Path

from pda.analyzer.base import register_search_path
from pda.specification import clear_module_spec_cache


def test_register_search_path_moves_existing_entry_to_front(tmp_path: Path) -> None:
    original_sys_path = list(sys.path)
    path = tmp_path.resolve()
    entry = str(path)

    try:
        sys.path.append(entry)

        register_search_path(path)

        assert sys.path[0] == entry
        assert sys.path.count(entry) == 1
    finally:
        sys.path[:] = original_sys_path
        clear_module_spec_cache()
        importlib.invalidate_caches()
