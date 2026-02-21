import json
from typing import Any

import yaml

from pda.types import Pathlike


def load_json(filepath: Pathlike) -> Any:
    with open(filepath, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data: Any, filepath: Pathlike, indent: int = 4) -> None:
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=indent)


def load_yaml(filepath: Pathlike) -> Any:
    with open(filepath, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def save_yaml(data: Any, filepath: Pathlike) -> None:
    with open(filepath, "w", encoding="utf-8") as file:
        yaml.safe_dump(data, file)
