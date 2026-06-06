
"""
api_builder_pkg/endpoint_test_result.py — EndpointTestResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class EndpointTestResult:
    """Result of testing an endpoint."""
    endpoint_id: str
    test_name: str
    passed: bool
    model_used: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    request: Dict[str, Any] = field(default_factory=dict)
    response: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    quality_score: float = 0.0  # 0-100




