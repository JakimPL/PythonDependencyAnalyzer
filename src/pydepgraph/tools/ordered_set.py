from typing import Dict, Generic, Iterable, Iterator, Optional

from pydepgraph.types import AnyT


class OrderedSet(Generic[AnyT]):
    def __init__(self, iterable: Optional[Iterable[AnyT]] = None) -> None:
        self._dict: Dict[AnyT, None] = {}
        if iterable is not None:
            for item in iterable:
                self._dict[item] = None

    def __bool__(self) -> bool:
        return bool(self._dict)

    def __contains__(self, item: AnyT) -> bool:
        return item in self._dict

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[AnyT]:
        return iter(self._dict)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({list(self)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrderedSet):
            return NotImplemented

        return tuple(self) == tuple(other)

    def add(self, item: AnyT) -> None:
        self._dict[item] = None

    def discard(self, item: AnyT) -> None:
        self._dict.pop(item, None)

    def remove(self, item: AnyT) -> None:
        del self._dict[item]

    def pop(self) -> AnyT:
        return self._dict.popitem()[0]

    def clear(self) -> None:
        self._dict.clear()

    def update(self, iterable: Iterable[AnyT]) -> None:
        for item in iterable:
            self._dict[item] = None
