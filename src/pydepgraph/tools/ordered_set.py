from typing import Dict, Generic, Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


class OrderedSet(Generic[T]):
    def __init__(self, iterable: Optional[Iterable[T]] = None) -> None:
        self._dict: Dict[T, None] = {}
        if iterable is not None:
            for item in iterable:
                self._dict[item] = None

    def __bool__(self) -> bool:
        return bool(self._dict)

    def __contains__(self, item: T) -> bool:
        return item in self._dict

    def __len__(self) -> int:
        return len(self._dict)

    def __iter__(self) -> Iterator[T]:
        return iter(self._dict)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({list(self)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrderedSet):
            return NotImplemented

        return tuple(self) == tuple(other)

    def add(self, item: T) -> None:
        self._dict[item] = None

    def discard(self, item: T) -> None:
        self._dict.pop(item, None)

    def remove(self, item: T) -> None:
        del self._dict[item]

    def pop(self) -> T:
        return self._dict.popitem()[0]

    def clear(self) -> None:
        self._dict.clear()

    def update(self, iterable: Iterable[T]) -> None:
        for item in iterable:
            self._dict[item] = None
