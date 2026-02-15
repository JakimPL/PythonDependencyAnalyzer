from dataclasses import dataclass
from typing import Generic, Optional, Self, Tuple

from pda.types import HashableT


@dataclass
class Node(Generic[HashableT]):
    item: HashableT
    label: str
    level: int = 0
    order: int = 0
    group: Optional[str] = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented

        return bool(self.item == other.item)

    def __hash__(self) -> int:
        return hash(self.item)

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, Node):
            return NotImplemented

        return self.key < other.key

    @property
    def key(self) -> Tuple[int, int, str]:
        return (self.level, self.order, self.label)
