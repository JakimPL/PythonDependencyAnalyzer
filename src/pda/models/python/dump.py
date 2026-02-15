import ast
from collections.abc import Sequence
from typing import Optional, Union


def ast_dump(node: ast.AST, short: bool = True) -> str:
    if not short:
        return ast.dump(node)

    fields = []
    for name, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            fields.append(f"{name}={value.__class__.__name__}")

        elif isinstance(value, (str, bytes)):
            fields.append(f"{name}={value!r}")

        elif isinstance(value, Sequence):
            if value and all(isinstance(v, ast.AST) for v in value):
                fields.append(f"{name}=<{len(value)}>")
            else:
                fields.append(f"{name}={value!r}")

        else:
            fields.append(f"{name}={value!r}")

    return f"{node.__class__.__name__}({', '.join(fields)})"


def _op_symbol(op: Union[ast.cmpop, ast.unaryop, ast.boolop, ast.operator]) -> str:
    return {
        ast.Add: "+",
        ast.Sub: "-",
        ast.Mult: "*",
        ast.MatMult: "@",
        ast.Div: "/",
        ast.FloorDiv: "//",
        ast.Mod: "%",
        ast.Pow: "**",
        ast.And: "and",
        ast.Or: "or",
        ast.Eq: "==",
        ast.NotEq: "!=",
        ast.Lt: "<",
        ast.LtE: "<=",
        ast.Gt: ">",
        ast.GtE: ">=",
        ast.Not: "not",
        ast.UAdd: "+",
        ast.USub: "-",
    }.get(type(op), type(op).__name__)


def _expr_name(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        base = _expr_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr

    if isinstance(node, ast.Call):
        return _expr_name(node.func)

    if isinstance(node, ast.Subscript):
        return _expr_name(node.value)

    return None


def ast_label(node: ast.AST) -> str:
    cls = node.__class__.__name__

    if isinstance(node, ast.alias):
        return f"alias({node.name} as {node.asname})" if node.asname else f"alias({node.name})"

    if isinstance(node, ast.ImportFrom):
        return f"ImportFrom({node.module or ''})"

    if isinstance(node, ast.Import):
        return "Import"

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return f"{cls}({node.name})"

    if isinstance(node, ast.Name):
        return f"Name({node.id})"

    if isinstance(node, ast.Attribute):
        full = _expr_name(node)
        return f"Attribute({full})" if full else f"Attribute({node.attr})"

    if isinstance(node, ast.arg):
        return f"arg({node.arg})"

    if isinstance(node, ast.keyword):
        return f"kw({node.arg})" if node.arg else "kw(**)"

    if isinstance(node, ast.Call):
        target = _expr_name(node.func)
        return f"Call({target})" if target else "Call"

    if isinstance(node, ast.Assign):
        targets = ", ".join(_expr_name(target) or target.__class__.__name__ for target in node.targets)
        return f"Assign({targets})"

    if isinstance(node, ast.withitem):
        ctx = _expr_name(node.context_expr)
        return f"with {ctx}" if ctx else "with"

    if isinstance(node, ast.BinOp):
        return f"BinOp({_op_symbol(node.op)})"

    if isinstance(node, ast.BoolOp):
        return f"BoolOp({_op_symbol(node.op)})"

    if isinstance(node, ast.UnaryOp):
        return f"UnaryOp({_op_symbol(node.op)})"

    if isinstance(node, ast.Compare) and node.ops:
        return f"Compare({_op_symbol(node.ops[0])})"

    if isinstance(node, ast.ExceptHandler):
        name = _expr_name(node.type)
        return f"ExceptHandler({name})" if name else "ExceptHandler"

    if isinstance(node, ast.Constant):
        return f"Constant({node.value!r})"

    for attr in ("name", "id", "attr", "arg"):
        value = getattr(node, attr, None)
        if isinstance(value, str):
            return f"{cls}({value})"

    return cls
