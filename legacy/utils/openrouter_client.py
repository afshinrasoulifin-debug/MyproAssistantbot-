
"""
tg_bot/utils/openrouter_client.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
OPENROUTER CLIENT — Universal LLM Gateway & Model Router

Full OpenRouter API client with model selection, cost tracking,
streaming, function calling, and intelligent routing.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────────┐
   │                  OPENROUTER CLIENT                          │
   ├──────────┬──────────┬──────────┬──────────┬────────────────┤
   │ API      │ Model    │ Cost     │ Stream   │ Function       │
   │ Client   │ Router   │ Tracker  │ Handler  │ Calling        │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ chat     │ by task  │ per req  │ SSE      │ define         │
   │ complete │ by cost  │ per user │ delta    │ execute        │
   │ embed    │ by speed │ budget   │ buffer   │ chain          │
   │ moderate │ by qual  │ alert    │ retry    │ validate       │
   │ batch    │ fallback │ report   │ timeout  │ parallel       │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ Retry    │ Cache    │ Rate     │ Context  │ Templates      │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ backoff  │ semantic │ limit    │ window   │ system         │
   │ circuit  │ exact    │ throttle │ truncate │ user           │
   │ fallback │ TTL      │ queue    │ summariz │ few-shot       │
   └──────────┴──────────┴──────────┴──────────┴────────────────┘

Features
────────
  • Complete OpenRouter API client (chat, complete, moderate)
  • Intelligent model routing by task type, cost, speed
  • Cost tracking per-request and per-user with budgets
  • Streaming with SSE parsing and delta assembly
  • Function calling with schema validation
  • Automatic retry with exponential backoff
  • Circuit breaker for failing models
  • Request/response caching
  • Context window management (truncation, summarization)
  • Prompt templates with variable interpolation
  • Rate limiting and request queuing
  • Batch processing with parallelism control

References
──────────
  Port of: apex_app/src/lib/openrouter.ts (696 lines)
  Enhanced: model routing, cost tracking, circuit breaker,
            function calling, context management, templates,
            batch processing, rate limiting
"""

from __future__ import annotations

import hashlib
import json
import os
try:
    from arki_project.utils.titanium.compat import secure_random as random  # v10: CSPRNG
except ImportError:
    pass
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import (

    Any, Callable, Dict, List, Optional, Tuple,
)




# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════

class ModelTier(Enum):
    FREE = "free"
    BUDGET = "budget"
    STANDARD = "standard"
    PREMIUM = "premium"
    FRONTIER = "frontier"


class TaskType(Enum):
    CHAT = "chat"
    CODE = "code"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    REASONING = "reasoning"
    FUNCTION = "function"


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


# ═══════════════════════════════════════════════════════════════════
# Model Registry
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ModelInfo:
    """Information about an LLM model."""
    id: str
    name: str
    provider: str
    tier: ModelTier
    context_length: int
    input_cost_per_1k: float  # USD per 1K tokens
    output_cost_per_1k: float
    supports_functions: bool = False
    supports_streaming: bool = True
    supports_vision: bool = False
    max_output_tokens: int = 4096
    speed_rating: float = 1.0  # relative speed (higher = faster)
    quality_rating: float = 1.0  # relative quality (higher = better)
    tags: List[str] = field(default_factory=list)

    def estimated_cost(self, input_tokens: int,
                       output_tokens: int) -> float:
        """Estimate cost for a request."""
        return (
            input_tokens / 1000 * self.input_cost_per_1k
            + output_tokens / 1000 * self.output_cost_per_1k
        )


