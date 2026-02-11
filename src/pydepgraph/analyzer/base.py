from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, Optional

from pydepgraph.config import ConfigT
from pydepgraph.tools import logger
from pydepgraph.tools.utils import resolve_path
from pydepgraph.types import Pathlike, T


class BaseAnalyzer(ABC, Generic[ConfigT, T]):
    def __init__(
        self,
        config: Optional[ConfigT] = None,
        project_root: Optional[Pathlike] = None,
        package: Optional[str] = None,
    ) -> None:
        self.config = self.default_config() if config is None else config
        self._project_root = resolve_path(project_root)
        self._package = package

    @classmethod
    @abstractmethod
    def default_config(cls) -> ConfigT:
        """Return the default configuration for this analyzer."""

    @abstractmethod
    def __bool__(self) -> bool:
        """Return True if the analyzer has processed data, False otherwise."""

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> T:
        """Run the analyzer and return the result."""

    @abstractmethod
    def clear(self) -> None:
        """Clear the analyzer's internal state."""

    @property
    def project_root(self) -> Optional[Path]:
        return self._project_root

    @project_root.setter
    def project_root(self, value: Optional[Pathlike]) -> None:
        self._project_root = resolve_path(value)
        if self:
            logger.info("Project root changed. Clearing the graph and modules.")

        self.clear()

    @property
    def package(self) -> Optional[str]:
        return self._package

    @package.setter
    def package(self, value: Optional[str]) -> None:
        self._package = value
        if self:
            logger.info("Package changed. Clearing the graph and modules.")

        self.clear()
