from pathlib import Path
from typing import Any, Dict, Optional, Self

from pydantic import Field

from pda.config.base import BaseConfig
from pda.config.pyvis.options import PDAOptions
from pda.config.pyvis.theme import Theme
from pda.tools.serialization import load_yaml
from pda.tools.templates import TemplateLoader
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
    def default(cls, theme: Theme = "light") -> Self:
        return cls.load(cls.default_path(), theme=theme)

    @classmethod
    def load(cls, config_path: Path, theme: Theme = "light") -> Self:
        cls._validate_config_path(config_path)
        theme_vars = cls._load_theme(config_path, theme)
        loader = TemplateLoader(theme_vars)
        return cls(
            pda=load_yaml(config_path / "pda.yaml"),
            network=loader.load(config_path / "network.yaml"),
            vis=loader.load(config_path / "vis.yaml"),
        )

    @staticmethod
    def _validate_config_path(config_path: Path) -> None:
        if config_path.is_file():
            raise NotADirectoryError(f"Expected a directory for config path, but got a file: '{config_path}'")

        if not config_path.exists():
            raise FileNotFoundError(f"Config path '{config_path}' does not exist.")

    @staticmethod
    def _load_theme(config_path: Path, theme: Theme) -> Dict[str, Any]:
        theme_path = config_path / "themes" / f"{theme}.yaml"
        if not theme_path.exists():
            raise FileNotFoundError(f"Theme file not found: '{theme_path}'")

        result: Dict[str, Any] = load_yaml(theme_path)
        return result
