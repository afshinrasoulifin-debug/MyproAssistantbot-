
from __future__ import annotations
"""
tg_bot/utils/response_types.py — Structured Response Types v9.4
Pydantic-style dataclasses for handler input/output validation.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

# ── TITANIUM v29.0 Integration ──



@dataclass
class AIRequest:
    """Validated AI request."""
    user_id: int
    text: str
    model: str = "gemini-2.5-pro"
    temperature: float = 0.7
    max_tokens: int = 8192
    system_prompt: str = ""
    history: List[Dict] = field(default_factory=list)

    def validate(self) -> List[str]:
        errors = []
        if not self.text.strip():
            errors.append("Text cannot be empty")
        if self.temperature < 0 or self.temperature > 2:
            errors.append("Temperature must be 0-2")
        if self.max_tokens < 1:
            errors.append("max_tokens must be positive")
        return errors


@dataclass
class AIResponse:
    """Structured AI response."""
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    fallback_used: bool = False
    hallucination_risk: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class SearchResult:
    """Web search result."""
    title: str
    url: str
    snippet: str
    source: str = ""
    relevance: float = 0.0


@dataclass
class ContentPiece:
    """Generated content piece."""
    title: str
    body: str
    content_type: str = "post"
    platform: str = "general"
    hashtags: List[str] = field(default_factory=list)
    media_url: str = ""
    word_count: int = 0

    def __post_init__(self) -> Any:
        self.word_count = len(self.body.split())


@dataclass
class SalesLead:
    """Sales lead data."""
    user_id: int
    name: str = ""
    score: float = 0.0
    stage: str = "awareness"
    source: str = ""
    notes: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class MonitorAlert:
    """Monitoring alert."""
    source: str
    message: str
    severity: str = "info"  # info, warning, critical
    metric_name: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0


@dataclass
class UserProfile:
    """User profile for AI personalization."""
    user_id: int
    language: str = "fa"
    timezone: str = "Asia/Tehran"
    plan: str = "free"
    preferences: Dict[str, Any] = field(default_factory=dict)
    interests: List[str] = field(default_factory=list)
    interaction_count: int = 0


@dataclass
class BatchJob:
    """Batch processing job."""
    job_id: str
    user_id: int
    items: List[str] = field(default_factory=list)
    status: str = "pending"
    progress: float = 0.0
    results: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


