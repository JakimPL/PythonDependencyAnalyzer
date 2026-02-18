from dataclasses import dataclass
from typing import Any, Generic, Optional, Self, Tuple

from pda.types import HashableT


@dataclass
class Node(Generic[HashableT]):
    item: HashableT
    ordinal: int
    label: str
    details: Optional[str] = None
    level: int = 0
    order: int = 0
    group: Optional[str] = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented

        return bool(self.item == other.item and self.ordinal == other.ordinal)

    def __hash__(self) -> int:
        return hash((self.item, self.ordinal))

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, Node):
            return NotImplemented

        return self.key < other.key

    @property
    def key(self) -> Tuple[Any, ...]:
        return (self.level, self.order, self.label, self.ordinal)
