import ast
from pathlib import Path
from typing import Any, List, Union, cast

from anytree import PreOrderIter

from pda.nodes.python.forest import ASTForest
from pda.nodes.python.node import ASTNode
from pda.specification import ImportStatement
from pda.specification.imports.path import ImportPath
from pda.specification.imports.scope import ImportScope
from pda.specification.source.span import SourceSpan


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
        scope = self._determine_scope(import_node)

        return [
            ImportStatement(
                origin=origin,
                span=span,
                path=import_path,
                scope=scope,
            )
            for import_path in import_paths
        ]

    def _determine_scope(self, node: ASTNode[Any]) -> ImportScope:
        scope = ImportScope.NONE
        current = node.parent

        while current is not None:
            if not isinstance(current, ASTNode):
                current = current.parent
                continue

            match current.ast:
                case ast.If():
                    if node.has_ancestor_of_id(current.ast.orelse):
                        scope |= ImportScope.ELSE
                    else:
                        scope |= ImportScope.IF

                    if self._is_type_checking_condition(cast(ASTNode[ast.If], current)):
                        scope |= ImportScope.TYPE_CHECKING
                    elif self._is_main_condition(cast(ASTNode[ast.If], current)):
                        scope |= ImportScope.MAIN

                case ast.Try():
                    if node.has_ancestor_of_id(current.ast.finalbody):
                        scope |= ImportScope.FINALLY
                    elif any(node.has_ancestor_of_id(handler.body) for handler in current.ast.handlers):
                        scope |= ImportScope.EXCEPT
                    else:
                        scope |= ImportScope.TRY

                case ast.Match():
                    for case in current.ast.cases:
                        if node.has_ancestor_of_id(case.body):
                            if isinstance(case.pattern, ast.MatchAs) and case.pattern.pattern is None:
                                scope |= ImportScope.DEFAULT
                            else:
                                scope |= ImportScope.CASE
                            break

                case ast.For() | ast.While() | ast.ListComp() | ast.SetComp() | ast.DictComp() | ast.GeneratorExp():
                    scope |= ImportScope.LOOP

                case ast.With():
                    scope |= ImportScope.WITH

                case ast.FunctionDef() | ast.AsyncFunctionDef():
                    if node.has_ancestor_of_id(current.ast.decorator_list):
                        scope |= ImportScope.DECORATOR
                    else:
                        scope |= ImportScope.FUNCTION

                case ast.ClassDef():
                    scope |= ImportScope.CLASS

            current = current.parent

        scope.validate()
        return scope

    def _is_type_checking_condition(self, if_node: ASTNode[ast.If]) -> bool:
        test = if_node.ast.test
        return self._references_type_checking(test)

    def _references_type_checking(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id == "TYPE_CHECKING"

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return node.value.id == "typing" and node.attr == "TYPE_CHECKING"

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self._references_type_checking(node.operand)

        if isinstance(node, ast.BoolOp):
            return any(self._references_type_checking(value) for value in node.values)

        if isinstance(node, ast.Compare):
            if self._references_type_checking(node.left):
                return True

            return any(self._references_type_checking(comp) for comp in node.comparators)

        return False

    def _is_main_condition(self, if_node: ASTNode[ast.If]) -> bool:
        test = if_node.ast.test
        return self._checks_name_main(test)

    def _checks_name_main(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Compare):
            left_is_name = isinstance(node.left, ast.Name) and node.left.id == "__name__"
            right_is_main = any(
                isinstance(comp, ast.Constant) and comp.value == "__main__" for comp in node.comparators
            )
            return left_is_name and right_is_main

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return self._checks_name_main(node.operand)

        if isinstance(node, ast.BoolOp):
            return any(self._checks_name_main(value) for value in node.values)

        return False
