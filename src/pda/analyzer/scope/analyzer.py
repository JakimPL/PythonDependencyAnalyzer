from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pda.analyzer.base import BaseAnalyzer
from pda.analyzer.scope.builder import ScopeBuilder
from pda.analyzer.scope.collector import SymbolCollector
from pda.config.analyzer.scope import ScopeAnalyzerConfig
from pda.models import ASTForest
from pda.models.scope.forest import ScopeForest
from pda.models.scope.node import ScopeNode
from pda.specification import Symbol
from pda.types import Pathlike


class ScopeAnalyzer(BaseAnalyzer[ScopeAnalyzerConfig, ScopeForest]):
    """
    Analyzes Python code to build complete scope hierarchies with populated symbol tables.

    This analyzer orchestrates:
    1. ScopeBuilder - creates scope structure
    2. SymbolCollector - extracts symbol definitions
    3. Assembly - populates scopes with collected symbols

    The result is a ScopeForest with complete symbol tables.
    """

    def __init__(
        self,
        config: Optional[ScopeAnalyzerConfig] = None,
        project_root: Optional[Pathlike] = None,
        package: Optional[str] = None,
    ) -> None:
        """
        Initialize the scope analyzer.

        Args:
            config: Optional configuration for the analyzer.
            project_root: Optional project root directory.
            package: Optional package name.
        """
        super().__init__(config=config, project_root=project_root, package=package)
        self._files: Optional[List[Path]] = None
        self._scope_forest: Optional[ScopeForest] = None
        self._symbols_by_scope: Dict[ScopeNode[Any], Dict[str, Symbol]] = {}

    def __bool__(self) -> bool:
        """Return True if the analyzer has processed data."""
        return self._scope_forest is not None

    def __call__(
        self,
        files: Optional[List[Pathlike]] = None,
        *,
        refresh: bool = False,
    ) -> ScopeForest:
        """
        Analyze Python files and build complete scope hierarchies.

        Args:
            files: List of Python file paths to analyze. If None, uses previously analyzed files.
            refresh: Force re-analysis even if files haven't changed.

        Returns:
            ScopeForest with complete symbol tables.

        Raises:
            ValueError: If no files have been analyzed yet and none are provided.
        """
        result = self._analyze_if_needed(files=files, refresh=refresh)
        return result

    def clear(self) -> None:
        """Clear the analyzer's internal state."""
        self._files = None
        self._scope_forest = None
        self._symbols_by_scope = {}

    def _analyze_if_needed(
        self,
        files: Optional[List[Pathlike]] = None,
        *,
        refresh: bool = False,
    ) -> ScopeForest:
        """
        Perform analysis if needed, optionally refreshing the data.

        Args:
            files: List of Python file paths to analyze. If None, uses previously analyzed files.
            refresh: Force re-analysis even if files haven't changed.

        Returns:
            The analyzed ScopeForest.

        Raises:
            ValueError: If no files have been analyzed yet and none are provided.
        """
        files_to_use: Optional[List[Path]] = self._resolve_paths(files or self._files)
        if not files_to_use:
            raise ValueError("No files have been analyzed yet")

        if self._scope_forest is None or refresh or self._files != files_to_use:
            self._analyze(files_to_use)

        assert self._scope_forest is not None, "Scope forest should have been populated after analysis"
        return self._scope_forest

    def _analyze(self, paths: List[Path]) -> None:
        """
        Perform the actual analysis.

        Args:
            file_paths: List of resolved Python file paths to analyze.
        """
        self.clear()

        self._files = paths
        forest = self._construct_ast_forest()

        builder = ScopeBuilder()
        self._scope_forest = builder(forest)

        collector = SymbolCollector()
        self._symbols_by_scope = collector(self._scope_forest)

        self._define_symbols()

    def _resolve_paths(self, paths: Optional[Union[List[Pathlike], List[Path]]]) -> List[Path]:
        """
        Resolve a list of paths to absolute Path objects.

        Args:
            paths: List of paths to resolve.

        Returns:
            List of resolved Path objects.
        """
        if paths is None:
            return []

        return [Path(path).resolve() for path in paths]

    def _construct_ast_forest(self) -> ASTForest:
        """
        Construct an ASTForest from the previously resolved file paths.

        Args:
            filepaths: List of resolved Python file paths to analyze.
        Returns:
            An ASTForest containing the parsed ASTs of the given files.
        """
        assert self._files is not None, "Files must be set before constructing AST forest"
        return ASTForest(self._files)

    def _define_symbols(self) -> None:
        for scope, symbols in self._symbols_by_scope.items():
            for name, symbol in symbols.items():
                scope.define(name, symbol)

    @classmethod
    def default_config(cls) -> ScopeAnalyzerConfig:
        """Return the default configuration for scope analysis."""
        return ScopeAnalyzerConfig()
