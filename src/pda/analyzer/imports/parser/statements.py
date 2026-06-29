import ast
from pathlib import Path
from typing import List, Union

from anytree import PreOrderIter

from pda.analyzer.imports.parser.scopes import ImportScopeResolver
from pda.models import ASTForest, ASTNode
from pda.specification import ImportPath, ImportStatement, SourceSpan


class ImportStatementParser:
    def __init__(self) -> None:
        self._scopes = ImportScopeResolver()

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
        scopes = self._scopes.determine(import_node)

        return [
            ImportStatement(
                origin=origin,
                span=span,
                path=import_path,
                scopes=scopes,
            )
            for import_path in import_paths
        ]
