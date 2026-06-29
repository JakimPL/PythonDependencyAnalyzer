from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from pda.constants import DELIMITER


@dataclass(frozen=True)
class ModuleIdentity:
    name: str

    @property
    def parts(self) -> Tuple[str, ...]:
        return tuple(part for part in self.name.split(DELIMITER) if part)

    @property
    def public_fqn(self) -> str:
        return self.name.removesuffix(f"{DELIMITER}__init__")

    @property
    def parent_name(self) -> Optional[str]:
        parts = self.parts
        if len(parts) <= 1:
            return None

        return DELIMITER.join(parts[:-1])

    @property
    def top_level_name(self) -> str:
        parts = self.parts
        return parts[0] if parts else self.name
