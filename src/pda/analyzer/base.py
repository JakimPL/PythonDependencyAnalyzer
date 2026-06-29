import sys
from abc import ABC, abstractmethod
from importlib import invalidate_caches
from pathlib import Path
from typing import Generic, Optional

from pda.analyzer.target import AnalysisTarget
from pda.config import ConfigT
from pda.tools.logger import logger
from pda.types import AnyT, Pathlike


def register_search_path(path: Path) -> None:
    """
    Ensure ``path`` is on ``sys.path`` for explicit runtime-compatible workflows.

    Project analyzers should use ``ProjectResolutionContext`` instead of mutating
    the interpreter search path.
    """
    entry = str(path)
    sys.path[:] = [existing for existing in sys.path if existing != entry]
    sys.path.insert(0, entry)
    invalidate_caches()


class BaseAnalyzer(ABC, Generic[ConfigT, AnyT]):
    def __init__(
        self,
        config: Optional[ConfigT] = None,
        project_root: Optional[Pathlike] = None,
        analysis_target: Optional[AnalysisTarget] = None,
    ) -> None:
        self.config = config or self.default_config()
        self._project_root = Path(project_root).resolve() if project_root is not None else None
        self._analysis_target = analysis_target

    @abstractmethod
    def __bool__(self) -> bool:
        """Return True if the analyzer has processed data, False otherwise."""

    def __call__(self, *, refresh: bool = False) -> AnyT:
        return self._analyze_if_needed(refresh=refresh)

    @abstractmethod
    def clear(self) -> None:
        """Clear the analyzer's internal state."""

    @abstractmethod
    def _analyze_if_needed(self, *, refresh: bool = False) -> AnyT:
        """Perform analysis if needed, optionally refreshing the data."""

    @property
    def project_root(self) -> Optional[Path]:
        return self._project_root

    @project_root.setter
    def project_root(self, value: Optional[Pathlike]) -> None:
        self._project_root = Path(value).resolve() if value is not None else None
        if self:
            logger.info("Project root changed. Clearing the graph and modules")

        self.clear()

    @property
    def analysis_target(self) -> Optional[AnalysisTarget]:
        return self._analysis_target

    @analysis_target.setter
    def analysis_target(self, value: Optional[AnalysisTarget]) -> None:
        self._analysis_target = value
        if self:
            logger.info("Analysis target changed. Clearing analyzer state.")

        self.clear()

    @classmethod
    @abstractmethod
    def default_config(cls) -> ConfigT:
        """Return the default configuration for this analyzer."""
