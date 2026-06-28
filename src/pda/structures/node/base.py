from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, Self, Tuple

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
    available: bool = True
    in_cycle: bool = False
    component: Optional[int] = None

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

    @property
    def identifier(self) -> str:
        return f"{self.label}#{self.ordinal}" if self.ordinal else self.label

    def cycle_data(self) -> Dict[str, Any]:
        if not self.in_cycle:
            return {}

        data: Dict[str, Any] = {"in_cycle": True}
        if self.component is not None:
            data["component"] = self.component

        return data

    def serialize(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.identifier,
            "label": self.label,
            "level": self.level,
        }

        if self.group is not None:
            data["group"] = self.group

        if not self.available:
            data["available"] = False

        if self.details is not None:
            data["details"] = self.details

        data.update(self.cycle_data())
        return data
