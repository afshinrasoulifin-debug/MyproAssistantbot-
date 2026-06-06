
from __future__ import annotations
"""Base provider interface."""
import abc, logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum, auto



logger = logging.getLogger(__name__)

class ProviderStatus(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNAVAILABLE = auto()
    RATE_LIMITED = auto()

@dataclass
class ProviderMetrics:
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    total_tokens: int = 0
    total_latency: float = 0.0
    last_request: float = 0.0
    last_error: Optional[str] = None
    status: ProviderStatus = ProviderStatus.HEALTHY

    @property
    def avg_latency(self) -> float:
        return self.total_latency / max(self.successful, 1)

    @property
    def success_rate(self) -> float:
        return self.successful / max(self.total_requests, 1)

@dataclass
class ProviderRequest:
    messages: List[Dict[str, str]]
    model: str = ""
    max_tokens: int = 65536
    temperature: float = 0.7
    user_id: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""

@dataclass
class ProviderResponse:
    content: str = ""
    model: str = ""
    provider: str = ""
    tokens_used: int = 0
    latency: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

class BaseProvider(abc.ABC):
    """Abstract base for all AI providers."""
    def __init__(self, name: str, priority: int = 0) -> None:
        self.name = name
        self.priority = priority
        self.metrics = ProviderMetrics()
        self._enabled = True

    @abc.abstractmethod
    async def complete(self, request: ProviderRequest) -> ProviderResponse: ...

    async def health_check(self) -> ProviderStatus:
        return self.metrics.status

    def enable(self) -> Any: self._enabled = True
    def disable(self) -> Any: self._enabled = False

    @property
    def is_available(self) -> bool:
        return self._enabled and self.metrics.status in (
            ProviderStatus.HEALTHY, ProviderStatus.DEGRADED
        )


