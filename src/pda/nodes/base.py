from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from typing import Callable, Dict, Generic, List, Optional, Self, Set, Tuple, Type, TypeVar, Union

import networkx as nx
from anytree import LevelOrderIter, NodeMixin

from pda.nodes.types import AnyNodeT
from pda.tools.ordered_set import OrderedSet
from pda.types import AnyT, HashableT

ItemT = TypeVar("ItemT")


class BaseNode(NodeMixin, Generic[ItemT]):  # type: ignore[misc]
    def __init__(self, item: ItemT, *, parent: Optional[BaseNode[ItemT]] = None) -> None:
        super().__init__()
        self.item: ItemT = item
        self.parent: Optional[BaseNode[ItemT]] = parent

    def has_ancestor_matching(self, predicate: Callable[[BaseNode[ItemT]], bool]) -> bool:
        current = self.parent
        while current:
            if predicate(current):
                return True

            current = current.parent

        return False

    def has_ancestor(self, ancestor: Union[BaseNode[ItemT], Iterable[BaseNode[ItemT]]]) -> bool:
        ancestors = {ancestor} if isinstance(ancestor, BaseNode) else set(ancestor)
        return self.has_ancestor_matching(lambda node: node in ancestors)

    def has_ancestor_of_type(
        self,
        ancestor_type: Union[Type[BaseNode[ItemT]], Tuple[Type[BaseNode[ItemT]], ...]],
    ) -> bool:
        return self.has_ancestor_matching(lambda node: isinstance(node, ancestor_type))

    def has_ancestor_of_id(self, items: Iterable[ItemT]) -> bool:
        if not isinstance(items, Iterable):
            raise ValueError(f"Expected an iterable of items, got {type(items)}")

        item_ids = {id(item) for item in items}
        return self.has_ancestor_matching(lambda node: id(node.item) in item_ids)


class BaseForest(ABC, Generic[HashableT, AnyT, AnyNodeT]):
    def __init__(self, items: Iterable[HashableT]) -> None:
        self._mapping: Dict[AnyT, AnyNodeT] = {}
        self._items: List[AnyT] = self._prepare_inputs(items)
        self._roots: Set[AnyNodeT] = set()
        self()

    @classmethod
    def from_item(cls, item: HashableT) -> Self:
        return cls([item])

    def __bool__(self) -> bool:
        return bool(self._mapping)

    def __call__(self) -> Set[AnyNodeT]:
        for item in self._items:
            self._build_tree(item)

        return self._roots

    def __iter__(self) -> Iterator[AnyNodeT]:
        for root in self._roots:
            yield from LevelOrderIter(root)

    def __getitem__(self, item: AnyT) -> AnyNodeT:
        item = self._prepare_item(item)
        return self._mapping[item]

    def _prepare_inputs(self, inputs: Iterable[HashableT]) -> List[AnyT]:
        items: OrderedSet[HashableT] = OrderedSet[HashableT](inputs)
        return list(map(self._prepare_input, items))

    @property
    def roots(self) -> Set[AnyNodeT]:
        return self._roots.copy()

    @property
    def mapping(self) -> Dict[AnyT, AnyNodeT]:
        return self._mapping.copy()

    @property
    def graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for node in self:
            item: AnyT = self.item(node)
            label: str = self.label(node)
            level: int = node.depth
            graph.add_node(item, label=label, rank=level, level=level)
            if node.parent is not None:
                parent_item = self.item(node.parent)
                edge_label = self.edge_label(node.parent, node)
                graph.add_edge(parent_item, item, label=edge_label)

        return graph

    @abstractmethod
    def label(self, node: AnyNodeT) -> str: ...

    @abstractmethod
    def item(self, node: AnyNodeT) -> AnyT: ...

    def edge_label(self, from_node: AnyNodeT, to_node: AnyNodeT) -> str:
        from_label = self.label(from_node)
        to_label = self.label(to_node)
        return f"{from_label} → {to_label}"

    @abstractmethod
    def _input_to_item(self, inp: HashableT) -> AnyT: ...

    def _prepare_input(self, inp: HashableT) -> AnyT:
        item = self._input_to_item(inp)
        return self._prepare_item(item)

    def _prepare_item(self, item: AnyT) -> AnyT:
        return item

    @abstractmethod
    def _build_tree(
        self,
        item: AnyT,
        parent: Optional[AnyNodeT] = None,
    ) -> None: ...

    def _add_node(
        self,
        item: AnyT,
        parent: Optional[AnyNodeT] = None,
    ) -> Optional[AnyNodeT]:
        if item in self._mapping:
            return self[item]

        node = self._create_node(item, parent=parent)
        self._mapping[item] = node
        return node

    @abstractmethod
    def _create_node(
        self,
        item: AnyT,
        parent: Optional[AnyNodeT] = None,
    ) -> AnyNodeT: ...

    def get(self, item: AnyT) -> Optional[AnyNodeT]:
        item = self._prepare_item(item)
        return self._mapping.get(item)
