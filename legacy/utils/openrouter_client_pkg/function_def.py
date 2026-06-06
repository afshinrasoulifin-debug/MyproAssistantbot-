
"""
openrouter_client_pkg/function_def.py — FunctionDef
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class FunctionDef:
    """Function definition for LLM function calling."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI-compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }




