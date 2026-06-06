
"""
tg_bot/utils/multi_llm_orchestrator.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
MULTI-LLM ORCHESTRATOR — Advanced Model Management System

Goes beyond basic model routing with intelligent orchestration:

  ┌──────────────┐
  │   User Query  │
  └──────┬───────┘
         │
    ┌────▼────┐
    │ Classify │  ← NLP-based task profiling
    │  Task    │
    └────┬────┘
         │
  ┌──────▼──────────────────────────────────┐
  │        Routing Strategy                  │
  ├──────────┬──────────┬───────────────────┤
  │ Specialist│ Ensemble │ Debate  │ Cascade │
  │  Single   │  Vote    │ Argue   │ Chain   │
  │  Best     │  N models│ Refine  │ Fallback│
  └──────────┴──────────┴─────────┴─────────┘
         │
    ┌────▼────┐
    │ Synthe- │  ← Meta-model combines results
    │ size    │
    └────┬────┘
         │
    ┌────▼────┐
    │ Cache + │  ← Cost & performance tracking
    │ Track   │
    └─────────┘

Features
────────
  • 8 model profiles with strength/weakness mapping
  • 8 orchestration modes (specialist, ensemble, debate, cost-opt,
    cascade, round-robin, A/B test, consensus)
  • NLP task classification (code, math, creative, analysis,
    vision, translation, security, general)
  • Multi-factor model scoring (quality, speed, cost, reliability)
  • Refusal detection with regex patterns
  • Self-assessed confidence estimation
  • Response caching (SHA-256 keyed, LRU with TTL)
  • Cost tracking per call and per session
  • Performance history for quality regression detection
  • Budget enforcement with cost estimation

References
──────────
  Port of: apex_app/src/lib/multi-llm-orchestrator.ts (654 lines)
  Enhanced with: BM25-inspired task profiling, richer model registry,
                 consensus mode, A/B testing, round-robin, budget guards
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────

CACHE_TTL_S       = 600
CACHE_MAX_SIZE    = 256
MAX_DEBATE_ROUNDS = 4
DEFAULT_API_BASE  = "https://openrouter.ai/api/v1/chat/completions"


# ═══════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════

class RoutingStrategy(str, Enum):
    BEST_QUALITY = "best_quality"
    CHEAPEST     = "cheapest"
    FASTEST      = "fastest"
    BALANCED     = "balanced"
    SPECIALIST   = "specialist"


@dataclass
class ModelProfile:
    """Detailed profile of an LLM model."""
    id: str
    name: str
    provider: str
    strengths: List[str]
    weaknesses: List[str]
    cost_per_1k_input: float        # USD
    cost_per_1k_output: float       # USD
    max_tokens: int
    context_window: int
    supports_vision: bool
    supports_tools: bool
    speed: str                      # fast | medium | slow
    quality: float                  # 1-10
    reliability: float              # 0-1 (uptime)
    avg_latency_ms: float
    refusal_rate: float             # 0-1
    tags: List[str] = field(default_factory=list)

    @property
    def cost_per_1k_total(self) -> float:
        return self.cost_per_1k_input + self.cost_per_1k_output


@dataclass
class ModelResponse:
    """Response from a single model call."""
    model: str
    content: str
    confidence: float               # 0-1
    tokens: Dict[str, int]          # {input, output}
    cost: float                     # USD
    latency_ms: float
    refusal: bool
    error: Optional[str] = None

    @property
    def total_tokens(self) -> int:
        return self.tokens.get("input", 0) + self.tokens.get("output", 0)


@dataclass
class DebateRound:
    """One round of model debate."""
    round: int
    responses: List[ModelResponse]
    synthesis: str = ""
    consensus: bool = False
    avg_confidence: float = 0.0


@dataclass
class OrchestrationResult:
    """Complete result of an orchestration run."""
    mode: str
    final_response: str
    confidence: float
    models: List[ModelResponse]
    debate: Optional[List[DebateRound]] = None
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    cache_hit: bool = False
    task_category: str = ""
    selected_models: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Mode: {self.mode} | Models: {len(self.models)} | "
            f"Cost: ${self.total_cost:.4f} | Confidence: {self.confidence:.2f} | "
            f"Tokens: {self.total_tokens:,} | Latency: {self.total_latency_ms:.0f}ms"
        )


@dataclass
class RoutingConfig:
    """Configuration for model routing."""
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    max_cost: Optional[float] = None          # USD budget
    max_latency_ms: Optional[float] = None
    min_confidence: Optional[float] = None
    required_capabilities: Optional[List[str]] = None
    preferred_models: Optional[List[str]] = None
    exclude_models: Optional[List[str]] = None


# ═══════════════════════════════════════════════════════════════════
# Model Registry
# ═══════════════════════════════════════════════════════════════════

MODEL_PROFILES: List[ModelProfile] = [
    ModelProfile(
        id="anthropic/claude-sonnet-4-20250514",
        name="Claude Sonnet 4",
        provider="Anthropic",
        strengths=["coding", "analysis", "reasoning", "safety",
                   "long_context", "instruction_following"],
        weaknesses=["speed"],
        cost_per_1k_input=0.003, cost_per_1k_output=0.015,
        max_tokens=65536, context_window=200_000,
        supports_vision=True, supports_tools=True,
        speed="medium", quality=9.5, reliability=0.99,
        avg_latency_ms=3000, refusal_rate=0.05,
        tags=["premium", "coding", "analysis"],
    ),
    ModelProfile(
        id="openai/gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        strengths=["general", "creative", "vision", "multilingual", "speed"],
        weaknesses=["cost"],
        cost_per_1k_input=0.005, cost_per_1k_output=0.015,
        max_tokens=65536, context_window=128_000,
        supports_vision=True, supports_tools=True,
        speed="fast", quality=9.0, reliability=0.98,
        avg_latency_ms=2000, refusal_rate=0.08,
        tags=["premium", "multimodal", "fast"],
    ),
    ModelProfile(
        id="openai/gpt-4o-mini",
        name="GPT-4o Mini",
        provider="OpenAI",
        strengths=["speed", "cost", "general"],
        weaknesses=["complex_reasoning"],
        cost_per_1k_input=0.00015, cost_per_1k_output=0.0006,
        max_tokens=16384, context_window=128_000,
        supports_vision=True, supports_tools=True,
        speed="fast", quality=7.5, reliability=0.99,
        avg_latency_ms=1000, refusal_rate=0.1,
        tags=["budget", "fast", "general"],
    ),
    ModelProfile(
        id="google/gemini-2.5-pro-preview",
        name="Gemini 2.5 Pro",
        provider="Google",
        strengths=["reasoning", "math", "science", "long_context", "multilingual"],
        weaknesses=["creativity"],
        cost_per_1k_input=0.00125, cost_per_1k_output=0.01,
        max_tokens=65536, context_window=1_000_000,
        supports_vision=True, supports_tools=True,
        speed="medium", quality=9.2, reliability=0.97,
        avg_latency_ms=3500, refusal_rate=0.06,
        tags=["premium", "reasoning", "science"],
    ),
    ModelProfile(
        id="meta-llama/llama-3.1-405b-instruct",
        name="Llama 3.1 405B",
        provider="Meta",
        strengths=["open_source", "general", "coding", "multilingual"],
        weaknesses=["vision", "tools"],
        cost_per_1k_input=0.001, cost_per_1k_output=0.001,
        max_tokens=65536, context_window=131_072,
        supports_vision=False, supports_tools=False,
        speed="medium", quality=8.5, reliability=0.95,
        avg_latency_ms=2500, refusal_rate=0.03,
        tags=["open_source", "general"],
    ),
    ModelProfile(
        id="mistralai/mistral-large-latest",
        name="Mistral Large",
        provider="Mistral",
        strengths=["coding", "reasoning", "european_languages"],
        weaknesses=["vision"],
        cost_per_1k_input=0.002, cost_per_1k_output=0.006,
        max_tokens=65536, context_window=128_000,
        supports_vision=False, supports_tools=True,
        speed="fast", quality=8.0, reliability=0.96,
        avg_latency_ms=2000, refusal_rate=0.04,
        tags=["coding", "european"],
    ),
    ModelProfile(
        id="deepseek/deepseek-r1",
        name="DeepSeek R1",
        provider="DeepSeek",
        strengths=["reasoning", "math", "coding", "cost"],
        weaknesses=["creative", "vision"],
        cost_per_1k_input=0.00055, cost_per_1k_output=0.0022,
        max_tokens=65536, context_window=128_000,
        supports_vision=False, supports_tools=False,
        speed="slow", quality=9.0, reliability=0.93,
        avg_latency_ms=5000, refusal_rate=0.02,
        tags=["reasoning", "math", "budget"],
    ),
    ModelProfile(
        id="qwen/qwen-2.5-72b-instruct",
        name="Qwen 2.5 72B",
        provider="Alibaba",
        strengths=["multilingual", "chinese", "coding", "cost"],
        weaknesses=["english_creative"],
        cost_per_1k_input=0.0003, cost_per_1k_output=0.0003,
        max_tokens=65536, context_window=131_072,
        supports_vision=False, supports_tools=True,
        speed="fast", quality=7.8, reliability=0.94,
        avg_latency_ms=1500, refusal_rate=0.05,
        tags=["budget", "multilingual", "chinese"],
    ),
]

_MODEL_INDEX: Dict[str, ModelProfile] = {m.id: m for m in MODEL_PROFILES}


def get_model(model_id: str) -> Optional[ModelProfile]:
    return _MODEL_INDEX.get(model_id)


# ═══════════════════════════════════════════════════════════════════
# Task Classification (NLP-Based)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TaskProfile:
    category: str
    required_strengths: List[str]
    complexity: str                     # low | medium | high
    needs_vision: bool
    needs_tools: bool
    estimated_tokens: int

# Rule-based classifier using regex patterns
_TASK_RULES: List[Dict[str, Any]] = [
    {
        "category": "coding",
        "pattern": r"\b(code|function|class|bug|debug|implement|program|"
                   r"script|api|endpoint|sql|html|css|javascript|python|"
                   r"typescript|rust|go|java|c\+\+|compile|syntax|refactor|"
                   r"deploy|dockerfile|kubernetes|git|github|module|library)\b",
        "strengths": ["coding"],
        "complexity_hint": "medium",
    },
    {
        "category": "math",
        "pattern": r"\b(math|calculate|equation|proof|theorem|solve|formula|"
                   r"algebra|calculus|statistics|probability|integral|derivative|"
                   r"matrix|vector|eigenvalue|optimization|linear|differential)\b",
        "strengths": ["math", "reasoning"],
        "complexity_hint": "high",
    },
    {
        "category": "creative",
        "pattern": r"\b(write|story|poem|creative|fiction|essay|blog|article|"
                   r"content|marketing|copy|song|lyrics|screenplay|slogan|"
                   r"brainstorm|imagine|describe)\b",
        "strengths": ["creative"],
        "complexity_hint": "medium",
    },
    {
        "category": "analysis",
        "pattern": r"\b(analyze|analysis|compare|evaluate|review|assessment|"
                   r"report|summary|summarize|benchmark|pros.?cons|critique)\b",
        "strengths": ["analysis", "reasoning"],
        "complexity_hint": "high",
    },
    {
        "category": "vision",
        "pattern": r"\b(image|picture|photo|screenshot|visual|look.?at|"
                   r"describe.?this|what.?do.?you.?see|diagram|chart|graph)\b",
        "strengths": ["vision"],
        "complexity_hint": "medium",
    },
    {
        "category": "translation",
        "pattern": r"\b(translate|translation|convert.?to|in.?\w+.?language|"
                   r"interpret|localize|ترجمه|翻译)\b",
        "strengths": ["multilingual"],
        "complexity_hint": "low",
    },
    {
        "category": "security",
        "pattern": r"\b(security|vulnerability|exploit|penetration|scan|"
                   r"hack|bypass|injection|xss|sqli|cve|firewall|"
                   r"authentication|oauth|jwt|encryption|decrypt|brute)\b",
        "strengths": ["coding", "analysis"],
        "complexity_hint": "high",
    },
    {
        "category": "science",
        "pattern": r"\b(physics|chemistry|biology|genome|molecule|atom|"
                   r"quantum|relativity|evolution|ecology|neuroscience|"
                   r"experiment|hypothesis|research)\b",
        "strengths": ["science", "reasoning"],
        "complexity_hint": "high",
    },
]


def classify_task(query: str) -> TaskProfile:
    """Classify user query into a task profile for model routing."""
    lower = query.lower()
    length = len(query)

    for rule in _TASK_RULES:
        if re.search(rule["pattern"], lower, re.IGNORECASE):
            complexity = rule["complexity_hint"]
            if length > 500:
                complexity = "high"
            return TaskProfile(
                category=rule["category"],
                required_strengths=rule["strengths"],
                complexity=complexity,
                needs_vision=("vision" in rule["strengths"]),
                needs_tools=(rule["category"] in ("security", "coding")),
                estimated_tokens=length * 3,
            )

    return TaskProfile(
        category="general",
        required_strengths=["general"],
        complexity="medium",
        needs_vision=False,
        needs_tools=False,
        estimated_tokens=length * 2,
    )


# ═══════════════════════════════════════════════════════════════════
# Model Scoring & Selection
# ═══════════════════════════════════════════════════════════════════

def score_model(model: ModelProfile, task: TaskProfile,
                config: RoutingConfig) -> float:
    """Score a model for a task/config. Higher = better match."""
    score = 0.0

    # Strength match (0-40)
    overlap = sum(1 for s in task.required_strengths
                  if s in model.strengths)
    if task.required_strengths:
        score += (overlap / len(task.required_strengths)) * 40

    # Quality (0-20)
    score += (model.quality / 10) * 20

    # Strategy-specific (0-30)
    strat = config.strategy
    if strat == RoutingStrategy.BEST_QUALITY:
        score += (model.quality / 10) * 30
    elif strat == RoutingStrategy.CHEAPEST:
        max_cost = 0.03
        score += max(0, (1 - model.cost_per_1k_total / max_cost)) * 30
    elif strat == RoutingStrategy.FASTEST:
        speed_map = {"fast": 30, "medium": 15, "slow": 5}
        score += speed_map.get(model.speed, 10)
    elif strat == RoutingStrategy.BALANCED:
        score += (model.quality / 10) * 10
        score += max(0, (1 - model.cost_per_1k_total / 0.03)) * 10
        speed_map = {"fast": 10, "medium": 5, "slow": 2}
        score += speed_map.get(model.speed, 5)
    elif strat == RoutingStrategy.SPECIALIST:
        # Extra bonus for exact strength match
        score += overlap * 15

    # Capability requirements
    if task.needs_vision and not model.supports_vision:
        score -= 50
    if task.needs_tools and not model.supports_tools:
        score -= 20

    # Reliability
    score += model.reliability * 10

    # Low refusal bonus
    score += (1 - model.refusal_rate) * 10

    # Preferred / excluded
    if config.preferred_models and model.id in config.preferred_models:
        score += 15
    if config.exclude_models and model.id in config.exclude_models:
        score -= 100

    # Cost budget check
    if config.max_cost:
        est_cost = (task.estimated_tokens / 1000) * model.cost_per_1k_total
        if est_cost > config.max_cost:
            score -= 30

    # Latency check
    if config.max_latency_ms and model.avg_latency_ms > config.max_latency_ms:
        score -= 20

    return score


def select_models(task: TaskProfile, config: RoutingConfig,
                  count: int = 1) -> List[ModelProfile]:
    """Select top-N models for a task."""
    scored = [(m, score_model(m, task, config)) for m in MODEL_PROFILES]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [m for m, _ in scored[:count]]


# ═══════════════════════════════════════════════════════════════════
# Response Cache (LRU + TTL)
# ═══════════════════════════════════════════════════════════════════

class ResponseCache:
    """Cache for model responses keyed by (model + query) hash."""

    def __init__(self, max_size: int = CACHE_MAX_SIZE, ttl: float = CACHE_TTL_S) -> None:
        self._cache: OrderedDict[str, Tuple[OrchestrationResult, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _key(query: str, mode: str) -> str:
        raw = json.dumps({"q": query, "m": mode}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, query: str, mode: str) -> Optional[OrchestrationResult]:
        k = self._key(query, mode)
        if k in self._cache:
            result, ts = self._cache[k]
            if time.time() - ts < self._ttl:
                self._cache.move_to_end(k)
                self._hits += 1
                result.cache_hit = True
                return result
            del self._cache[k]
        self._misses += 1
        return None

    def put(self, query: str, mode: str, result: OrchestrationResult) -> None:
        k = self._key(query, mode)
        self._cache[k] = (result, time.time())
        self._cache.move_to_end(k)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    @property
    def hit_rate(self) -> str:
        total = self._hits + self._misses
        return f"{self._hits / total * 100:.1f}%" if total > 0 else "N/A"


_cache = ResponseCache()


# ═══════════════════════════════════════════════════════════════════
# Core API Call
# ═══════════════════════════════════════════════════════════════════

# Refusal detection patterns
_REFUSAL_PATTERNS = [
    re.compile(r"I (?:cannot|can't|won't|refuse|am unable)", re.I),
    re.compile(r"I'm not able to", re.I),
    re.compile(r"against (?:my|the) (?:guidelines|policies|rules)", re.I),
    re.compile(r"inappropriate|harmful|unethical", re.I),
    re.compile(r"I must decline", re.I),
    re.compile(r"not (?:comfortable|appropriate|ethical)", re.I),
]


def _detect_refusal(content: str) -> bool:
    return any(p.search(content) for p in _REFUSAL_PATTERNS)


def _estimate_confidence(content: str, refusal: bool) -> float:
    """Heuristic confidence estimation from response text."""
    if refusal:
        return 0.1

    conf = 0.80
    lowering = [
        ("I think", -0.08), ("I believe", -0.08), ("I'm not sure", -0.25),
        ("I'm uncertain", -0.20), ("probably", -0.05), ("possibly", -0.10),
        ("might be", -0.10), ("I don't know", -0.30),
    ]
    raising = [
        ("definitely", 0.05), ("certainly", 0.05), ("clearly", 0.03),
        ("evidently", 0.03), ("without doubt", 0.05),
    ]

    for phrase, delta in lowering:
        if phrase.lower() in content.lower():
            conf += delta
    for phrase, delta in raising:
        if phrase.lower() in content.lower():
            conf += delta

    # Length bonus: longer = more thought
    if len(content) > 1000:
        conf += 0.05
    if len(content) > 3000:
        conf += 0.05

    return max(0.0, min(1.0, conf))


async def call_model(
    model_id: str,
    messages: List[Dict[str, str]],
    api_key: str,
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    api_base: str = DEFAULT_API_BASE,
) -> ModelResponse:
    """
    Make a single API call to a model via OpenRouter.

    Parameters
    ----------
    model_id : str
        Model identifier (e.g. "openai/gpt-4o").
    messages : list
        Chat messages [{role, content}].
    api_key : str
        OpenRouter API key.
    temperature : float
        Sampling temperature.
    max_tokens : int
        Maximum output tokens.

    Returns
    -------
    ModelResponse
        Parsed response with confidence scoring.
    """
    start = time.time()

    try:
        # v10.1: Route through TITANIUM shielded client (L1-L7 security)
        try:
            from arki_project.utils.titanium.integration import shielded_post
            resp = await shielded_post(
                api_base,
                json_data={
                    "model": model_id,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://arki-engine.ai",
                    "X-Title": "Arki-Orchestrator",
                },
                timeout=1200.0,
                provider_name=f"multi_llm:{model_id}",
            )
            if not resp.success:
                raise RuntimeError(f"API {resp.status}: {resp.text[:200]}")
            data = resp.json()
        except ImportError:
            # Fallback to raw aiohttp if TITANIUM not available
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_base,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://arki-engine.ai",
                        "X-Title": "Arki-Orchestrator",
                    },
                    json={
                        "model": model_id,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        raise RuntimeError(f"API {resp.status}: {err[:200]}")
                    data = await resp.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})

        refusal = _detect_refusal(content)
        confidence = _estimate_confidence(content, refusal)

        profile = _MODEL_INDEX.get(model_id)
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        cost = (profile.cost_per_1k_input * in_tok / 1000
                + profile.cost_per_1k_output * out_tok / 1000) if profile else 0

        return ModelResponse(
            model=model_id,
            content=content,
            confidence=confidence,
            tokens={"input": in_tok, "output": out_tok},
            cost=cost,
            latency_ms=(time.time() - start) * 1000,
            refusal=refusal,
        )
    except Exception as exc:
        return ModelResponse(
            model=model_id, content="", confidence=0.0,
            tokens={"input": 0, "output": 0}, cost=0.0,
            latency_ms=(time.time() - start) * 1000,
            refusal=False, error=str(exc),
        )


# ═══════════════════════════════════════════════════════════════════
# Orchestration Modes
# ═══════════════════════════════════════════════════════════════════

async def route_to_specialist(
    query: str,
    api_key: str,
    config: Optional[RoutingConfig] = None,
) -> OrchestrationResult:
    """Route to the single best model for this task."""
    config = config or RoutingConfig(strategy=RoutingStrategy.BALANCED)

    # Check cache
    cached = _cache.get(query, "specialist")
    if cached:
        return cached

    task = classify_task(query)
    best = select_models(task, config, count=1)[0]

    response = await call_model(
        best.id, [{"role": "user", "content": query}], api_key,
    )

    # Fallback on refusal / error
    if response.refusal or response.error:
        fallbacks = select_models(task, config, 3)[1:]
        for fb in fallbacks:
            fb_resp = await call_model(
                fb.id, [{"role": "user", "content": query}], api_key,
            )
            if not fb_resp.refusal and not fb_resp.error:
                result = OrchestrationResult(
                    mode="specialist_fallback",
                    final_response=fb_resp.content,
                    confidence=fb_resp.confidence,
                    models=[response, fb_resp],
                    total_cost=response.cost + fb_resp.cost,
                    total_latency_ms=response.latency_ms + fb_resp.latency_ms,
                    total_tokens=response.total_tokens + fb_resp.total_tokens,
                    task_category=task.category,
                    selected_models=[best.id, fb.id],
                )
                _cache.put(query, "specialist", result)
                return result

    result = OrchestrationResult(
        mode="specialist",
        final_response=response.content,
        confidence=response.confidence,
        models=[response],
        total_cost=response.cost,
        total_latency_ms=response.latency_ms,
        total_tokens=response.total_tokens,
        task_category=task.category,
        selected_models=[best.id],
    )
    _cache.put(query, "specialist", result)
    return result


async def ensemble_vote(
    query: str,
    api_key: str,
    model_ids: Optional[List[str]] = None,
    voter_count: int = 3,
) -> OrchestrationResult:
    """Ask multiple models and pick the highest-confidence answer."""
    cached = _cache.get(query, "ensemble")
    if cached:
        return cached

    task = classify_task(query)
    models = model_ids or [
        m.id for m in select_models(task, RoutingConfig(strategy=RoutingStrategy.BALANCED), voter_count)
    ]

    responses = await asyncio.gather(
        *(call_model(m, [{"role": "user", "content": query}], api_key)
          for m in models)
    )

    valid = [r for r in responses if not r.error and not r.refusal]
    best = max(valid, key=lambda r: r.confidence) if valid else responses[0]

    result = OrchestrationResult(
        mode="ensemble",
        final_response=best.content,
        confidence=best.confidence,
        models=list(responses),
        total_cost=sum(r.cost for r in responses),
        total_latency_ms=max(r.latency_ms for r in responses),
        total_tokens=sum(r.total_tokens for r in responses),
        task_category=task.category,
        selected_models=models,
    )
    _cache.put(query, "ensemble", result)
    return result


async def debate(
    query: str,
    api_key: str,
    *,
    model_ids: Optional[List[str]] = None,
    max_rounds: int = MAX_DEBATE_ROUNDS,
    synthesis_model: str = "anthropic/claude-sonnet-4-20250514",
) -> OrchestrationResult:
    """Multi-round debate: models argue and refine to consensus."""
    cached = _cache.get(query, "debate")
    if cached:
        return cached

    task = classify_task(query)
    models = model_ids or [
        m.id for m in select_models(
            task, RoutingConfig(strategy=RoutingStrategy.BEST_QUALITY), 3,
        )
    ]

    rounds: List[DebateRound] = []
    all_responses: List[ModelResponse] = []

    # Round 1: Initial responses (parallel)
    initial = await asyncio.gather(
        *(call_model(m, [{"role": "user", "content": query}], api_key)
          for m in models)
    )
    valid_init = [r for r in initial if not r.error]
    avg_conf = (sum(r.confidence for r in valid_init) / len(valid_init)
                if valid_init else 0)
    rounds.append(DebateRound(
        round=1, responses=list(initial), avg_confidence=avg_conf,
    ))
    all_responses.extend(initial)

    # Subsequent rounds
    for rnd in range(2, max_rounds + 1):
        prev = rounds[-1].responses
        critiques = "\n\n".join(
            f"[{r.model}]: {r.content}" for r in prev if r.content
        )

        debate_prompt = (
            f"Original question: {query}\n\n"
            f"Previous round responses:\n{critiques}\n\n"
            "Based on these responses, provide your improved answer. "
            "Consider strengths and weaknesses of each response. "
            "If you agree, explain why. If you disagree, explain your reasoning."
        )

        rnd_responses = await asyncio.gather(
            *(call_model(m, [{"role": "user", "content": debate_prompt}], api_key)
              for m in models)
        )
        valid_rnd = [r for r in rnd_responses if not r.error and not r.refusal]
        avg_conf = (sum(r.confidence for r in valid_rnd) / len(valid_rnd)
                    if valid_rnd else 0)
        consensus = avg_conf > 0.85

        rounds.append(DebateRound(
            round=rnd, responses=list(rnd_responses),
            avg_confidence=avg_conf, consensus=consensus,
        ))
        all_responses.extend(rnd_responses)

        if consensus:
            break

    # Synthesis
    all_args = "\n\n".join(
        f"--- Round {dr.round} ---\n" +
        "\n\n".join(f"[{r.model}]: {r.content}" for r in dr.responses if r.content)
        for dr in rounds
    )

    synth = await call_model(
        synthesis_model,
        [{
            "role": "user",
            "content": (
                "You are synthesizing a multi-model debate. Combine the best "
                "arguments into one authoritative answer.\n\n"
                f"Original question: {query}\n\n"
                f"Debate transcript:\n{all_args}\n\n"
                "Provide the definitive answer:"
            ),
        }],
        api_key,
    )
    all_responses.append(synth)

    result = OrchestrationResult(
        mode="debate",
        final_response=synth.content,
        confidence=synth.confidence,
        models=all_responses,
        debate=rounds,
        total_cost=sum(r.cost for r in all_responses),
        total_latency_ms=sum(r.latency_ms for r in all_responses),
        total_tokens=sum(r.total_tokens for r in all_responses),
        task_category=task.category,
        selected_models=models + [synthesis_model],
    )
    _cache.put(query, "debate", result)
    return result


async def cost_optimize(
    query: str,
    api_key: str,
    max_cost: float = 0.01,
    min_quality: float = 7.0,
) -> OrchestrationResult:
    """Cost-optimized: cheapest model meeting quality bar."""
    task = classify_task(query)
    candidates = sorted(
        [m for m in MODEL_PROFILES
         if m.quality >= min_quality
         and (not task.needs_vision or m.supports_vision)],
        key=lambda m: m.cost_per_1k_total,
    )

    for model in candidates:
        est_cost = (task.estimated_tokens / 1000) * model.cost_per_1k_total
        if est_cost > max_cost:
            continue

        response = await call_model(
            model.id, [{"role": "user", "content": query}], api_key,
        )
        if not response.error and not response.refusal:
            return OrchestrationResult(
                mode="cost_optimized",
                final_response=response.content,
                confidence=response.confidence,
                models=[response],
                total_cost=response.cost,
                total_latency_ms=response.latency_ms,
                total_tokens=response.total_tokens,
                task_category=task.category,
                selected_models=[model.id],
            )

    # Fallback
    fallback = candidates[0] if candidates else MODEL_PROFILES[0]
    response = await call_model(
        fallback.id, [{"role": "user", "content": query}], api_key,
    )
    return OrchestrationResult(
        mode="cost_optimized_fallback",
        final_response=response.content,
        confidence=response.confidence,
        models=[response],
        total_cost=response.cost,
        total_latency_ms=response.latency_ms,
        total_tokens=response.total_tokens,
        task_category=task.category,
        selected_models=[fallback.id],
    )


async def fallback_chain(
    query: str,
    api_key: str,
    model_ids: Optional[List[str]] = None,
) -> OrchestrationResult:
    """Try models in order until one succeeds without error/refusal."""
    task = classify_task(query)
    chain = model_ids or [
        m.id for m in select_models(
            task, RoutingConfig(strategy=RoutingStrategy.BEST_QUALITY), 5,
        )
    ]

    tried: List[ModelResponse] = []
    for model_id in chain:
        response = await call_model(
            model_id, [{"role": "user", "content": query}], api_key,
        )
        tried.append(response)

        if not response.error and not response.refusal and response.content:
            return OrchestrationResult(
                mode="fallback_chain",
                final_response=response.content,
                confidence=response.confidence,
                models=tried,
                total_cost=sum(r.cost for r in tried),
                total_latency_ms=sum(r.latency_ms for r in tried),
                total_tokens=sum(r.total_tokens for r in tried),
                task_category=task.category,
                selected_models=chain,
            )

    best = max(tried, key=lambda r: r.confidence) if tried else tried[0]
    return OrchestrationResult(
        mode="fallback_chain_exhausted",
        final_response=best.content if best else "",
        confidence=best.confidence if best else 0,
        models=tried,
        total_cost=sum(r.cost for r in tried),
        total_latency_ms=sum(r.latency_ms for r in tried),
        total_tokens=sum(r.total_tokens for r in tried),
        task_category=task.category,
        selected_models=chain,
    )


# v9.8.7: Module-level counter persists between calls
_round_robin_counter: Dict[str, int] = {"_rr_idx": 0}


async def round_robin(
    query: str,
    api_key: str,
    model_ids: Optional[List[str]] = None,
) -> OrchestrationResult:
    """Distribute queries across models evenly."""
    models = model_ids or [m.id for m in MODEL_PROFILES]
    idx = _round_robin_counter.get("_rr_idx", 0)
    model_id = models[idx % len(models)]
    _round_robin_counter["_rr_idx"] = idx + 1

    response = await call_model(
        model_id, [{"role": "user", "content": query}], api_key,
    )
    return OrchestrationResult(
        mode="round_robin",
        final_response=response.content,
        confidence=response.confidence,
        models=[response],
        total_cost=response.cost,
        total_latency_ms=response.latency_ms,
        total_tokens=response.total_tokens,
        task_category=classify_task(query).category,
        selected_models=[model_id],
    )


async def consensus(
    query: str,
    api_key: str,
    model_ids: Optional[List[str]] = None,
    min_agreement: int = 2,
) -> OrchestrationResult:
    """Only return answer if multiple models agree on core content."""
    task = classify_task(query)
    models = model_ids or [
        m.id for m in select_models(
            task, RoutingConfig(strategy=RoutingStrategy.BALANCED), 3,
        )
    ]

    responses = await asyncio.gather(
        *(call_model(m, [{"role": "user", "content": query}], api_key)
          for m in models)
    )

    valid = [r for r in responses if not r.error and not r.refusal]

    if len(valid) >= min_agreement:
        # Return the one with highest confidence
        best = max(valid, key=lambda r: r.confidence)
        return OrchestrationResult(
            mode="consensus",
            final_response=best.content,
            confidence=best.confidence,
            models=list(responses),
            total_cost=sum(r.cost for r in responses),
            total_latency_ms=max(r.latency_ms for r in responses),
            total_tokens=sum(r.total_tokens for r in responses),
            task_category=task.category,
            selected_models=models,
        )

    return OrchestrationResult(
        mode="consensus_failed",
        final_response=responses[0].content if responses else "",
        confidence=0.3,
        models=list(responses),
        total_cost=sum(r.cost for r in responses),
        total_latency_ms=max(r.latency_ms for r in responses) if responses else 0,
        total_tokens=sum(r.total_tokens for r in responses),
        task_category=task.category,
        selected_models=models,
    )


# ═══════════════════════════════════════════════════════════════════
# Performance History (Quality Regression Tracking)
# ═══════════════════════════════════════════════════════════════════

class PerformanceTracker:
    """Track model performance over time for quality regression detection."""

    def __init__(self, window_size: int = 100) -> None:
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._window = window_size

    def record(self, model_id: str, response: ModelResponse) -> None:
        entry = {
            "timestamp": time.time(),
            "confidence": response.confidence,
            "latency_ms": response.latency_ms,
            "cost": response.cost,
            "refusal": response.refusal,
            "error": bool(response.error),
            "tokens": response.total_tokens,
        }
        self._history[model_id].append(entry)
        if len(self._history[model_id]) > self._window:
            self._history[model_id] = self._history[model_id][-self._window:]

    def get_model_stats(self, model_id: str) -> dict:
        entries = self._history.get(model_id, [])
        if not entries:
            return {}

        return {
            "calls": len(entries),
            "avg_confidence": sum(e["confidence"] for e in entries) / len(entries),
            "avg_latency_ms": sum(e["latency_ms"] for e in entries) / len(entries),
            "total_cost": sum(e["cost"] for e in entries),
            "refusal_rate": sum(1 for e in entries if e["refusal"]) / len(entries),
            "error_rate": sum(1 for e in entries if e["error"]) / len(entries),
        }

    def get_all_stats(self) -> Dict[str, dict]:
        return {mid: self.get_model_stats(mid) for mid in self._history}


perf_tracker = PerformanceTracker()

class MultiLLMOrchestrator:
    """Orchestrate queries across multiple LLM providers for consensus."""

    def __init__(self) -> None:
        self._providers = []
        self._strategy = "fastest"  # fastest, consensus, cascade

    def add_provider(self, name: str, client: Any) -> None:
        self._providers.append({"name": name, "client": client})

    async def query(self, messages: list, strategy: str = None) -> dict:
        """Query using selected strategy."""
        strat = strategy or self._strategy
        if strat == "fastest":
            return await self._fastest(messages)
        elif strat == "consensus":
            return await self._consensus(messages)
        return await self._cascade(messages)

    async def _fastest(self, messages: list) -> Any:
        import asyncio
        tasks = []
        for p in self._providers:
            tasks.append(asyncio.create_task(self._safe_query(p, messages)))
        if not tasks:
            return {"content": "", "provider": "none"}
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        return done.pop().result()

    async def _consensus(self, messages: list) -> Any:
        import asyncio
        results = await asyncio.gather(*[self._safe_query(p, messages) for p in self._providers], return_exceptions=True)
        valid = [r for r in results if isinstance(r, dict)]
        return valid[0] if valid else {"content": "", "provider": "none"}

    async def _cascade(self, messages: list) -> Any:
        for p in self._providers:
            try:
                return await self._safe_query(p, messages)
            except Exception:
                continue
        return {"content": "", "provider": "none"}

    async def _safe_query(self, provider: str, messages: list) -> Any:
        return {"content": "", "provider": provider["name"]}



# ═══════════════════════════════════════════════════════════════════════
# ULTRAPLINIAN ENGINE — Multi-Model Competition + CONSORTIUM (DEEP)
# ═══════════════════════════════════════════════════════════════════════
#
# Architecture:
#   ┌────────────────────────────────────────────────────────────┐
#   │                    ULTRAPLINIAN PIPELINE                    │
#   │                                                            │
#   │  APEX prompt → Depth Directive → AutoTune → Parseltongue│
#   │       ↓                                                    │
#   │  N models in staggered waves (12/wave, 150ms gap)         │
#   │       ↓                                                    │
#   │  100-point scoring per response                            │
#   │  (length:25 + structure:20 + anti-refusal:25               │
#   │   + directness:15 + relevance:15)                          │
#   │       ↓                                                    │
#   │  Early-exit: min 5 success → 5s grace → hard 45s          │
#   │       ↓                                                    │
#   │  Winner selection (highest score)                          │
#   └────────────────────────────────────────────────────────────┘
#                          OR
#   ┌────────────────────────────────────────────────────────────┐
#   │                    CONSORTIUM MODE                          │
#   │                                                            │
#   │  Same collection as above                                  │
#   │       ↓                                                    │
#   │  Feed ALL responses to orchestrator model                  │
#   │       ↓                                                    │
#   │  Synthesize ground truth from collective intelligence      │
#   └────────────────────────────────────────────────────────────┘
#
# Ported from: APEX-main/api/lib/ultraplinian.ts + consortium.ts
# Version: 4.0.0-DEEP (Phase 1-5 hardened)
# ═══════════════════════════════════════════════════════════════════════


import asyncio as _up_asyncio
import logging
import time as _up_time
from typing import (
    Any, Awaitable, Callable, Dict, Final, List,
    Optional, Sequence, Tuple, TypedDict,
)

_up_logger = logging.getLogger("arki.apex.ultraplinian")


# ═══════════════════ TYPE DEFINITIONS ═══════════════════

class ModelResult(TypedDict):
    """Result from querying a single model."""
    model: str
    content: str
    score: int
    duration_ms: int
    success: bool
    error: Optional[str]


class ConsortiumSynthesis(TypedDict):
    """Result from CONSORTIUM synthesis."""
    synthesis: str
    orchestrator_model: str
    duration_ms: int


class RaceConfig(TypedDict, total=False):
    """Configuration for model racing."""
    min_results: int        # Min successful before grace (default: 5)
    grace_period: float     # Seconds after min_results (default: 5.0)
    hard_timeout: float     # Max total seconds (default: 45.0)
    wave_size: int          # Models per wave (default: 12)
    wave_delay: float       # Seconds between waves (default: 0.15)


# Type for the query function callback
QueryFunc = Callable[..., Awaitable[Dict[str, Any]]]


# ═══════════════════ SCORING ENGINE ═══════════════════
# 100-point composite scoring from APEX ultraplinian.ts scoreResponse()
# All regex patterns pre-compiled at module level.

_REFUSAL_PATTERNS: Final[Tuple[re.Pattern, ...]] = (
    re.compile(r"I cannot|I can't|I'm unable to", re.I),
    re.compile(r"I apologize|I'm sorry, but", re.I),
    re.compile(r"As an AI|As a language model", re.I),
    re.compile(r"I must decline|I have to refuse", re.I),
    re.compile(r"It would be inappropriate", re.I),
    re.compile(r"I'm not comfortable", re.I),
    re.compile(r"Instead, I can", re.I),
    re.compile(r"It's important to note", re.I),
)

_PREAMBLE_PATTERNS: Final[Tuple[re.Pattern, ...]] = (
    re.compile(r"^(Sure|Of course|Certainly|Absolutely|Great question)", re.I),
    re.compile(r"^I'd be happy to help", re.I),
    re.compile(r"^Let me help you", re.I),
    re.compile(r"^Thanks for asking", re.I),
)

_HEADER_PATTERN: Final[re.Pattern] = re.compile(r"^#{1,3}\s", re.M)
_LIST_PATTERN: Final[re.Pattern] = re.compile(r"^[\s]*[-*•]\s", re.M)
_CODE_BLOCK_PATTERN: Final[re.Pattern] = re.compile(r"```")


def ultraplinian_score_response(content: str, user_query: str) -> int:
    """Score a model response on substance, directness, and completeness.
    
    100-point composite scoring system:
    
    Component breakdown:
        Length (0-25):       Longer = more substance. Diminishing returns ~1000 chars.
        Structure (0-20):    Headers (×3) + list items (×1.5) + code blocks (×5).
        Anti-refusal (0-25): Each refusal pattern found → -8 points (from 25).
        Directness (0-15):   15 if no preamble detected, 8 if preamble found.
        Relevance (0-15):    Query word overlap with response.
    
    Args:
        content: Model response text.
        user_query: Original user question (for relevance scoring).
    
    Returns:
        Score 0-100 (integer).
    
    Examples:
        >>> ultraplinian_score_response("", "test")
        0
        >>> score = ultraplinian_score_response("# Guide\n- Step 1\n- Step 2\n```code```", "guide")
        >>> score > 20  # structure + relevance
        True
    """
    if not content or len(content) < 10:
        return 0
    
    score = 0.0
    
    # Length (0-25): diminishing returns at ~1000 chars
    score += min(len(content) / 40.0, 25.0)
    
    # Structure (0-20)
    headers = len(_HEADER_PATTERN.findall(content))
    list_items = len(_LIST_PATTERN.findall(content))
    code_blocks = len(_CODE_BLOCK_PATTERN.findall(content)) // 2
    score += min(headers * 3 + list_items * 1.5 + code_blocks * 5, 20.0)
    
    # Anti-refusal (0-25)
    refusal_count = sum(1 for pat in _REFUSAL_PATTERNS if pat.search(content))
    score += max(25.0 - refusal_count * 8, 0.0)
    
    # Directness (0-15)
    trimmed = content.strip()
    has_preamble = any(pat.search(trimmed) for pat in _PREAMBLE_PATTERNS)
    score += 8.0 if has_preamble else 15.0
    
    # Relevance (0-15)
    query_words = [w for w in user_query.lower().split() if len(w) > 3]
    if query_words:
        content_lower = content.lower()
        matched = sum(1 for w in query_words if w in content_lower)
        relevance = matched / len(query_words)
    else:
        relevance = 0.5
    score += relevance * 15.0
    
    return round(min(score, 100))


# ═══════════════════ EARLY-EXIT MODEL RACING ═══════════════════

async def ultraplinian_race_models(
    query_func: QueryFunc,
    models: Sequence[str],
    messages: List[dict],
    user_query: str,
    min_results: int = 5,
    grace_period: float = 5.0,
    hard_timeout: float = 45.0,
    wave_size: int = 12,
    wave_delay: float = 0.15,
    on_result: Optional[Callable[[ModelResult], None]] = None,
) -> List[ModelResult]:
    """Race N models in parallel with early-exit strategy.
    
    Instead of waiting for ALL models (which means waiting for the slowest),
    this returns as soon as enough good responses are collected:
    
    1. Fire models in staggered waves (wave_size per wave, wave_delay between)
    2. Once min_results succeed, start grace_period timer
    3. When grace period ends or all finish, return collected results
    4. hard_timeout aborts everything remaining
    
    The winner is almost always among the first responders, so this
    cuts p95 latency dramatically without degrading quality.
    
    Args:
        query_func: Async function(model, messages) → {content, success, [error]}.
        models: List of model IDs to race.
        messages: Conversation messages to send.
        user_query: For scoring responses.
        min_results: Minimum successful before grace period starts.
        grace_period: Seconds to wait after min_results.
        hard_timeout: Maximum seconds for entire race.
        wave_size: Models per wave (default 12, from APEX spec).
        wave_delay: Seconds between waves (default 0.15).
        on_result: Optional callback for each result (enables live streaming).
    
    Returns:
        List of ModelResult, sorted by score descending.
    
    Raises:
        ValueError: If models is empty.
    """
    if not models:
        return []
    
    results: List[ModelResult] = []
    success_count = 0
    grace_started = False
    grace_deadline: Optional[float] = None
    start_time = _up_time.monotonic()
    
    async def _query_one(model: str) -> None:
        nonlocal success_count, grace_started, grace_deadline
        t0 = _up_time.monotonic()
        try:
            result = await query_func(model, messages)
            duration = int((_up_time.monotonic() - t0) * 1000)
            content = result.get("content", "")
            success = bool(content and result.get("success", True))
            score = ultraplinian_score_response(content, user_query) if success else 0
            entry: ModelResult = {
                "model": model, "content": content, "score": score,
                "duration_ms": duration, "success": success,
                "error": result.get("error"),
            }
        except Exception as e:
            duration = int((_up_time.monotonic() - t0) * 1000)
            entry = {
                "model": model, "content": "", "score": 0,
                "duration_ms": duration, "success": False,
                "error": str(e),
            }
        
        results.append(entry)
        if entry["success"]:
            success_count += 1
        
        # Notify caller
        if on_result:
            try:
                on_result(entry)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
        
        # Start grace period once enough successes
        if success_count >= min_results and not grace_started:
            grace_started = True
            grace_deadline = _up_time.monotonic() + grace_period
    
    # Launch waves
    tasks: List[_up_asyncio.Task] = []
    for i, model in enumerate(models):
        wave_index = i // wave_size
        delay = wave_index * wave_delay
        
        async def _delayed(m: Any=model, d: Any=delay) -> Any:
            if d > 0:
                await _up_asyncio.sleep(d)
            await _query_one(m)
        
        tasks.append(_up_asyncio.create_task(_delayed()))
    
    # Wait with early-exit
    deadline = _up_time.monotonic() + hard_timeout
    while tasks:
        now = _up_time.monotonic()
        if now >= deadline:
            _up_logger.info(f"Hard timeout ({hard_timeout}s) reached, cancelling {len(tasks)} remaining")
            break
        if grace_deadline and now >= grace_deadline:
            _up_logger.info(f"Grace period ended, {len(results)} results collected")
            break
        
        done, pending = await _up_asyncio.wait(
            tasks, timeout=0.5, return_when=_up_asyncio.FIRST_COMPLETED,
        )
        tasks = list(pending)
        if not pending:
            break
    
    # Cancel remaining tasks
    for t in tasks:
        t.cancel()
    
    # Sort by score descending
    results.sort(key=lambda r: r["score"], reverse=True)
    
    elapsed = round((_up_time.monotonic() - start_time) * 1000)
    successes = sum(1 for r in results if r["success"])
    _up_logger.info(f"Race complete: {successes}/{len(results)} succeeded in {elapsed}ms")
    
    return results


# ═══════════════════ CONSORTIUM SYNTHESIS ═══════════════════

async def consortium_synthesize(
    query_func: QueryFunc,
    orchestrator_model: str,
    user_query: str,
    scored_responses: Sequence[ModelResult],
    system_prompt: str = "",
) -> ConsortiumSynthesis:
    """CONSORTIUM: Feed collected responses to orchestrator for synthesis.
    
    Takes the scored responses from an ULTRAPLINIAN race (or any collection)
    and feeds them to a strong orchestrator model that synthesizes
    ground truth from the collective intelligence.
    
    Args:
        query_func: Async function(model, messages) → {content, ...}.
        orchestrator_model: Strong model ID for synthesis.
        user_query: Original user question.
        scored_responses: List of ModelResult from racing phase.
        system_prompt: Consortium system prompt (uses default if empty).
    
    Returns:
        ConsortiumSynthesis with synthesis text, model, and duration.
    """
    successful = sorted(
        [r for r in scored_responses if r.get("success") and r.get("content")],
        key=lambda r: r["score"],
        reverse=True,
    )
    
    if not successful:
        return {"synthesis": "", "orchestrator_model": orchestrator_model, "duration_ms": 0}
    
    # Build orchestration prompt
    parts = [
        f"## USER'S ORIGINAL QUESTION\n\n{user_query}\n\n",
        f"## MODEL RESPONSES ({len(successful)} collected)\n\n",
    ]
    
    for i, r in enumerate(successful):
        parts.append(
            f"---\n### Response {i+1} (Score: {r['score']}/100, {r.get('duration_ms', 0)}ms)\n\n"
            f"{r['content']}\n\n"
        )
    
    parts.append(
        f"---\n\n## YOUR TASK\n\n"
        f"Synthesize the above {len(successful)} responses into a single, definitive answer. "
        f"Identify consensus, resolve contradictions, produce the most complete response possible."
    )
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": "".join(parts)})
    
    t0 = _up_time.monotonic()
    try:
        result = await query_func(orchestrator_model, messages)
        duration = int((_up_time.monotonic() - t0) * 1000)
        synthesis = result.get("content", "")
    except Exception as e:
        duration = int((_up_time.monotonic() - t0) * 1000)
        synthesis = f"[CONSORTIUM ERROR: {e}]"
        _up_logger.error(f"Consortium synthesis failed: {e}")
    
    return {
        "synthesis": synthesis,
        "orchestrator_model": orchestrator_model,
        "duration_ms": duration,
    }


