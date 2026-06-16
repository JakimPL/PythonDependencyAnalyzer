from pathlib import Path
from typing import Any, Dict, Optional, Self

from pydantic import Field

from pda.config.base import BaseConfig
from pda.config.pyvis.layout import LayoutConfig
from pda.config.pyvis.theme import Theme
from pda.tools.serialization import load_yaml
from pda.tools.templates import TemplateLoader
from pda.types import nested_defaultdict


class PyVisConfig(BaseConfig):
    network: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Keyword arguments to be passed to the pyvis Network constructor.",
    )
    vis: Dict[str, Dict[str, Any]] = Field(
        default_factory=nested_defaultdict,
        description="vis.js options for customizing the appearance of the pyvis visualization.",
    )
    layout: LayoutConfig = Field(
        default_factory=LayoutConfig,
        description="Python-side layout strategy used to position nodes before handing them to vis.js.",
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
            network=loader.load(config_path / "network.yaml"),
            vis=loader.load(config_path / "vis.yaml"),
            layout=cls._load_layout(config_path),
        )

    @staticmethod
    def _load_layout(config_path: Path) -> LayoutConfig:
        layout_path = config_path / "layout.yaml"
        if not layout_path.exists():
            return LayoutConfig()

        data: Optional[Dict[str, Any]] = load_yaml(layout_path)
        return LayoutConfig(**(data or {}))

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
