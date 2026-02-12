from typing import TypeVar

from anytree import NodeMixin

AnyNodeT = TypeVar("AnyNodeT", bound=NodeMixin)
