from pathlib import Path
from typing import Any, Dict, Optional, Self

from pydantic import Field

from pda.config.base import BaseConfig
from pda.config.pyvis.options import PDAOptions
from pda.tools.serialization import load_yaml
from pda.types import nested_defaultdict


class PyVisConfig(BaseConfig):
    pda: PDAOptions = Field(
        default_factory=PDAOptions,
        description="Options specific to the Python Dependency Analyzer visualization.",
    )
    network: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Keyword arguments to be passed to the pyvis Network constructor.",
    )
    vis: Dict[str, Dict[str, Any]] = Field(
        default_factory=nested_defaultdict,
        description="vis.js options for customizing the appearance of the pyvis visualization.",
    )

    @classmethod
    def default_path(cls) -> Path:
        return Path(__file__).parent.parent.parent.parent.parent / "config" / "pyvis"

    @classmethod
    def default(cls) -> Self:
        return cls.load(cls.default_path())

    @classmethod
    def load(cls, config_path: Path) -> Self:
        if config_path.is_file():
            raise NotADirectoryError(f"Expected a directory for config path, but got a file: '{config_path}'")

        if not config_path.exists():
            raise FileNotFoundError(f"Config path '{config_path}' does not exist.")

        pda = load_yaml(config_path / "pda.yaml")
        network = load_yaml(config_path / "network.yaml")
        vis = load_yaml(config_path / "vis.yaml")
        config_dict = {
            "pda": pda,
            "network": network,
            "vis": vis,
        }

        return cls(**config_dict)
