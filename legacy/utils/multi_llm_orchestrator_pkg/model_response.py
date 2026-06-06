
"""
multi_llm_orchestrator_pkg/model_response.py — ModelResponse
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ModelResponse:
    """Response from a single model call."""
    model: str
    content: str
    confidence: float               # 0-1
    tokens: Dict[str, int]          # {input, output}
    cost: float                     # USD
    latency_ms: float
    refusal: bool
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.tokens.get("input", 0) + self.tokens.get("output", 0)




