
from __future__ import annotations
"""
utils/smart_router.py — Smart Model Router v26.0
═══════════════════════════════════════════════════════════════════
Auto-selects the best model for each query based on:
  1. Query type classification (code, math, creative, analysis, Persian, search)
  2. Complexity level (simple → expert)
  3. User's selected tier (fast, standard, smart, pro, power, ultra)
  4. Model performance history (Phase 5 integration)
  5. Language detection (Persian → models with strong Farsi support)

Architecture:
  User query → SmartRouter.select() → (best_model_key, confidence, reason)
"""

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple, Any

logger = logging.getLogger("arki.smart_router")


# ═══════════════════ QUERY TYPE CLASSIFICATION ═══════════════════

class QueryType(str, Enum):
    CODE = "code"
    MATH = "math"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    PERSIAN_CULTURAL = "persian"
    SEARCH = "search"
    MULTILINGUAL = "multilingual"
    REASONING = "reasoning"
    GENERAL = "general"


# Pattern weights: (pattern, QueryType, weight)
_QUERY_PATTERNS: List[Tuple[re.Pattern, QueryType, float]] = [
    # Code patterns
    (re.compile(r"(```|def\s|class\s|import\s|function\s|=>|\{\}|\(\)|console\.|print\(|return\s|for\s.*in\s|while\s|if\s.*:|elif|async\s|await\s)", re.I), QueryType.CODE, 0.9),
    (re.compile(r"(کد|برنامه.?نویس|پایتون|جاوا|دیباگ|خطا.*کد|باگ|api|sdk|endpoint|regex|sql|html|css|json|xml|git|docker|kubernetes)", re.I), QueryType.CODE, 0.8),
    (re.compile(r"(code|debug|compile|runtime|syntax|algorithm|refactor|unittest|deploy|backend|frontend|database|query)", re.I), QueryType.CODE, 0.7),

    # Math patterns
    (re.compile(r"(\d+\s*[+\-*/^%]\s*\d+|\bx\s*=|integrate|derivative|matrix|vector|equation|factorial|probability|sqrt|log\b|sin\b|cos\b|lim\b)", re.I), QueryType.MATH, 0.9),
    (re.compile(r"(ریاضی|معادله|انتگرال|مشتق|ماتریس|بردار|احتمال|آمار|محاسبه|فرمول|هندسه|مثلثات|لگاریتم)", re.I), QueryType.MATH, 0.85),
    (re.compile(r"(theorem|proof|calculus|algebra|geometry|trigonometry|statistics|combinatorics|optimization)", re.I), QueryType.MATH, 0.8),

    # Reasoning / Logic
    (re.compile(r"(چرا|دلیل|استدلال|تحلیل\s*کن|بررسی\s*کن|مقایسه|نتیجه.?گیری|فرض|اثبات|منطق)", re.I), QueryType.REASONING, 0.7),
    (re.compile(r"(why|reason|analyze|compare|contrast|conclude|hypothesis|logic|prove|argue|evaluate|assess|critique)", re.I), QueryType.REASONING, 0.7),

    # Creative patterns
    (re.compile(r"(شعر|داستان|قصه|خلاق|تخیل|نام.?گذاری|شعار|تبلیغ|لوگو|طراحی|هنر|ادبی|غزل|رباعی|مثنوی)", re.I), QueryType.CREATIVE, 0.85),
    (re.compile(r"(poem|story|creative|imagine|write.*story|song|lyric|slogan|brand|design|art|fiction|narrative|metaphor)", re.I), QueryType.CREATIVE, 0.8),

    # Analysis patterns
    (re.compile(r"(تحلیل|بررسی|ارزیابی|گزارش|آمار|داده|روند|مقایسه.*با|نقاط.*قوت|نقاط.*ضعف|swot)", re.I), QueryType.ANALYSIS, 0.75),
    (re.compile(r"(analyze|report|trend|data|statistic|benchmark|evaluate|assessment|survey|dashboard|metric|kpi)", re.I), QueryType.ANALYSIS, 0.75),

    # Persian cultural / language specific
    (re.compile(r"(فارسی|ایران|تاریخ.*ایران|فرهنگ.*ایران|ادبیات.*فارسی|حافظ|سعدی|فردوسی|مولانا|شاهنامه|نوروز|یلدا|رمضان)", re.I), QueryType.PERSIAN_CULTURAL, 0.9),
    (re.compile(r"(ترجمه.*فارسی|به.*فارسی|persian|farsi|iran)", re.I), QueryType.PERSIAN_CULTURAL, 0.7),

    # Search patterns
    (re.compile(r"(جستجو|سرچ|پیدا.*کن|کجا|چطوری.*پیدا|آخرین.*اخبار|قیمت|آب.*هوا)", re.I), QueryType.SEARCH, 0.8),
    (re.compile(r"(search|find|look.*up|where|latest.*news|price|weather|when.*did|who.*is)", re.I), QueryType.SEARCH, 0.7),
]


