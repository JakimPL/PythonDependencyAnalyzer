import ast
from typing import Any, Dict, List, Optional, Union

from pda.models import ASTNode
from pda.models.scope.forest import ScopeForest
from pda.models.scope.node import ScopeNode
from pda.specification import SourceSpan, Symbol


class SymbolCollector:
    """
    Collects symbol definitions from an AST and returns them as data.

    This class walks the AST and extracts all definitions (assignments,
    function/class definitions, parameters, etc.) without mutating scopes.
    """

    def __init__(self) -> None:
        """
        Initialize the symbol collector.
        """
        self._scope_forest: Optional[ScopeForest] = None
        self._symbols_by_scope: Dict[ScopeNode[Any], Dict[str, Symbol]] = {}

    def __call__(self, scope_forest: ScopeForest) -> Dict[ScopeNode[Any], Dict[str, Symbol]]:
        """
        Collect all symbols and return them as data.

        Returns:
            Dictionary mapping each scope to its symbols {name: Symbol}.
        """
        self._scope_forest = scope_forest
        self._symbols_by_scope = {}

        for root_scope in scope_forest.roots:
            self._collect_in_scope(root_scope)

        return self._symbols_by_scope

    def _collect_in_scope(
        self,
        scope: ScopeNode[Any],
    ) -> None:
        """
        Collect symbols defined in a scope and recursively process child scopes.

        Args:
            scope: The scope to process.
        """
        if scope not in self._symbols_by_scope:
            self._symbols_by_scope[scope] = {}

        self._visit_scope_body(scope.node, scope)
        for child_scope in scope.children:
            self._collect_in_scope(child_scope)

    def _visit_scope_body(
        self,
        node: ASTNode[Any],
        scope: ScopeNode[Any],
    ) -> None:
        """
        Visit the body of a scope (not the defining node itself).

        Visits all children nodes in this scope. For nodes that define their own
        scopes (functions, classes), the name is collected in the current scope,
        but the contents are collected when that child scope is visited recursively.

        Args:
            node: The scope's defining node.
            scope: The scope to collect symbols in.
        """
        for child in node.children:
            self._visit_node(child, scope)

    def _visit_node(
        self,
        node: ASTNode[Any],
        scope: ScopeNode[Any],
    ) -> None:
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

    def _collect_function(
        self,
        node: ASTNode[Union[ast.FunctionDef, ast.AsyncFunctionDef]],
        scope: ScopeNode[Any],
    ) -> None:
        """
        Collect a function definition and its parameters.

        Args:
            node: The function definition node.
            scope: The scope where the function is defined (NOT the function's own scope).
            symbols_by_scope: Dictionary to populate with symbols.
        """
        func_def = node.ast
        self._define_symbol(func_def.name, func_def, scope)

        assert self._scope_forest is not None, "Scope forest must be set before collecting symbols"
        func_scope = self._scope_forest.get(node)
        if func_scope is None:
            return

        if func_scope not in self._symbols_by_scope:
            self._symbols_by_scope[func_scope] = {}

        self._collect_parameters(func_def.args, func_scope)

    def _collect_class(
        self,
        node: ASTNode[ast.ClassDef],
        scope: ScopeNode[Any],
    ) -> None:
        """
        Collect a class definition.

        Args:
            node: The class definition node.
            scope: The scope where the class is defined.
            symbols_by_scope: Dictionary to populate with symbols.
        """
        self._define_symbol(node.ast.name, node.ast, scope)

    def _collect_assignment(
        self,
        node: ASTNode[Union[ast.Assign, ast.AugAssign, ast.AnnAssign]],
        scope: ScopeNode[Any],
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

    def _collect_walrus(
        self,
        node: ASTNode[ast.NamedExpr],
        scope: ScopeNode[Any],
    ) -> None:
        """
        Collect walrus operator assignment target.

        Args:
            node: The named expression node.
            scope: The containing scope.
            symbols_by_scope: Dictionary to populate with symbols.
        """
        target = node.ast.target
        if isinstance(target, ast.Name):
            self._define_symbol(target.id, node.ast, scope)

    def _collect_for_target(
        self,
        node: ASTNode[Union[ast.For, ast.AsyncFor]],
        scope: ScopeNode[Any],
    ) -> None:
        """
        Collect for loop target variables.

        Args:
            node: The for loop node.
            scope: The containing scope.
        """
        self._collect_names_from_target(node.ast.target, node.ast, scope)

    def _collect_with_targets(
        self,
        node: ASTNode[Union[ast.With, ast.AsyncWith]],
        scope: ScopeNode[Any],
    ) -> None:
        """
        Collect with statement target variables.

        Args:
            node: The with statement node.
            scope: The containing scope.
        """
        for item in node.ast.items:
            if item.optional_vars is not None:
                self._collect_names_from_target(item.optional_vars, node.ast, scope)

    def _collect_exception_handler(
        self,
        node: ASTNode[ast.ExceptHandler],
        scope: ScopeNode[Any],
    ) -> None:
        """
        Collect exception handler variable.

        Args:
            node: The exception handler node.
            scope: The containing scope.
        """
        if node.ast.name is not None:
            self._define_symbol(node.ast.name, node.ast, scope)

    def _collect_match_targets(
        self,
        node: ASTNode[ast.Match],
        scope: ScopeNode[Any],
    ) -> None:
        """
        Collect pattern variables from match cases.

        Args:
            node: The match statement node.
            scope: The containing scope.
        """
        for case in node.ast.cases:
            self._collect_names_from_pattern(case.pattern, case, scope)

    def _collect_parameters(
        self,
        args: ast.arguments,
        scope: ScopeNode[Any],
    ) -> None:
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

    def _collect_names_from_target(
        self,
        target: ast.expr,
        def_node: ast.AST,
        scope: ScopeNode[Any],
    ) -> None:
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

    def _collect_names_from_pattern(
        self,
        pattern: ast.pattern,
        def_node: ast.AST,
        scope: ScopeNode[Any],
    ) -> None:
        """
        Recursively extract names from a match pattern.

        Args:
            pattern: The pattern node.
            def_node: The defining node (case node).
            scope: The containing scope..
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

    def _define_symbol(self, name: str, node: ast.AST, scope: ScopeNode[Any]) -> None:
        """
        Create a Symbol and add it to the dictionary.

        Args:
            name: The symbol name.
            node: The AST node defining this symbol.
            scope: The scope this symbol belongs to.
        """
        fqn_prefix = scope.get_fqn_prefix()
        fqn = f"{fqn_prefix}.{name}" if fqn_prefix else name

        symbol = Symbol(
            node=node,
            fqn=fqn,
            origin=scope.origin,
            span=SourceSpan.from_ast(node),
        )

        if scope not in self._symbols_by_scope:
            self._symbols_by_scope[scope] = {}

        self._symbols_by_scope[scope][name] = symbol
