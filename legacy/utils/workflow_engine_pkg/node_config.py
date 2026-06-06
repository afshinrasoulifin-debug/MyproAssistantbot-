
"""
workflow_engine_pkg/node_config.py — NodeConfig
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class NodeConfig:
    """Configuration for a workflow node."""
    timeout_seconds: float = 300.0
    retry_policy: Optional[RetryPolicy] = None
    cache_result: bool = False
    skip_on_error: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)




