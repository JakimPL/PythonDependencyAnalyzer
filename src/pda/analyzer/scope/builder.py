from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional

from pda.analyzer.scope.scope import Scope
from pda.exceptions import PDAEmptyScopeError, PDAMissingScopeOriginError
from pda.models import ASTForest, ASTNode
from pda.specification import ScopeType


class ScopeBuilder:
    """
    Builds a scope hierarchy from an AST by walking the tree and creating
    scopes for modules, classes, functions, lambdas, and comprehensions.

    This class does NOT populate symbol tables - it only creates the scope
    structure. Symbol collection happens in a separate phase.
    """

    def __init__(self, forest: ASTForest) -> None:
        """
        Initialize the scope builder.

        Args:
            forest: The ASTForest containing wrapped AST nodes with their origins.
        """
        self.forest = forest
        self.node_to_scope: Dict[ASTNode[Any], Scope] = {}
        self.scope_tree: Optional[Scope] = None
        self._current_scope: Optional[Scope] = None
        self._current_origin: Optional[Path] = None

    def build(self) -> Scope:
        """
        Build the scope hierarchy by walking the AST.

        Returns:
            The root module scope (if single file) or first module scope (if multiple files).
        """
        for root in self.forest.roots:
            self._visit_node(root)

        if self.scope_tree is None:
            raise PDAEmptyScopeError("Failed to build scope tree - no module found")

        return self.scope_tree

    def _visit_node(self, node: ASTNode[Any]) -> None:
        """
        Visit a node and its children, creating scopes as needed.

        Args:
            node: The ASTNode to visit.
        """
        match node.ast:
            case ast.Module():
                self._visit_module(node)
            case ast.ClassDef():
                self._visit_with_new_scope(node, ScopeType.CLASS)
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                self._visit_with_new_scope(node, ScopeType.FUNCTION)
            case ast.Lambda():
                self._visit_with_new_scope(node, ScopeType.LAMBDA)
            case ast.ListComp() | ast.SetComp() | ast.DictComp() | ast.GeneratorExp():
                self._visit_with_new_scope(node, ScopeType.COMPREHENSION)
            case _:
                self._map_node_to_current_scope(node)
                self._visit_children(node)

    def _visit_module(self, node: ASTNode[ast.Module]) -> None:
        """
        Visit a Module node and create a MODULE scope.

        Args:
            node: The Module ASTNode.
        """
        origin = self.forest.get_origin(node)
        if origin is None:
            raise PDAMissingScopeOriginError(f"Cannot find origin for module node {node}")

        module_scope = Scope(
            scope_type=ScopeType.MODULE,
            node=node,
            origin=origin,
            parent=None,
        )

        self.scope_tree = module_scope
        self._current_scope = module_scope
        self._current_origin = origin
        self._map_node_to_current_scope(node)
        self._visit_children(node)

    def _visit_with_new_scope(self, node: ASTNode[Any], scope_type: ScopeType) -> None:
        """
        Visit a node that creates a new scope (class, function, lambda, comprehension).

        Args:
            node: The ASTNode that creates a new scope.
            scope_type: The type of scope to create.
        """
        if self._current_origin is None:
            raise PDAMissingScopeOriginError("Cannot create scope without current origin")

        new_scope = Scope(
            scope_type=scope_type,
            node=node,
            origin=self._current_origin,
            parent=self._current_scope,
        )

        self._map_node_to_current_scope(node)
        previous_scope = self._current_scope
        self._current_scope = new_scope
        self._visit_children(node)
        self._current_scope = previous_scope

    def _visit_children(self, node: ASTNode[Any]) -> None:
        """
        Visit all children of a node.

        Args:
            node: The parent ASTNode.
        """
        for child in node.children:
            self._visit_node(child)

    def _map_node_to_current_scope(self, node: ASTNode[Any]) -> None:
        """
        Map a node to the current scope.

        Args:
            node: The ASTNode to map.
        """
        if self._current_scope is not None:
            self.node_to_scope[node] = self._current_scope

    def get_scope(self, node: ASTNode[Any]) -> Optional[Scope]:
        """
        Get the scope for a given AST node.

        Args:
            node: The ASTNode to look up.

        Returns:
            The Scope containing this node, or None if not found.
        """
        return self.node_to_scope.get(node)

    def get_all_scopes(self) -> List[Scope]:
        """
        Get all unique scopes in the tree.

        Returns:
            List of all unique Scope objects.
        """
        return list(set(self.node_to_scope.values()))
