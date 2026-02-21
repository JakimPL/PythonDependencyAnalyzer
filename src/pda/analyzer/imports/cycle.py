from __future__ import annotations

import warnings
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional

from pda.config import ModuleImportsAnalyzerConfig
from pda.exceptions import PDADependencyCycleError, PDADependencyCycleWarning
from pda.tools.logger import logger


class NodeState(Enum):
    UNVISITED = auto()
    VISITING = auto()
    VISITED = auto()


class CycleDetector:
    def __init__(self, config: ModuleImportsAnalyzerConfig) -> None:
        self._config = config
        self._node_states: Dict[Optional[Path], NodeState] = {}
        self._cycle_detected: bool = False
        self._cycle_path: List[Path] = []

    @property
    def cycle_detected(self) -> bool:
        return self._cycle_detected

    @property
    def cycle_path(self) -> List[Path]:
        return self._cycle_path.copy()

    def reset(self) -> None:
        self._node_states.clear()
        self._cycle_detected = False
        self._cycle_path.clear()

    def mark_visiting(self, origin: Optional[Path]) -> None:
        self._node_states[origin] = NodeState.VISITING

    def mark_visited(self, origin: Optional[Path]) -> None:
        self._node_states[origin] = NodeState.VISITED

    def get_state(self, origin: Optional[Path]) -> NodeState:
        return self._node_states.get(origin, NodeState.UNVISITED)

    def check_cycle(
        self,
        current_path: List[Path],
        next_origin: Optional[Path],
    ) -> bool:
        if next_origin is None:
            return False

        if next_origin in current_path:
            self._cycle_detected = True
            self._cycle_path = current_path + [next_origin]
            self._handle_cycle()
            return True

        return False

    def _handle_cycle(self) -> None:
        paths = "\n-> ".join(str(path) for path in self._cycle_path)

        if not self._config.ignore_cycles:
            raise PDADependencyCycleError(f"Dependency cycle detected in path:\n{paths}")

        logger.warning("Cycle detected: %s", paths)

    def report_cycles(self) -> None:
        if self._cycle_detected:
            message = "Import cycle detected during analysis:\n-> {}".format(
                "\n-> ".join(str(path) for path in self._cycle_path),
            )
            warnings.warn(message, PDADependencyCycleWarning)
