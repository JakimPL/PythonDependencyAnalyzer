from typing import Any

from pda.models.scope.node import ScopeNode
from pda.structures import AnyNode, Forest


class ScopeForest(Forest[AnyNode[Any], ScopeNode[Any]]):
    """
    A forest of scope trees, typically containing multiple module scopes.

    This is used when analyzing multiple Python files, where each file
    has its own module scope as a root.
    """

    def edge_label(self, from_node: ScopeNode[Any], to_node: ScopeNode[Any]) -> str:
        """
        Get the edge label between two scopes.

        Args:
            from_node: The parent scope.
            to_node: The child scope.

        Returns:
            A label describing the relationship.
        """
        return f"{from_node.scope_type.value}:{from_node.label} → {to_node.scope_type.value}:{to_node.label}"
