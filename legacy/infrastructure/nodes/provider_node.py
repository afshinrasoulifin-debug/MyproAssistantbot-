
from __future__ import annotations
"""ProviderNode — Provider node for model routing."""
import logging
from typing import Any, Dict



logger = logging.getLogger(__name__)


class ProviderNode:
    """Represents an AI provider in the routing graph."""

    def __init__(self, name: str = "default", priority: int = 0) -> None:
        self.name = name
        self.priority = priority
        self._healthy = True
        self._last_check = 0.0
        self._success_count = 0
        self._error_count = 0

    def record_success(self) -> Any:
        self._success_count += 1
        self._healthy = True

    def record_error(self) -> Any:
        self._error_count += 1
        if self._error_count > 5:
            self._healthy = False

    @property
    def health_score(self) -> float:
        total = self._success_count + self._error_count
        return self._success_count / max(total, 1)

    def stats(self) -> Dict[str, Any]:
        return {"name": self.name, "healthy": self._healthy, "priority": self.priority,
                "successes": self._success_count, "errors": self._error_count,
                "health_score": self.health_score}


