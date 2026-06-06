
"""
multi_llm_orchestrator_pkg/orchestration_result.py — OrchestrationResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class OrchestrationResult:
    """Complete result of an orchestration run."""
    mode: str
    final_response: str
    confidence: float
    models: List[ModelResponse]
    debate: Optional[List[DebateRound]] = None
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    cache_hit: bool = False
    task_category: str = ""
    selected_models: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Mode: {self.mode} | Models: {len(self.models)} | "
            f"Cost: ${self.total_cost:.4f} | Confidence: {self.confidence:.2f} | "
            f"Tokens: {self.total_tokens:,} | Latency: {self.total_latency_ms:.0f}ms"
        )




