from __future__ import annotations

import ast
from typing import Any, DefaultDict, Dict, Set, TypeAlias

from fda.node.wrapper import ASTNodeWrapper

NodeWrapperMap: TypeAlias = Dict[ast.AST, ASTNodeWrapper[Any]]
FunctionCalls: TypeAlias = DefaultDict[ASTNodeWrapper[ast.FunctionDef], Set[ASTNodeWrapper[ast.Call]]]
SimplifiedFunctionCalls: TypeAlias = Dict[str, Set[str]]
CallResolutions: TypeAlias = Dict[ASTNodeWrapper[ast.Call], ASTNodeWrapper[Any]]
