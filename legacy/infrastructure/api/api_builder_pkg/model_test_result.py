
"""
api_builder_pkg/model_test_result.py — ModelTestResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ModelTestResult:
    """Result of testing a model via the API builder."""
    model_key: str
    model_id: str
    provider: str
    available: bool = False
    latency_ms: float = 0.0
    response_quality: float = 0.0  # 0-100
    tokens_used: int = 0
    response_preview: str = ""
    error: Optional[str] = None
    tier: str = ""


# ═══════════════════════════════════════════════════════════════════
# Endpoint Registry
# ═══════════════════════════════════════════════════════════════════




