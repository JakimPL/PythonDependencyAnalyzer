from __future__ import annotations

from dataclasses import dataclass

from pda.constants import DELIMITER


@dataclass(frozen=True)
class AnalysisTarget:
    """The import root the user asked an analyzer to examine."""

    root_module_name: str

    def __post_init__(self) -> None:
        if not self.root_module_name:
            raise ValueError("Root module name must be provided")

        if self.root_module_name.startswith(DELIMITER):
            raise ValueError("Root module name must be absolute")

        if any(not part for part in self.root_module_name.split(DELIMITER)):
            raise ValueError(f"Invalid root module name: '{self.root_module_name}'")