# ═══════════════════ MODEL STRENGTHS MAP ═══════════════════

# Best models per query type for each tier
# Format: {tier: {query_type: [model_key_priority_list]}}
_TIER_ROUTING: Dict[str, Dict[str, List[str]]] = {
    "fast": {
        QueryType.CODE:       ["g-deepseek-chat", "g-gemini-flash", "g-qwen3-8b"],
        QueryType.MATH:       ["g-gemini-flash", "g-deepseek-chat", "g-qwen3-4b"],
        QueryType.CREATIVE:   ["g-gemini-flash", "g-llama8", "g-mistral-small"],
        QueryType.REASONING:  ["g-deepseek-chat", "g-gemini-flash", "g-deepseek-r1-lite"],
        QueryType.ANALYSIS:   ["g-gemini-flash", "g-deepseek-chat", "g-nemotron-nano"],
        QueryType.PERSIAN_CULTURAL: ["g-gemini-flash", "g-deepseek-chat", "g-qwen3-8b"],
        QueryType.SEARCH:     ["g-sonar", "g-gemini-flash", "g-deepseek-chat"],
        QueryType.GENERAL:    ["g-gemini-flash", "g-deepseek-chat", "g-llama8"],
    },
    "standard": {
        QueryType.CODE:       ["g-deepseek-v3", "g-claude-sonnet35", "g-qwen25-72b"],
        QueryType.MATH:       ["g-phi4-reasoning", "g-gemini25-pro", "g-deepseek-v3"],
        QueryType.CREATIVE:   ["g-claude-sonnet4", "g-claude-sonnet35", "g-llama33-70b"],
        QueryType.REASONING:  ["g-phi4-reasoning", "g-gemini25-pro", "g-claude-sonnet4"],
        QueryType.ANALYSIS:   ["g-gemini25-pro", "g-claude-sonnet4", "g-deepseek-v3"],
        QueryType.PERSIAN_CULTURAL: ["g-cohere-aya", "g-gemini25-pro", "g-claude-sonnet4"],
        QueryType.SEARCH:     ["g-gpt4o", "g-gemini25-pro", "g-llama4-scout"],
        QueryType.GENERAL:    ["g-claude-sonnet4", "g-gemini25-pro", "g-gpt4o"],
    },
    "smart": {
        QueryType.CODE:       ["g-smart-codestral", "g-smart-deepseek-v3", "g-smart-o3-mini"],
        QueryType.MATH:       ["g-smart-o3-mini", "g-smart-phi4-reason", "g-smart-qwq"],
        QueryType.CREATIVE:   ["g-smart-claude-sonnet4", "g-smart-gemini-pro", "g-smart-kimi-k2"],
        QueryType.REASONING:  ["g-smart-deepseek-r1", "g-smart-qwq", "g-smart-arcee"],
        QueryType.ANALYSIS:   ["g-smart-gemini-pro", "g-smart-claude-sonnet4", "g-smart-deepseek-v3"],
        QueryType.PERSIAN_CULTURAL: ["g-smart-aya", "g-smart-gemini-pro", "g-smart-command-r"],
        QueryType.SEARCH:     ["g-smart-gpt4o", "g-smart-llama4-scout", "g-smart-gemini-pro"],
        QueryType.GENERAL:    ["g-smart-gemini-pro", "g-smart-claude-sonnet4", "g-smart-deepseek-v3"],
    },
    "pro": {
        QueryType.CODE:       ["g-deepseek-r1", "g-gpt53-chat", "g-gemini3-pro"],
        QueryType.MATH:       ["g-gpt53-chat", "g-o4-mini", "g-deepseek-r1"],
        QueryType.CREATIVE:   ["g-claude-opus46", "g-gemini3-pro", "g-gpt52"],
        QueryType.REASONING:  ["g-deepseek-r1", "g-o4-mini", "g-gpt53-chat"],
        QueryType.ANALYSIS:   ["g-gemini3-pro", "g-claude-opus46", "g-gpt52"],
        QueryType.PERSIAN_CULTURAL: ["g-command-r-plus", "g-gemini3-pro", "g-gpt52"],
        QueryType.SEARCH:     ["g-gpt52", "g-gemini3-pro", "g-llama31-405b"],
        QueryType.GENERAL:    ["g-gemini3-pro", "g-gpt52", "g-claude-opus46"],
    },
    "power": {
        QueryType.CODE:       ["g-qwen3-coder", "g-kimi-k2", "g-grok4"],
        QueryType.MATH:       ["g-gpt54", "g-qwen3-235b", "g-grok4"],
        QueryType.CREATIVE:   ["g-llama4-maverick", "g-mistral-large", "g-kimi-k2"],
        QueryType.REASONING:  ["g-qwen3-235b", "g-gpt54", "g-grok4"],
        QueryType.ANALYSIS:   ["g-gemini31-pro", "g-qwen3-235b", "g-minimax"],
        QueryType.PERSIAN_CULTURAL: ["g-gemini31-pro", "g-qwen3-235b", "g-kimi-k2"],
        QueryType.SEARCH:     ["g-gemini31-pro", "g-grok4", "g-kimi-k2"],
        QueryType.GENERAL:    ["g-kimi-k2", "g-gemini31-pro", "g-qwen3-235b"],
    },
    "ultra": {
        QueryType.CODE:       ["g-qwen25-coder", "g-codestral", "g-devstral"],
        QueryType.MATH:       ["g-o3", "g-qwq-32b", "g-grok4-fast"],
        QueryType.CREATIVE:   ["g-claude-opus4", "g-grok4-fast", "g-grok41-fast"],
        QueryType.REASONING:  ["g-o3", "g-claude-opus4", "g-qwq-32b"],
        QueryType.ANALYSIS:   ["g-claude-opus4", "g-o3", "g-grok4-fast"],
        QueryType.PERSIAN_CULTURAL: ["g-claude-opus4", "g-grok4-fast", "g-qwq-32b"],
        QueryType.SEARCH:     ["g-grok4-fast", "g-grok41-fast", "g-claude-opus4"],
        QueryType.GENERAL:    ["g-claude-opus4", "g-grok4-fast", "g-o3"],
    },
}


