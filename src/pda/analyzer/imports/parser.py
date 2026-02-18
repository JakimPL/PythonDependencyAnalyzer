import ast
from pathlib import Path
from typing import Any, List, Union

from anytree import PreOrderIter

from pda.analyzer.imports.special.main import is_main_guard_only
from pda.analyzer.imports.special.type_checking import is_type_checking_only
from pda.models import ASTForest, ASTNode
from pda.models.python.dump import ast_dump
from pda.specification import ImportPath, ImportScope, ImportStatement, SourceSpan


class ImportStatementParser:
    def __call__(self, origin: Path) -> List[ImportStatement]:
        tree = ASTForest([origin])
        import_nodes = self._find_import_nodes(tree)
        return self._retrieve_all_import_statements(origin, import_nodes)

    def _find_import_nodes(
        self,
        tree: ASTForest,
    ) -> List[ASTNode[Union[ast.Import, ast.ImportFrom]]]:
        return [node for node in tree.roots for node in PreOrderIter(node) if node.type in (ast.Import, ast.ImportFrom)]

    def _retrieve_all_import_statements(
        self,
        origin: Path,
        import_nodes: List[ASTNode[Union[ast.Import, ast.ImportFrom]]],
    ) -> List[ImportStatement]:
        statements: List[ImportStatement] = []
        for import_node in import_nodes:
            import_statements = self._create_import_statements(import_node, origin)
            statements.extend(import_statements)

        return statements

    def _create_import_statements(
        self,
        import_node: ASTNode[Union[ast.Import, ast.ImportFrom]],
        origin: Path,
    ) -> List[ImportStatement]:
        import_paths = ImportPath.from_ast(import_node.ast)
        span = SourceSpan.from_ast(import_node.ast)
        scopes = self._determine_scopes(import_node)

        return [
            ImportStatement(
                origin=origin,
                span=span,
                path=import_path,
                scopes=scopes,
            )
            for import_path in import_paths
        ]

    def _determine_scopes(self, node: ASTNode[Any]) -> List[ImportScope]:
        scopes: List[ImportScope] = []
        current = node.parent

        while current is not None:
            if not isinstance(current, ASTNode):
                current = current.parent
                continue

            scope = ImportScope.NONE
            match current.ast:
                case ast.If():
                    scope = self._handle_if_scope(node, current)
                    scope |= self._handle_type_checking_scope(node, current)
                    scope |= self._handle_main_guard_scope(node, current)
                case ast.Try():
                    scope = self._handle_try_scope(node, current)
                case ast.Match():
                    scope = self._handle_match_scope(node, current)
                case ast.For() | ast.While() | ast.ListComp() | ast.SetComp() | ast.DictComp() | ast.GeneratorExp():
                    scope = ImportScope.LOOP
                case ast.With():
                    scope = ImportScope.WITH
                case ast.FunctionDef() | ast.AsyncFunctionDef():
                    scope = self._handle_function_scope(current)
                case ast.ClassDef():
                    scope = ImportScope.CLASS

            if scope:
                scope.validate()
                scopes.append(scope)

            current = current.parent

        return scopes

    def _handle_if_scope(
        self,
        node: ASTNode[Any],
        if_node: ASTNode[ast.If],
    ) -> ImportScope:
        def is_ancestor_in_body(parent: ASTNode[Any]) -> bool:
            return parent.ast in if_node.ast.body

        def is_ancestor_in_orelse(parent: ASTNode[Any]) -> bool:
            return parent.ast in if_node.ast.orelse

        node_in_body = node.has_ancestor(is_ancestor_in_body, include_self=True)
        node_in_orelse = node.has_ancestor(is_ancestor_in_orelse, include_self=True)

        if node_in_body and node_in_orelse:
            raise ValueError(
                f"Import node {ast_dump(node.ast)} is child of If {ast_dump(if_node.ast)} and in both body and orelse"
            )

        if not node_in_body and not node_in_orelse:
            raise ValueError(
                f"Import node {ast_dump(node.ast)} is child of If {ast_dump(if_node.ast)} but not in its body or orelse"
            )

        return ImportScope.IF if node_in_body else ImportScope.ELSE

    def _handle_type_checking_scope(self, node: ASTNode[Any], if_node: ASTNode[ast.If]) -> ImportScope:
        def is_ancestor_in_orelse(parent: ASTNode[Any]) -> bool:
            return parent.ast in if_node.ast.orelse

        in_else_branch = node.has_ancestor(is_ancestor_in_orelse, include_self=True)

        if is_type_checking_only(if_node.ast, in_else_branch=in_else_branch):
            return ImportScope.TYPE_CHECKING

        return ImportScope.NONE

    def _handle_main_guard_scope(self, node: ASTNode[Any], if_node: ASTNode[ast.If]) -> ImportScope:
        def is_ancestor_in_orelse(parent: ASTNode[Any]) -> bool:
            return parent.ast in if_node.ast.orelse

        in_else_branch = node.has_ancestor(is_ancestor_in_orelse, include_self=True)

        if is_main_guard_only(if_node.ast, in_else_branch=in_else_branch):
            return ImportScope.MAIN

        return ImportScope.NONE

    def _handle_try_scope(self, node: ASTNode[Any], try_node: ASTNode[ast.Try]) -> ImportScope:
        except_handlers = try_node.ast.handlers

        def is_ancestor_in_body(parent: ASTNode[Any]) -> bool:
            return parent.ast in try_node.ast.body

        def is_ancestor_in_orelse(parent: ASTNode[Any]) -> bool:
            return parent.ast in try_node.ast.orelse

        def is_ancestor_in_except_handlers(parent: ASTNode[Any]) -> bool:
            return any(parent.ast in except_handler.body for except_handler in except_handlers)

        def is_ancestor_in_finally(parent: ASTNode[Any]) -> bool:
            return parent.ast in try_node.ast.finalbody

        node_in_body = node.has_ancestor(is_ancestor_in_body, include_self=True)
        node_in_orelse = node.has_ancestor(is_ancestor_in_orelse, include_self=True)
        node_in_except_handlers = node.has_ancestor(is_ancestor_in_except_handlers, include_self=True)
        node_in_finally = node.has_ancestor(is_ancestor_in_finally, include_self=True)

        flags = {
            node_in_body: ImportScope.TRY,
            node_in_orelse: ImportScope.TRY_ELSE,
            node_in_except_handlers: ImportScope.EXCEPT,
            node_in_finally: ImportScope.FINALLY,
        }

        if sum(flags) > 1:
            raise ValueError(
                f"Import node {ast_dump(node.ast)} is child of Try {ast_dump(try_node.ast)} and in multiple scopes"
            )

        if not any(flags):
            raise ValueError(
                f"Import node {ast_dump(node.ast)} is child of Try {ast_dump(try_node.ast)} "
                "but not in any of its scopes"
            )

        return next(scope for in_scope, scope in flags.items() if in_scope)

    def _handle_match_scope(self, node: ASTNode[Any], match_node: ASTNode[ast.Match]) -> ImportScope:
        def is_ancestor_in_case_body(parent: ASTNode[Any], *, case: ast.match_case) -> bool:
            return parent.ast in case.body

        match_cases = match_node.ast.cases
        for case in match_cases:

            if node.has_ancestor(is_ancestor_in_case_body, include_self=True, case=case):
                scope = ImportScope.CASE
                if isinstance(case.pattern, ast.MatchAs) and case.pattern.pattern is None:
                    scope |= ImportScope.DEFAULT

                return scope

        raise ValueError("Import node is child of Match but not in any of its cases")

    def _handle_function_scope(self, func_node: ASTNode[Union[ast.FunctionDef, ast.AsyncFunctionDef]]) -> ImportScope:
        scope = ImportScope.FUNCTION

        if func_node.ast.decorator_list:
            scope |= ImportScope.DECORATED_FUNCTION

        return scope
