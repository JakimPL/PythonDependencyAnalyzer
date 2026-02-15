from __future__ import annotations

from collections.abc import Iterable
from typing import Callable, Generic, Optional, Tuple, Type, Union

from anytree import NodeMixin

from pda.structures.node.base import Node
from pda.types import HashableT


class AnyNode(Node[HashableT], NodeMixin, Generic[HashableT]):  # type: ignore[misc]
    def __init__(
        self,
        item: HashableT,
        *,
        parent: Optional[AnyNode[HashableT]] = None,
        ordinal: int = 0,
        label: Optional[str] = None,
        level: int = 0,
        order: int = 0,
        group: Optional[str] = None,
    ) -> None:
        self.parent: Optional[AnyNode[HashableT]] = parent

        ordinal = ordinal or id(item)
        label = label or str(item)
        level = level if parent is None else parent.level + 1
        super().__init__(
            item,
            ordinal=ordinal,
            label=label,
            level=level,
            order=order,
            group=group,
        )

    def has_ancestor_matching(self, predicate: Callable[[AnyNode[HashableT]], bool]) -> bool:
        current = self.parent
        while current:
            if predicate(current):
                return True

            current = current.parent

        return False

    def has_ancestor(self, ancestor: Union[AnyNode[HashableT], Iterable[AnyNode[HashableT]]]) -> bool:
        ancestors = {ancestor} if isinstance(ancestor, AnyNode) else set(ancestor)
        return self.has_ancestor_matching(lambda node: node in ancestors)

    def has_ancestor_of_type(
        self,
        ancestor_type: Union[Type[AnyNode[HashableT]], Tuple[Type[AnyNode[HashableT]], ...]],
    ) -> bool:
        return self.has_ancestor_matching(lambda node: isinstance(node, ancestor_type))

    def has_ancestor_of_id(self, items: Iterable[HashableT]) -> bool:
        if not isinstance(items, Iterable):
            raise TypeError(f"Expected an iterable of items, got {type(items)}")

        item_ids = {id(item) for item in items}
        return self.has_ancestor_matching(lambda node: id(node.item) in item_ids)
