from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from pda.models.python.dump import ast_dump
from pda.models.python.node import ASTNode
from pda.specification import ScopeType, Symbol
from pda.structures import AnyNode
from pda.types import ASTT


class ScopeNode(AnyNode[ASTNode[ASTT]]):
    """
    Represents a Python scope with its symbol table.

    A scope tracks local definitions and imported symbols, and maintains
    a reference to its parent scope for hierarchical name resolution.
    """

    parent: Optional[ScopeNode[ASTT]]

    def __init__(
        self,
        scope_type: ScopeType,
        node: ASTNode[ASTT],
        origin: Path,
        *,
        parent: Optional[ScopeNode[ASTT]] = None,
        label: Optional[str] = None,
    ) -> None:
        """
        Initialize a new scope.

        Args:
            scope_type: The type of this scope (MODULE, CLASS, FUNCTION, etc.).
            node: The AST node that created this scope.
            origin: The file path where this scope is defined.
            parent: The enclosing parent scope (None for module scope).
            label: The label for this scope node (if None, defaults to node.label).
        """
        label = label or node.label
        details = node.details
        group = node.group
        super().__init__(
            item=node,
            parent=parent,
            ordinal=id(node),
            label=label,
            details=details,
            group=group,
        )
        self.scope_type = scope_type
        self.origin = origin
        self.symbols: Dict[str, Symbol] = {}
        self.imports: Dict[str, Symbol] = {}

    @property
    def node(self) -> ASTNode[ASTT]:
        """Get the AST node that created this scope."""
        return self.item

    def get_parent_scope(self) -> Optional[ScopeNode[Any]]:
        """Get the parent scope with proper type narrowing."""
        if self.parent is None:
            return None

        assert isinstance(self.parent, ScopeNode)
        return self.parent

    def define(self, name: str, symbol: Symbol) -> None:
        """
        Add a local definition to this scope.

        Args:
            name: The symbol name.
            symbol: The Symbol object containing definition information.
        """
        self.symbols[name] = symbol

    def import_symbol(self, name: str, symbol: Symbol) -> None:
        """
        Add an imported symbol to this scope.

        Args:
            name: The local name (may be aliased).
            symbol: The Symbol object from the imported module.
        """
        self.imports[name] = symbol

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """
        Look up a name only in this scope, without walking up the scope chain.

        Args:
            name: The name to look up.

        Returns:
            Symbol if found in this scope (checking both local definitions
            and imports), None otherwise.
        """
        if name in self.symbols:
            return self.symbols[name]

        if name in self.imports:
            return self.imports[name]

        return None

    def lookup(self, name: str) -> Optional[Symbol]:
        """
        Look up a name in this scope and walk up the scope chain if not found.

        This implements Python's LEGB rule (Local, Enclosing, Global, Built-in),
        but without built-ins. Note that class scopes are skipped when looking
        up from function scopes (Python semantics).

        Args:
            name: The name to look up.

        Returns:
            Symbol if found in this scope or any parent scope, None otherwise.
        """
        symbol = self.lookup_local(name)
        if symbol is not None:
            return symbol

        parent_scope = self.get_parent_scope()
        if parent_scope is not None:
            if self.scope_type == ScopeType.FUNCTION and parent_scope.scope_type == ScopeType.CLASS:
                grandparent_scope = parent_scope.get_parent_scope()
                if grandparent_scope is not None:
                    return grandparent_scope.lookup(name)

                return None

            return parent_scope.lookup(name)

        return None

    def lookup_nonlocal(self, name: str) -> Optional[Symbol]:
        """
        Look up a name for nonlocal/closure resolution, skipping module and class scopes.

        This is used for resolving names in nested functions where 'nonlocal'
        might be used. It skips module-level and class-level scopes.

        Args:
            name: The name to look up.

        Returns:
            Symbol if found in enclosing function scopes, None otherwise.
        """
        current: Optional[ScopeNode[Any]] = self.parent

        while current is not None:
            if current.scope_type in (ScopeType.MODULE, ScopeType.CLASS):
                current = current.parent
                continue

            symbol = current.lookup_local(name)
            if symbol is not None:
                return symbol

            current = current.parent

        return None

    def get_fqn_prefix(self) -> str:
        """
        Get the fully qualified name prefix for symbols defined in this scope.

        Returns:
            String like "module.path.ClassName" or "module.path".
        """
        parent_prefix = self.parent.get_fqn_prefix() if self.parent else ""
        if hasattr(self.node.ast, "name"):
            node_name = str(self.node.ast.name)
            if parent_prefix:
                return f"{parent_prefix}.{node_name}"

            return node_name

        return parent_prefix

    def __repr__(self) -> str:
        """String representation for debugging."""
        node_info = ast_dump(self.node.ast)
        return f"Scope({self.scope_type.value}, {node_info}, {len(self.symbols)} symbols, {len(self.imports)} imports)"
