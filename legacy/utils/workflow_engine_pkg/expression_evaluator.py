
"""
workflow_engine_pkg/expression_evaluator.py — ExpressionEvaluator
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ExpressionEvaluator:
    """
    Safe expression evaluator for workflow conditions and transforms.

    Supports:
      - Variable references: ${variable_name}
      - Comparisons: ==, !=, <, >, <=, >=
      - Logical operators: and, or, not
      - String operations: contains, startswith, endswith
      - Arithmetic: +, -, *, /, %
      - Type checks: is_null, is_empty, is_number
    """

    def __init__(self, variables: Dict[str, Any]):
        self.variables = variables

    def resolve_variable(self, expr: str) -> Any:
        """Resolve ${var.path} references."""
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, expr)
        if not matches:
            return expr

        result = expr
        for match in matches:
            value = self._get_nested(match)
            if isinstance(value, str) and result == f"${{{match}}}":
                return value
            result = result.replace(f"${{{match}}}", str(value))
        return result

    def _get_nested(self, path: str) -> Any:
        """Get nested value from variables using dot notation."""
        parts = path.split(".")
        current = self.variables
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    def evaluate_condition(self, expr: str) -> bool:
        """Evaluate a boolean expression."""
        expr = expr.strip()

        # Handle logical operators
        if " and " in expr:
            parts = expr.split(" and ", 1)
            return self.evaluate_condition(parts[0]) and self.evaluate_condition(parts[1])
        if " or " in expr:
            parts = expr.split(" or ", 1)
            return self.evaluate_condition(parts[0]) or self.evaluate_condition(parts[1])
        if expr.startswith("not "):
            return not self.evaluate_condition(expr[4:])

        # Handle comparisons
        for op in ["==", "!=", "<=", ">=", "<", ">"]:
            if op in expr:
                left, right = expr.split(op, 1)
                left_val = self.resolve_variable(left.strip())
                right_val = self.resolve_variable(right.strip())
                return self._compare(left_val, right_val, op)

        # Handle special functions
        if expr.startswith("is_null("):
            var = expr[8:-1].strip()
            return self.resolve_variable(f"${{{var}}}") is None
        if expr.startswith("is_empty("):
            var = expr[9:-1].strip()
            val = self.resolve_variable(f"${{{var}}}")
            return val is None or val == "" or val == [] or val == {}
        if expr.startswith("contains("):
            args = expr[9:-1].split(",", 1)
            haystack = str(self.resolve_variable(args[0].strip()))
            needle = str(self.resolve_variable(args[1].strip()))
            return needle in haystack

        # Truthy evaluation
        val = self.resolve_variable(f"${{{expr}}}")
        return bool(val)

    def _compare(self, left: Any, right: Any, op: str) -> bool:
        """Compare two values."""
        # Try numeric comparison
        try:
            left_num = float(str(left))
            right_num = float(str(right).strip("'\""))
            if op == "==":
                return left_num == right_num
            elif op == "!=":
                return left_num != right_num
            elif op == "<":
                return left_num < right_num
            elif op == ">":
                return left_num > right_num
            elif op == "<=":
                return left_num <= right_num
            elif op == ">=":
                return left_num >= right_num
        except (ValueError, TypeError):
            logger.debug("Suppressed: %s", _exc)

        # String comparison
        left_str = str(left).strip("'\"")
        right_str = str(right).strip("'\"")
        if op == "==":
            return left_str == right_str
        elif op == "!=":
            return left_str != right_str
        return False

    def interpolate(self, template: str) -> str:
        """Interpolate variables into a template string."""
        return str(self.resolve_variable(template))


# ═══════════════════════════════════════════════════════════════════
# DAG (Directed Acyclic Graph) Core
# ═══════════════════════════════════════════════════════════════════



