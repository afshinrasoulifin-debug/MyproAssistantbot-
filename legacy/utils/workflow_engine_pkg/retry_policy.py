
"""
workflow_engine_pkg/retry_policy.py — RetryPolicy
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class RetryPolicy:
    """Retry configuration for a node."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    retry_on: Optional[List[str]] = None  # exception types

    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(
            self.initial_delay * (self.backoff_factor ** attempt),
            self.max_delay,
        )
        # Add jitter (±25%)
        jitter = delay * 0.25
        return delay + (hash(str(attempt)) % 100 / 100.0 - 0.5) * 2 * jitter




