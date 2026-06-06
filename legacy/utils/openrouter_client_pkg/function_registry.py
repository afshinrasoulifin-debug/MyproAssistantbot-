
"""
openrouter_client_pkg/function_registry.py — FunctionRegistry
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class FunctionRegistry:
    """Registry of callable functions."""

    def __init__(self) -> None:
        self.functions: Dict[str, FunctionDef] = {}

    def register(self, func_def: FunctionDef) -> None:
        self.functions[func_def.name] = func_def

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get all function schemas for API request."""
        return [f.to_openai_schema() for f in self.functions.values()]

    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a registered function."""
        func_def = self.functions.get(name)
        if not func_def or not func_def.handler:
            raise ValueError(f"Function not found or no handler: {name}")
        return func_def.handler(**arguments)


# ═══════════════════════════════════════════════════════════════════
# OpenRouter Client (Main Interface)
# ═══════════════════════════════════════════════════════════════════



