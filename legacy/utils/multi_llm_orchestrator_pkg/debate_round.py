
"""
multi_llm_orchestrator_pkg/debate_round.py — DebateRound
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class DebateRound:
    """One round of model debate."""
    round: int
    responses: List[ModelResponse]
    synthesis: str = ""
    consensus: bool = False
    avg_confidence: float = 0.0




