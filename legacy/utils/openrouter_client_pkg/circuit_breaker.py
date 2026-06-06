
"""
openrouter_client_pkg/circuit_breaker.py — CircuitBreaker
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CircuitBreaker:
    """
    Circuit breaker for failing models.

    States: CLOSED (normal) → OPEN (blocking) → HALF_OPEN (testing)
    """

    def __init__(self, failure_threshold: int = 3,
                 recovery_timeout: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.states: Dict[str, str] = {}  # model -> state
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.last_failure: Dict[str, float] = {}

    def can_use(self, model: str) -> bool:
        """Check if a model can be used."""
        state = self.states.get(model, "closed")

        if state == "closed":
            return True
        elif state == "open":
            # Check if recovery timeout has passed
            if time.time() - self.last_failure.get(model, 0) > self.recovery_timeout:
                self.states[model] = "half_open"
                return True
            return False
        elif state == "half_open":
            return True

        return True

    def record_success(self, model: str) -> None:
        """Record successful request."""
        self.failure_counts[model] = 0
        self.states[model] = "closed"

    def record_failure(self, model: str) -> None:
        """Record failed request."""
        self.failure_counts[model] += 1
        self.last_failure[model] = time.time()

        if self.failure_counts[model] >= self.failure_threshold:
            self.states[model] = "open"


# ═══════════════════════════════════════════════════════════════════
# Model Router
# ═══════════════════════════════════════════════════════════════════



