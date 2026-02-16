from pathlib import Path
from typing import Any, Dict, Optional, Self

from pydantic import Field

from pda.config.base import BaseConfig
from pda.config.pyvis.options import PDAOptions
from pda.tools.serialization import load_json
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
        return Path(__file__).parent.parent.parent.parent.parent / "options" / "pyvis.json"

    @classmethod
    def default(cls) -> Self:
        config_dict = load_json(cls.default_path())
        return cls(**config_dict)