@dataclass
class RouterResult:
    """Result from smart model selection."""
    model_key: str
    query_type: QueryType
    confidence: float
    reason: str
    alternatives: List[str] = field(default_factory=list)


def _detect_language(text: str) -> str:
    """Detect dominant language: 'fa' for Persian, 'en' for English, 'mixed'."""
    persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    total = persian_chars + latin_chars
    if total == 0:
        return "en"
    ratio = persian_chars / total
    if ratio > 0.6:
        return "fa"
    elif ratio > 0.3:
        return "mixed"
    return "en"


def _classify_query(text: str) -> Tuple[QueryType, float]:
    """Classify query into type with confidence score."""
    scores: Dict[QueryType, float] = {}
    for qt in QueryType:
        scores[qt] = 0.0

    text_lower = text.lower()

    for pattern, qtype, weight in _QUERY_PATTERNS:
        matches = pattern.findall(text_lower)
        if matches:
            scores[qtype] += weight * min(len(matches), 3)  # Cap at 3 matches

    # Boost Persian cultural if text is in Persian
    if _detect_language(text) in ("fa", "mixed"):
        scores[QueryType.PERSIAN_CULTURAL] += 0.3

    # Default general
    if all(v < 0.3 for v in scores.values()):
        scores[QueryType.GENERAL] = 0.5

    best_type = max(scores, key=lambda t: scores[t])
    total = sum(scores.values()) or 1.0
    confidence = scores[best_type] / total

    return best_type, round(min(confidence, 1.0), 3)


