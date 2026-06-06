
from __future__ import annotations
"""
tg_bot/orchestration/types.py — Shared types for orchestration layer.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional




class ProviderName(str, Enum):
    GEMINI = "gemini"
    GROQ = "groq"
    OPENROUTER = "openrouter"


class RequestPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass(slots=True)
class InferenceRequest:
    """A single AI inference request flowing through the orchestration layer."""
    prompt: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    model_key: str = ""
    model_id: str = ""
    provider: ProviderName = ProviderName.GEMINI
    user_id: int = 0
    temperature: float = 0.7
    max_tokens: int = 8192
    top_p: Optional[float] = None
    tools: Optional[list] = None
    priority: RequestPriority = RequestPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)
    request_id: str = ""


@dataclass(slots=True)
class InferenceResponse:
    """Response from an AI provider."""
    text: str
    provider: ProviderName
    model_id: str
    latency_ms: float = 0.0
    tokens_used: int = 0
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(slots=True)
class ProviderHealth:
    """Health snapshot of a provider."""
    name: ProviderName
    status: ProviderStatus = ProviderStatus.HEALTHY
    avg_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    success_rate: float = 1.0
    active_requests: int = 0
    total_requests: int = 0
    total_errors: int = 0
    last_error: Optional[str] = None
    last_success_at: float = 0.0
    last_error_at: float = 0.0
    circuit_open: bool = False


