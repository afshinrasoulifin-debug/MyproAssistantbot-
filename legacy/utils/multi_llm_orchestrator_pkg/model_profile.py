
"""
multi_llm_orchestrator_pkg/model_profile.py — ModelProfile
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ModelProfile:
    """Detailed profile of an LLM model."""
    id: str
    name: str
    provider: str
    strengths: List[str]
    weaknesses: List[str]
    cost_per_1k_input: float        # USD
    cost_per_1k_output: float       # USD
    max_tokens: int
    context_window: int
    supports_vision: bool
    supports_tools: bool
    speed: str                      # fast | medium | slow
    quality: float                  # 1-10
    reliability: float              # 0-1 (uptime)
    avg_latency_ms: float
    refusal_rate: float             # 0-1
    tags: List[str] = field(default_factory=list)

    @property
    def cost_per_1k_total(self) -> float:
        return self.cost_per_1k_input + self.cost_per_1k_output