class SmartRouter:
    """
    Intelligent model router for Arki Engine.

    Routes queries to optimal models based on query classification,
    model strengths, and performance history.
    """

    def __init__(self) -> None:
        self._performance_data: Dict[str, Dict[str, float]] = {}  # model_key → {metric: value}
        self._selection_history: List[Dict] = []

    def select(
        self,
        text: str,
        tier: str = "standard",
        user_id: int = 0,
        current_model: str | None = None,
    ) -> RouterResult:
        """
        Select the best model for a query.

        Args:
            text: User's query text
            tier: User's selected APEX tier
            user_id: Telegram user ID
            current_model: User's currently selected model (may override)

        Returns:
            RouterResult with best model and reasoning
        """
        query_type, confidence = _classify_query(text)
        language = _detect_language(text)

        # Get tier routing table
        tier_routes = _TIER_ROUTING.get(tier, _TIER_ROUTING["standard"])
        
        # Get recommended models for this query type
        recommended = tier_routes.get(query_type, tier_routes.get(QueryType.GENERAL, []))
        
        if not recommended:
            # Fallback
            recommended = tier_routes.get(QueryType.GENERAL, [])
        
        # If query is in Persian, try to boost Farsi-capable models
        if language in ("fa", "mixed") and query_type != QueryType.PERSIAN_CULTURAL:
            persian_models = tier_routes.get(QueryType.PERSIAN_CULTURAL, [])
            if persian_models:
                # Interleave: [rec[0], persian[0], rec[1], ...]
                merged = []
                for i in range(max(len(recommended), len(persian_models))):
                    if i < len(recommended):
                        merged.append(recommended[i])
                    if i < len(persian_models) and persian_models[i] not in merged:
                        merged.append(persian_models[i])
                recommended = merged

        # Check performance data if available
        if self._performance_data:
            # Sort by success rate, keeping original order as tiebreaker
            def score_model(mk: Any) -> Any:
                perf = self._performance_data.get(mk, {})
                success = perf.get("success_rate", 0.5)
                speed = perf.get("avg_speed", 0.5)
                return success * 0.7 + speed * 0.3
            
            recommended = sorted(recommended, key=score_model, reverse=True)

        best_model = recommended[0] if recommended else current_model or "g-gemini-flash"
        alternatives = recommended[1:3] if len(recommended) > 1 else []

        reason_parts = [f"نوع: {query_type.value}", f"زبان: {language}", f"تیر: {tier}"]
        if confidence > 0.7:
            reason_parts.append(f"اطمینان بالا ({confidence:.0%})")

        result = RouterResult(
            model_key=best_model,
            query_type=query_type,
            confidence=confidence,
            reason=" | ".join(reason_parts),
            alternatives=alternatives,
        )

        # Track selection
        self._selection_history.append({
            "user_id": user_id,
            "query_type": query_type.value,
            "model": best_model,
            "tier": tier,
            "confidence": confidence,
        })
        # Keep last 1000
        if len(self._selection_history) > 1000:
            self._selection_history = self._selection_history[-500:]

        logger.info(
            "SmartRouter → %s (type=%s, conf=%.2f, tier=%s)",
            best_model, query_type.value, confidence, tier,
        )

        return result

    def update_performance(
        self, model_key: str, success: bool, latency_ms: float = 0,
        quality_score: float = 0.0, query_type: str = "general",
    ) -> None:
        """Update model performance data after a response.
        
        v26.1: Enhanced feedback loop — quality_score and query_type
        feed back into routing decisions for smarter model selection.
        """
        if model_key not in self._performance_data:
            self._performance_data[model_key] = {
                "total_calls": 0,
                "successes": 0,
                "total_latency": 0,
                "success_rate": 0.5,
                "avg_speed": 0.5,
                "avg_quality": 0.5,
                "quality_scores": [],
                "best_query_types": {},
            }
        perf = self._performance_data[model_key]
        perf["total_calls"] += 1
        if success:
            perf["successes"] += 1
        perf["total_latency"] += latency_ms
        perf["success_rate"] = perf["successes"] / perf["total_calls"]
        if perf["total_calls"] > 0 and perf["total_latency"] > 0:
            avg_lat = perf["total_latency"] / perf["total_calls"]
            # Speed score: 0-1, where faster is better (assuming 0-30s range)
            perf["avg_speed"] = max(0, 1 - (avg_lat / 30000))

        # v26.1: Track quality scores for adaptive routing
        if quality_score > 0:
            perf["quality_scores"].append(quality_score)
            if len(perf["quality_scores"]) > 100:
                perf["quality_scores"] = perf["quality_scores"][-100:]
            perf["avg_quality"] = sum(perf["quality_scores"]) / len(perf["quality_scores"])

        # v26.1: Track per-query-type performance
        if query_type not in perf["best_query_types"]:
            perf["best_query_types"][query_type] = {"calls": 0, "quality_sum": 0.0}
        qt_data = perf["best_query_types"][query_type]
        qt_data["calls"] += 1
        qt_data["quality_sum"] += quality_score

    def get_best_model_for_type(self, query_type: str, candidates: list) -> str | None:
        """v26.1: Get historically best model for a query type from candidates."""
        best_model = None
        best_avg = 0.0
        for mk in candidates:
            perf = self._performance_data.get(mk)
            if not perf or query_type not in perf.get("best_query_types", {}):
                continue
            qt_data = perf["best_query_types"][query_type]
            if qt_data["calls"] >= 3:  # Need min 3 calls to judge
                avg = qt_data["quality_sum"] / qt_data["calls"]
                if avg > best_avg:
                    best_avg = avg
                    best_model = mk
        return best_model

    def get_stats(self) -> Dict:
        """Return routing statistics."""
        if not self._selection_history:
            return {"total_selections": 0}
        
        type_counts = {}
        tier_counts = {}
        model_counts = {}
        for s in self._selection_history:
            type_counts[s["query_type"]] = type_counts.get(s["query_type"], 0) + 1
            tier_counts[s["tier"]] = tier_counts.get(s["tier"], 0) + 1
            model_counts[s["model"]] = model_counts.get(s["model"], 0) + 1

        return {
            "total_selections": len(self._selection_history),
            "query_type_distribution": type_counts,
            "tier_distribution": tier_counts,
            "top_models": dict(sorted(model_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "model_performance": {
                k: {"success_rate": round(v["success_rate"], 3), "calls": v["total_calls"]}
                for k, v in self._performance_data.items()
                if v["total_calls"] > 0
            },
        }


# ═══════════════════ SINGLETON ═══════════════════

_smart_router: SmartRouter | None = None

def get_smart_router() -> SmartRouter:
    """Get or create singleton SmartRouter instance."""
    global _smart_router
    if _smart_router is None:
        _smart_router = SmartRouter()
    return _smart_router


