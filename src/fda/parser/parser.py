from __future__ import annotations

import ast
from pathlib import Path
from typing import Union


def parse_python_file(filepath: Union[str, Path]) -> ast.AST:
    filepath = Path(filepath)

    if not filepath.exists() or not filepath.is_file():
        raise FileNotFoundError(f"The file {filepath} does not exist or is not a file.")

    if filepath.suffix != ".py":
        raise ValueError(f"The file {filepath} is not a Python (.py) file.")

    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(filepath))

    return tree
