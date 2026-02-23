from __future__ import annotations

import ast
from typing import Any, Dict, List, Union

from pda.analyzer.scope.scope import Scope
from pda.models import ASTNode
from pda.specification import SourceSpan, Symbol


class SymbolCollector:
    """
    Collects symbol definitions from an AST and populates scope symbol tables.

    This class walks the AST and registers all definitions (assignments,
    function/class definitions, parameters, etc.) in their appropriate scopes.
    """

    def __init__(self, scope_tree: Scope, node_to_scope: Dict[ASTNode[Any], Scope]) -> None:
        """
        Initialize the symbol collector.

        Args:
            scope_tree: The root scope from ScopeBuilder.
            node_to_scope: Mapping from ASTNode to its containing Scope (from ScopeBuilder).
        """
        self.scope_tree = scope_tree
        self.node_to_scope = node_to_scope

    def collect(self) -> None:
        """
        Walk the scope tree and collect all symbols into their respective scopes.
        """
        self._collect_in_scope(self.scope_tree)

    def _collect_in_scope(self, scope: Scope) -> None:
        """
        Collect symbols defined in a scope and recursively process child scopes.

        Args:
            scope: The scope to process.
        """
        self._visit_node(scope.node, scope)
        for child_scope in self._get_child_scopes(scope):
            self._collect_in_scope(child_scope)

    def _get_child_scopes(self, scope: Scope) -> List[Scope]:
        """
        Get all direct child scopes of a given scope.

        Args:
            scope: The parent scope.

        Returns:
            List of child Scope objects.
        """
        return [s for s in self.node_to_scope.values() if s.parent is scope]

    def _visit_node(self, node: ASTNode[Any], scope: Scope) -> None:
        """
        Visit a node and collect symbols it defines.

        Args:
            node: The ASTNode to visit.
            scope: The containing scope.
        """
        match node.ast:
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                self._collect_function(node, scope)
            case ast.ClassDef():
                self._collect_class(node, scope)
            case ast.Assign() | ast.AugAssign() | ast.AnnAssign():
                self._collect_assignment(node, scope)
            case ast.NamedExpr():
                self._collect_walrus(node, scope)
            case ast.For() | ast.AsyncFor():
                self._collect_for_target(node, scope)
            case ast.With() | ast.AsyncWith():
                self._collect_with_targets(node, scope)
            case ast.ExceptHandler():
                self._collect_exception_handler(node, scope)
            case ast.Match():
                self._collect_match_targets(node, scope)
            case _:
                pass

        for child in node.children:
            child_scope = self.node_to_scope.get(child, scope)
            if child_scope is scope:
                self._visit_node(child, scope)

    def _collect_function(self, node: ASTNode[Union[ast.FunctionDef, ast.AsyncFunctionDef]], scope: Scope) -> None:
        """
        Collect a function definition and its parameters.

        Args:
            node: The function definition node.
            scope: The scope where the function is defined (NOT the function's own scope).
        """
        func_def = node.ast
        self._define_symbol(func_def.name, func_def, scope)

        func_scope = self.node_to_scope.get(node)
        if func_scope is None:
            return

        self._collect_parameters(func_def.args, func_scope)

    def _collect_class(self, node: ASTNode[ast.ClassDef], scope: Scope) -> None:
        """
        Collect a class definition.

        Args:
            node: The class definition node.
            scope: The scope where the class is defined.
        """
        self._define_symbol(node.ast.name, node.ast, scope)

    def _collect_assignment(
        self,
        node: ASTNode[Union[ast.Assign, ast.AugAssign, ast.AnnAssign]],
        scope: Scope,
    ) -> None:
        """
        Collect assignment targets as symbols.

        Args:
            node: The assignment node.
            scope: The containing scope.
        """
        targets = self._get_assignment_targets(node.ast)
        for target in targets:
            self._collect_names_from_target(target, node.ast, scope)

    def _collect_walrus(self, node: ASTNode[ast.NamedExpr], scope: Scope) -> None:
        """
        Collect walrus operator assignment target.

        Args:
            node: The named expression node.
            scope: The containing scope.
        """
        target = node.ast.target
        if isinstance(target, ast.Name):
            self._define_symbol(target.id, node.ast, scope)

    def _collect_for_target(self, node: ASTNode[Union[ast.For, ast.AsyncFor]], scope: Scope) -> None:
        """
        Collect for loop target variables.

        Args:
            node: The for loop node.
            scope: The containing scope.
        """
        self._collect_names_from_target(node.ast.target, node.ast, scope)

    def _collect_with_targets(self, node: ASTNode[Union[ast.With, ast.AsyncWith]], scope: Scope) -> None:
        """
        Collect with statement target variables.

        Args:
            node: The with statement node.
            scope: The containing scope.
        """
        for item in node.ast.items:
            if item.optional_vars is not None:
                self._collect_names_from_target(item.optional_vars, node.ast, scope)

    def _collect_exception_handler(self, node: ASTNode[ast.ExceptHandler], scope: Scope) -> None:
        """
        Collect exception handler variable.

        Args:
            node: The exception handler node.
            scope: The containing scope.
        """
        if node.ast.name is not None:
            self._define_symbol(node.ast.name, node.ast, scope)

    def _collect_match_targets(self, node: ASTNode[ast.Match], scope: Scope) -> None:
        """
        Collect pattern variables from match cases.

        Args:
            node: The match statement node.
            scope: The containing scope.
        """
        for case in node.ast.cases:
            self._collect_names_from_pattern(case.pattern, case, scope)

    def _collect_parameters(self, args: ast.arguments, scope: Scope) -> None:
        """
        Collect function parameters as symbols.

        Args:
            args: The function arguments node.
            scope: The function's scope.
        """
        all_args: List[ast.arg] = []

        if args.posonlyargs:
            all_args.extend(args.posonlyargs)
        if args.args:
            all_args.extend(args.args)
        if args.vararg:
            all_args.append(args.vararg)
        if args.kwonlyargs:
            all_args.extend(args.kwonlyargs)
        if args.kwarg:
            all_args.append(args.kwarg)

        for arg in all_args:
            self._define_symbol(arg.arg, arg, scope)

    def _get_assignment_targets(self, node: Union[ast.Assign, ast.AugAssign, ast.AnnAssign]) -> List[ast.expr]:
        """
        Extract target expressions from an assignment node.

        Args:
            node: The assignment node.

        Returns:
            List of target expressions.
        """
        match node:
            case ast.Assign():
                return node.targets
            case ast.AugAssign():
                return [node.target]
            case ast.AnnAssign():
                return [node.target] if node.target else []
            case _:
                return []

    def _collect_names_from_target(self, target: ast.expr, def_node: ast.AST, scope: Scope) -> None:
        """
        Recursively extract names from an assignment target.

        Handles: Name, Tuple, List (unpacking).

        Args:
            target: The target expression.
            def_node: The defining node (for creating Symbol).
            scope: The containing scope.
        """
        match target:
            case ast.Name():
                self._define_symbol(target.id, def_node, scope)
            case ast.Tuple() | ast.List():
                for elt in target.elts:
                    self._collect_names_from_target(elt, def_node, scope)
            case _:
                pass

    def _collect_names_from_pattern(self, pattern: ast.pattern, def_node: ast.AST, scope: Scope) -> None:
        """
        Recursively extract names from a match pattern.

        Args:
            pattern: The pattern node.
            def_node: The defining node (case node).
            scope: The containing scope.
        """
        match pattern:
            case ast.MatchAs():
                if pattern.name is not None:
                    self._define_symbol(pattern.name, def_node, scope)
                if pattern.pattern is not None:
                    self._collect_names_from_pattern(pattern.pattern, def_node, scope)
            case ast.MatchOr():
                for subpattern in pattern.patterns:
                    self._collect_names_from_pattern(subpattern, def_node, scope)
            case ast.MatchSequence():
                for subpattern in pattern.patterns:
                    self._collect_names_from_pattern(subpattern, def_node, scope)
            case ast.MatchMapping():
                for subpattern in pattern.patterns:
                    self._collect_names_from_pattern(subpattern, def_node, scope)
                if pattern.rest is not None:
                    self._define_symbol(pattern.rest, def_node, scope)
            case ast.MatchClass():
                for subpattern in pattern.patterns:
                    self._collect_names_from_pattern(subpattern, def_node, scope)
                for subpattern in pattern.kwd_patterns:
                    self._collect_names_from_pattern(subpattern, def_node, scope)
            case ast.MatchStar():
                if pattern.name is not None:
                    self._define_symbol(pattern.name, def_node, scope)
            case _:
                pass

    def _define_symbol(self, name: str, node: ast.AST, scope: Scope) -> None:
        """
        Create a Symbol and register it in the scope.

        Args:
            name: The symbol name.
            node: The AST node defining this symbol.
            scope: The scope to register the symbol in.
        """
        fqn_prefix = scope.get_fqn_prefix()
        fqn = f"{fqn_prefix}.{name}" if fqn_prefix else name

        symbol = Symbol(
            node=node,
            fqn=fqn,
            origin=scope.origin,
            span=SourceSpan.from_ast(node),
        )

        scope.define(name, symbol)
