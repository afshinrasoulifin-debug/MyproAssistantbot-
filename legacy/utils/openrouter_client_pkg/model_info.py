
"""
openrouter_client_pkg/model_info.py — ModelInfo
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ModelInfo:
    """Information about an LLM model."""
    id: str
    name: str
    provider: str
    tier: ModelTier
    context_length: int
    input_cost_per_1k: float  # USD per 1K tokens
    output_cost_per_1k: float
    supports_functions: bool = False
    supports_streaming: bool = True
    supports_vision: bool = False
    max_output_tokens: int = 4096
    speed_rating: float = 1.0  # relative speed (higher = faster)
    quality_rating: float = 1.0  # relative quality (higher = better)
    tags: List[str] = field(default_factory=list)

    def estimated_cost(self, input_tokens: int,
                       output_tokens: int) -> float:
        """Estimate cost for a request."""
        return (
            input_tokens / 1000 * self.input_cost_per_1k
            + output_tokens / 1000 * self.output_cost_per_1k
        )


# Free and budget models available on OpenRouter


