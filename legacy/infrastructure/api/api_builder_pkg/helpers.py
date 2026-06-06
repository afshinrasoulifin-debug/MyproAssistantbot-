
"""
api_builder_pkg/helpers.py — standalone functions
Arki Engine v29.0.0
"""
from ._base import *  # noqa

def _safe_eval_condition(expr: str, prev_output: Any) -> bool:
    """Evaluate a pipeline condition expression safely via AST.

    Allowed: comparisons, bool ops, len(), string/number literals, prev_output.
    Blocked: function calls (except len), imports, attribute access.

    Examples:
        "len(prev_output) > 0"
        "prev_output != ''"
        "True"
    """
    try:
        tree = _ast.parse(expr, mode="eval")
    except SyntaxError:
        raise ValueError(f"Invalid condition syntax: {expr}")

    _allowed_names = {"prev_output": prev_output, "True": True, "False": False, "None": None}

    def _eval_node(node):
        # Literals: numbers, strings, bools, None
        if isinstance(node, _ast.Constant):
            return node.value

        # Name references: prev_output, True, False, None
        if isinstance(node, _ast.Name):
            if node.id in _allowed_names:
                return _allowed_names[node.id]
            raise ValueError(f"Forbidden name in condition: {node.id}")

        # Function calls: ONLY len() allowed
        if isinstance(node, _ast.Call):
            if isinstance(node.func, _ast.Name) and node.func.id == "len" and len(node.args) == 1:
                return len(_eval_node(node.args[0]))
            raise ValueError(f"Only len() is allowed in conditions")

        # Comparisons: a > b, a == b, etc.
        if isinstance(node, _ast.Compare):
            left = _eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                op_func = _SAFE_OPS.get(type(op))
                if not op_func:
                    raise ValueError(f"Unsupported operator: {type(op).__name__}")
                right = _eval_node(comparator)
                if not op_func(left, right):
                    return False
                left = right
            return True

        # Bool ops: and, or
        if isinstance(node, _ast.BoolOp):
            if isinstance(node.op, _ast.And):
                return all(_eval_node(v) for v in node.values)
            if isinstance(node.op, _ast.Or):
                return any(_eval_node(v) for v in node.values)

        # Unary: not
        if isinstance(node, _ast.UnaryOp) and isinstance(node.op, _ast.Not):
            return not _eval_node(node.operand)

        # Binary ops: +, -, *
        if isinstance(node, _ast.BinOp):
            op_func = _SAFE_OPS.get(type(node.op))
            if op_func:
                return op_func(_eval_node(node.left), _eval_node(node.right))

        # Expression wrapper
        if isinstance(node, _ast.Expression):
            return _eval_node(node.body)

        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    return bool(_eval_node(tree))


# ═══════════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═══════════════════════════════════════════════════════════════════


def get_api_builder() -> APIBuilderAgent:
    """Get the singleton API Builder agent."""
    global _builder
    if _builder is None:
        _builder = APIBuilderAgent()
    return _builder