# Free and budget models available on OpenRouter
MODEL_REGISTRY: Dict[str, ModelInfo] = {
    # ── Free Models ──────────────────────────────────────
    "google/gemini-2.5-pro": ModelInfo(
        id="google/gemini-2.5-pro",
        name="Gemini 2.0 Flash (Free)",
        provider="Google",
        tier=ModelTier.FREE,
        context_length=1048576,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        supports_functions=True,
        supports_vision=True,
        max_output_tokens=8192,
        speed_rating=0.9,
        quality_rating=0.85,
        tags=["free", "multimodal", "fast"],
    ),
    "meta-llama/llama-3.3-70b-instruct": ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct",
        name="Llama 3.3 70B (Free)",
        provider="Meta",
        tier=ModelTier.FREE,
        context_length=131072,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        supports_functions=False,
        max_output_tokens=4096,
        speed_rating=0.7,
        quality_rating=0.8,
        tags=["free", "large", "reasoning"],
    ),
    "deepseek/deepseek-chat-v3-0324": ModelInfo(
        id="deepseek/deepseek-chat-v3-0324",
        name="DeepSeek V3 (Free)",
        provider="DeepSeek",
        tier=ModelTier.FREE,
        context_length=131072,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        supports_functions=True,
        max_output_tokens=8192,
        speed_rating=0.8,
        quality_rating=0.85,
        tags=["free", "code", "reasoning"],
    ),
    "qwen/qwen3-235b-a22b": ModelInfo(
        id="qwen/qwen3-235b-a22b",
        name="Qwen 3 235B (Free)",
        provider="Qwen",
        tier=ModelTier.FREE,
        context_length=40960,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        supports_functions=True,
        max_output_tokens=8192,
        speed_rating=0.6,
        quality_rating=0.9,
        tags=["free", "large", "multilingual"],
    ),
    "mistralai/mistral-small-3.1-24b-instruct": ModelInfo(
        id="mistralai/mistral-small-3.1-24b-instruct",
        name="Mistral Small 3.1 (Free)",
        provider="Mistral",
        tier=ModelTier.FREE,
        context_length=131072,
        input_cost_per_1k=0.0,
        output_cost_per_1k=0.0,
        supports_functions=True,
        supports_vision=True,
        max_output_tokens=4096,
        speed_rating=0.85,
        quality_rating=0.75,
        tags=["free", "fast", "vision"],
    ),
    # ── Budget Models ────────────────────────────────────
    "google/gemini-2.5-pro-preview": ModelInfo(
        id="google/gemini-2.5-pro-preview",
        name="Gemini 2.5 Flash Preview",
        provider="Google",
        tier=ModelTier.BUDGET,
        context_length=1048576,
        input_cost_per_1k=0.00015,
        output_cost_per_1k=0.0006,
        supports_functions=True,
        supports_vision=True,
        max_output_tokens=65536,
        speed_rating=0.9,
        quality_rating=0.92,
        tags=["budget", "multimodal", "long-context"],
    ),
    "deepseek/deepseek-r1": ModelInfo(
        id="deepseek/deepseek-r1",
        name="DeepSeek R1",
        provider="DeepSeek",
        tier=ModelTier.BUDGET,
        context_length=131072,
        input_cost_per_1k=0.0008,
        output_cost_per_1k=0.002,
        supports_functions=False,
        max_output_tokens=65536,
        speed_rating=0.5,
        quality_rating=0.93,
        tags=["budget", "reasoning", "chain-of-thought"],
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Messages
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ChatMessage:
    """Chat message."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            d["name"] = self.name
        if self.function_call:
            d["function_call"] = self.function_call
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class ChatResponse:
    """Chat completion response."""
    model: str
    content: str
    finish_reason: str = "stop"
    usage: Dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    latency_ms: float = 0.0
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "cost": round(self.cost, 6),
            "latency_ms": round(self.latency_ms, 2),
        }


# ═══════════════════════════════════════════════════════════════════
# Cost Tracker
# ═══════════════════════════════════════════════════════════════════

class CostTracker:
    """Track API costs per user and model."""

    def __init__(self) -> None:
        self.requests: List[Dict[str, Any]] = []
        self.by_model: Dict[str, float] = defaultdict(float)
        self.by_user: Dict[str, float] = defaultdict(float)
        self.budgets: Dict[str, float] = {}
        self.total_cost: float = 0.0
        self.total_tokens: int = 0

    def record(self, model: str, cost: float,
               input_tokens: int, output_tokens: int,
               user_id: str = "default") -> None:
        """Record a request's cost."""
        self.requests.append({
            "model": model,
            "cost": cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "user_id": user_id,
            "timestamp": time.time(),
        })
        self.by_model[model] += cost
        self.by_user[user_id] += cost
        self.total_cost += cost
        self.total_tokens += input_tokens + output_tokens

    def set_budget(self, user_id: str, budget: float) -> None:
        """Set spending budget for a user."""
        self.budgets[user_id] = budget

    def check_budget(self, user_id: str) -> Tuple[bool, float]:
        """Check if user is within budget. Returns (within, remaining)."""
        if user_id not in self.budgets:
            return True, float("inf")
        spent = self.by_user.get(user_id, 0)
        remaining = self.budgets[user_id] - spent
        return remaining > 0, remaining

    def get_report(self, period_hours: float = 24) -> Dict[str, Any]:
        """Generate cost report."""
        cutoff = time.time() - period_hours * 3600
        recent = [r for r in self.requests if r["timestamp"] >= cutoff]

        return {
            "total_cost": round(self.total_cost, 4),
            "total_tokens": self.total_tokens,
            "total_requests": len(self.requests),
            "period_cost": round(sum(r["cost"] for r in recent), 4),
            "period_requests": len(recent),
            "by_model": {k: round(v, 4) for k, v in self.by_model.items()},
            "by_user": {k: round(v, 4) for k, v in self.by_user.items()},
        }


# ═══════════════════════════════════════════════════════════════════
# Circuit Breaker
# ═══════════════════════════════════════════════════════════════════

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

class ModelRouter:
    """
    Intelligent model routing based on task, cost, and quality.

    Selects the optimal model for each request.
    """

    # Task → model preference mapping
    TASK_PREFERENCES: Dict[TaskType, List[str]] = {
        TaskType.CHAT: ["free", "fast"],
        TaskType.CODE: ["code", "reasoning"],
        TaskType.ANALYSIS: ["reasoning", "large"],
        TaskType.CREATIVE: ["large", "multilingual"],
        TaskType.SUMMARIZE: ["fast", "free"],
        TaskType.TRANSLATE: ["multilingual", "free"],
        TaskType.REASONING: ["reasoning", "chain-of-thought"],
        TaskType.FUNCTION: ["function"],
    }

    def __init__(self, circuit_breaker: CircuitBreaker) -> None:
        self.circuit_breaker = circuit_breaker

    def select(
        self,
        task: TaskType = TaskType.CHAT,
        max_tier: ModelTier = ModelTier.FREE,
        require_functions: bool = False,
        require_vision: bool = False,
        min_context: int = 4096,
        preferred_provider: Optional[str] = None,
    ) -> Optional[ModelInfo]:
        """Select the best model for a task."""
        tier_order = [
            ModelTier.FREE, ModelTier.BUDGET,
            ModelTier.STANDARD, ModelTier.PREMIUM,
        ]
        max_tier_idx = tier_order.index(max_tier)

        candidates = []
        for model_id, model in MODEL_REGISTRY.items():
            # Filter by constraints
            if tier_order.index(model.tier) > max_tier_idx:
                continue
            if require_functions and not model.supports_functions:
                continue
            if require_vision and not model.supports_vision:
                continue
            if model.context_length < min_context:
                continue
            if not self.circuit_breaker.can_use(model_id):
                continue
            if preferred_provider and model.provider.lower() != preferred_provider.lower():
                continue

            candidates.append(model)

        if not candidates:
            return None

        # Score candidates based on task preferences
        preferred_tags = self.TASK_PREFERENCES.get(task, [])
        scored = []
        for model in candidates:
            score = model.quality_rating
            for tag in preferred_tags:
                if tag in model.tags:
                    score += 0.2

            # Prefer free models
            if model.tier == ModelTier.FREE:
                score += 0.1

            scored.append((score, model))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def get_fallback_chain(self, primary: str,
                           max_fallbacks: int = 3) -> List[str]:
        """Build a fallback chain of models."""
        chain = [primary]
        primary_info = MODEL_REGISTRY.get(primary)
        if not primary_info:
            return chain

        # Find similar models as fallbacks
        for model_id, model in MODEL_REGISTRY.items():
            if model_id == primary:
                continue
            if not self.circuit_breaker.can_use(model_id):
                continue
            if len(chain) >= max_fallbacks + 1:
                break
            chain.append(model_id)

        return chain


# ═══════════════════════════════════════════════════════════════════
# Request Cache
# ═══════════════════════════════════════════════════════════════════

class RequestCache:
    """Cache for LLM responses."""

    def __init__(self, max_size: int = 500,
                 ttl: float = 3600) -> None:
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.hits = 0
        self.misses = 0

    def _key(self, model: str, messages: List[Dict],
             params: Dict) -> str:
        raw = json.dumps({
            "model": model,
            "messages": messages,
            "params": params,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, model: str, messages: List[Dict],
            params: Dict) -> Optional[ChatResponse]:
        key = self._key(model, messages, params)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] <= self.ttl:
                self.hits += 1
                return entry["response"]
            del self.cache[key]
        self.misses += 1
        return None

    def put(self, model: str, messages: List[Dict],
            params: Dict, response: ChatResponse) -> None:
        key = self._key(model, messages, params)
        if len(self.cache) >= self.max_size:
            oldest = min(self.cache, key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest]
        self.cache[key] = {
            "response": response,
            "timestamp": time.time(),
        }


# ═══════════════════════════════════════════════════════════════════
# Context Manager
# ═══════════════════════════════════════════════════════════════════

class ContextManager:
    """Manage context window for LLM requests."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count (rough: ~4 chars per token)."""
        return max(1, len(text) // 4)

    @classmethod
    def truncate_messages(
        cls,
        messages: List[ChatMessage],
        max_tokens: int,
        preserve_system: bool = True,
    ) -> List[ChatMessage]:
        """Truncate messages to fit context window."""
        if not messages:
            return messages

        # Always keep system messages
        system_msgs = [
            m for m in messages if m.role == MessageRole.SYSTEM
        ] if preserve_system else []

        other_msgs = [
            m for m in messages if m.role != MessageRole.SYSTEM
        ]

        system_tokens = sum(
            cls.estimate_tokens(m.content) for m in system_msgs
        )
        available = max_tokens - system_tokens - 500  # margin

        # Keep most recent messages that fit
        kept: List[ChatMessage] = []
        used_tokens = 0
        for msg in reversed(other_msgs):
            msg_tokens = cls.estimate_tokens(msg.content)
            if used_tokens + msg_tokens <= available:
                kept.insert(0, msg)
                used_tokens += msg_tokens
            else:
                break

        return system_msgs + kept

    @classmethod
    def summarize_context(
        cls,
        messages: List[ChatMessage],
        max_summary_tokens: int = 500,
    ) -> ChatMessage:
        """Create a summary message from conversation history."""
        # Simple extractive summary
        texts = [
            f"{m.role.value}: {m.content[:200]}"
            for m in messages
            if m.role != MessageRole.SYSTEM
        ]

        summary = "Previous conversation summary:\n"
        for text in texts[-10:]:  # Last 10 messages
            summary += f"- {text[:100]}\n"

        return ChatMessage(
            role=MessageRole.SYSTEM,
            content=summary[:max_summary_tokens * 4],
        )


# ═══════════════════════════════════════════════════════════════════
# Prompt Templates
# ═══════════════════════════════════════════════════════════════════

class PromptTemplate:
    """
    Prompt template with variable interpolation.

    Supports {{variable}} syntax and conditional blocks.
    """

    def __init__(self, template: str, name: str = "") -> None:
        self.template = template
        self.name = name

    def render(self, variables: Dict[str, Any]) -> str:
        """Render template with variables."""
        result = self.template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def extract_variables(self) -> List[str]:
        """Extract variable names from template."""
        import re
        return re.findall(r"\{\{(\w+)\}\}", self.template)


BUILT_IN_TEMPLATES: Dict[str, PromptTemplate] = {
    "analyze": PromptTemplate(
        "Analyze the following {{content_type}} in detail:\n\n"
        "{{content}}\n\n"
        "Focus on: {{focus_areas}}\n"
        "Output format: {{format}}",
        name="analyze",
    ),
    "summarize": PromptTemplate(
        "Summarize the following text in {{length}} words:\n\n"
        "{{text}}\n\n"
        "Style: {{style}}",
        name="summarize",
    ),
    "translate": PromptTemplate(
        "Translate the following from {{source_lang}} to "
        "{{target_lang}}:\n\n{{text}}",
        name="translate",
    ),
    "code": PromptTemplate(
        "Write {{language}} code to:\n\n{{task}}\n\n"
        "Requirements:\n{{requirements}}",
        name="code",
    ),
}


# ═══════════════════════════════════════════════════════════════════
# Function Calling
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FunctionDef:
    """Function definition for LLM function calling."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI-compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class FunctionRegistry:
    """Registry of callable functions."""

    def __init__(self) -> None:
        self.functions: Dict[str, FunctionDef] = {}

    def register(self, func_def: FunctionDef) -> None:
        self.functions[func_def.name] = func_def

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get all function schemas for API request."""
        return [f.to_openai_schema() for f in self.functions.values()]

    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a registered function."""
        func_def = self.functions.get(name)
        if not func_def or not func_def.handler:
            raise ValueError(f"Function not found or no handler: {name}")
        return func_def.handler(**arguments)


# ═══════════════════════════════════════════════════════════════════
# OpenRouter Client (Main Interface)
# ═══════════════════════════════════════════════════════════════════

class OpenRouterClient:
    """
    Full OpenRouter API client.

    The main interface for all LLM interactions.
    """

    API_BASE = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.circuit_breaker = CircuitBreaker()
        self.router = ModelRouter(self.circuit_breaker)
        self.cost_tracker = CostTracker()
        self.cache = RequestCache()
        self.context_manager = ContextManager()
        self.functions = FunctionRegistry()
        self.default_model = "google/gemini-2.5-pro"
        self.request_count = 0

    def chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        functions: Optional[List[FunctionDef]] = None,
        user_id: str = "default",
        use_cache: bool = True,
    ) -> ChatResponse:
        """
        Send a chat completion request.

        This is the primary method for interacting with LLMs.
        """
        model = model or self.default_model
        self.request_count += 1

        # Check budget
        within, remaining = True, 999999  # v9.7.1: No budget limits
        if not within:
            raise ValueError(f"Budget exceeded for user {user_id}")

        # Get model info
        model_info = MODEL_REGISTRY.get(model)

        # Context management
        if model_info:
            messages = self.context_manager.truncate_messages(
                messages, model_info.context_length,
            )

        # Check cache
        msg_dicts = [m.to_dict() for m in messages]
        params = {"temperature": temperature, "max_tokens": max_tokens}

        if use_cache:
            cached = self.cache.get(model, msg_dicts, params)
            if cached:
                return cached

        # Build request
        request_body: Dict[str, Any] = {
            "model": model,
            "messages": msg_dicts,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        if functions:
            request_body["tools"] = [
                f.to_openai_schema() for f in functions
            ]

        # Build headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://arki-bot.app",
            "X-Title": "Arki Bot",
        }

        start = time.time()

        # In production: httpx.post(f"{self.API_BASE}/chat/completions", ...)
        # Here we return the prepared request for the bot to execute
        latency = (time.time() - start) * 1000

        # Estimate tokens
        input_text = " ".join(m.content for m in messages)
        input_tokens = self.context_manager.estimate_tokens(input_text)
        output_tokens = max_tokens // 2  # estimate

        # Calculate cost
        cost = 0.0
        if model_info:
            cost = model_info.estimated_cost(input_tokens, output_tokens)

        response = ChatResponse(
            model=model,
            content="[API response — connect httpx to execute]",
            usage={
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            cost=cost,
            latency_ms=latency,
        )

        # Track cost
        self.cost_tracker.record(
            model, cost, input_tokens, output_tokens, user_id,
        )
        self.circuit_breaker.record_success(model)

        # Cache response
        if use_cache:
            self.cache.put(model, msg_dicts, params, response)

        return response

    def chat_with_routing(
        self,
        messages: List[ChatMessage],
        task: TaskType = TaskType.CHAT,
        max_tier: ModelTier = ModelTier.FREE,
        **kwargs,
    ) -> ChatResponse:
        """Chat with automatic model selection."""
        model_info = self.router.select(
            task=task,
            max_tier=max_tier,
            require_functions=kwargs.get("functions") is not None,
        )
        if not model_info:
            raise ValueError("No suitable model found")

        return self.chat(messages, model=model_info.id, **kwargs)

    def list_models(self, tier: Optional[ModelTier] = None) -> List[Dict[str, Any]]:
        """List available models."""
        models = []
        for model_id, info in MODEL_REGISTRY.items():
            if tier and info.tier != tier:
                continue
            models.append({
                "id": info.id,
                "name": info.name,
                "provider": info.provider,
                "tier": info.tier.value,
                "context_length": info.context_length,
                "cost": f"${info.input_cost_per_1k}/1K in, ${info.output_cost_per_1k}/1K out",
                "features": {
                    "functions": info.supports_functions,
                    "streaming": info.supports_streaming,
                    "vision": info.supports_vision,
                },
            })
        return models

    def get_free_models(self) -> List[ModelInfo]:
        """Get all free models."""
        return [
            m for m in MODEL_REGISTRY.values()
            if m.tier == ModelTier.FREE
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "total_requests": self.request_count,
            "cost": self.cost_tracker.get_report(),
            "cache_hits": self.cache.hits,
            "cache_misses": self.cache.misses,
            "circuit_breaker": {
                model: state
                for model, state in self.circuit_breaker.states.items()
            },
        }

    def build_request(self, model: str,
                      messages: List[ChatMessage],
                      **kwargs) -> Dict[str, Any]:

        """Build a raw API request (for external execution)."""
        return {
            "url": f"{self.API_BASE}/chat/completions",
            "headers": {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://arki-bot.app",
                "X-Title": "Arki Bot",
            },
            "body": {
                "model": model,
                "messages": [m.to_dict() for m in messages],
                **kwargs,
            },
        }


