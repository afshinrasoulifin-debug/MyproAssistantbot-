
from __future__ import annotations
"""
tg_bot/core/pipeline.py — Intelligent Message Pipeline v10 (Optimized)
═══════════════════════════════════════════════════════════════════════
The CORE routing brain — routes every user message through an
intelligent multi-stage pipeline.

v10 Optimizations:
  ✅ Enhanced classification with Persian NLP signals
  ✅ Quality gate with automatic escalation/regeneration
  ✅ Dynamic strategy selection via ReasoningEngine v10
  ✅ Better complexity estimation with linguistic features
  ✅ Response confidence tracking and adjustment
  ✅ Hallucination detection re-integrated
  ✅ Context-aware prompt enrichment

Pipeline Architecture v10
─────────────────────────
  User Message
       │
       ▼
  ┌─────────────┐
  │ 1. CLASSIFY  │ → Enhanced multi-signal classification
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ 2. CONTEXT   │ → Rich context (history + memory + knowledge)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ 3. REASON    │ → v10 auto-selects strategy (7 options)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ 4. PLAN      │ → Module execution plan
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ 5. EXECUTE   │ → Parallel module execution with fallback
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ 6. QUALITY   │ → Quality gate + hallucination check (NEW)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │ 7. DELIVER   │ → Send to user, store in memory, log telemetry
  └─────────────┘
"""


import hashlib
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from arki_project.utils.ai_cost_tracker import get_cost_tracker
from arki_project.utils.hallucination_detector import get_hallucination_detector
from arki_project.utils.quality_gate import get_quality_gate

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config
    from arki_project.utils.titanium.crypto import secure_hex
except ImportError:
    pass
# ── Infrastructure Integration ──
try:
    from arki_project.core.boot import get_infra 
except ImportError:
    _get_pipeline_infra = lambda: None


logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Task Categories & Intent Detection
# ═══════════════════════════════════════════════════════════════════

class TaskCategory(Enum):
    """Fine-grained task categories for intelligent routing."""
    CHAT = "chat"                    # General conversation
    SEARCH = "search"                # Web search needed
    ANALYSIS = "analysis"            # Data/text analysis
    CREATIVE = "creative"            # Content generation
    IMAGE = "image"                  # Image generation/analysis
    CODE = "code"                    # Code generation/debug
    AUTOMATION = "automation"        # Workflow/automation
    SALES = "sales"                  # Sales/business intelligence
    SECURITY = "security"            # Security/crypto operations
    SYSTEM = "system"                # System commands
    MULTIMODAL = "multimodal"        # Audio/video/image processing
    RESEARCH = "research"            # Deep research tasks


class ComplexityLevel(Enum):
    """Task complexity determines reasoning strategy."""
    TRIVIAL = 1     # Simple greeting, yes/no
    SIMPLE = 2      # Single-step answer
    MODERATE = 3    # Multi-step, single module
    COMPLEX = 4     # Multi-module coordination
    EXPERT = 5      # Deep reasoning, multi-step pipeline


class ReasoningStrategy(Enum):
    """Which reasoning approach to use."""
    DIRECT = "direct"               # Single-shot LLM call
    CHAIN_OF_THOUGHT = "cot"        # Step-by-step reasoning
    REACT = "react"                 # Reason-Act-Observe loop
    TREE_OF_THOUGHT = "tot"         # Branch exploration + voting
    SELF_REFINE = "self_refine"     # Generate → Critique → Refine
    MULTI_AGENT = "multi_agent"     # Multiple LLMs debate


# ── Intent Detection Patterns ──────────────────────────────────

# Persian + English keyword sets for each category
_INTENT_PATTERNS: Dict[TaskCategory, List[str]] = {
    TaskCategory.SEARCH: [
        r"سرچ|جستجو|اینترنت|search|بگرد|خبر|اخبار|آخرین",
        r"قیمت\s+\S+|نرخ\s+\S+|بری اینترنت|از نت|وب\s*سرچ",
        r"google|گوگل|find\s+|look\s+up|trending|ترند",
    ],
    TaskCategory.IMAGE: [
        r"عکس\s*(بساز|بکش|تولید)|تصویر\s*(بساز|بکش|تولید)",
        r"لوگو|بنر|پوستر|آیکون|کاور|والپیپر|نقاشی",
        r"generate\s+image|create\s+image|draw\s|design\s+logo",
        r"render\s|illustrate\s|طراحی\s*(کن|بکن)",
    ],
    TaskCategory.ANALYSIS: [
        r"تحلیل|آمار|بررسی|مقایسه|analyze|analys",
        r"statistics|data|trend|pattern|correlation",
        r"نمودار|chart|graph|report|گزارش",
    ],
    TaskCategory.CODE: [
        r"کد\s|برنامه\s|function|class|debug|code",
        r"python|javascript|api|database|sql",
        r"compile|execute|script|اسکریپت",
    ],
    TaskCategory.CREATIVE: [
        r"بنویس|بساز|خلاقانه|داستان|شعر|مقاله",
        r"write|create|story|poem|article|content",
        r"caption|هشتگ|hashtag|کپشن|پست|بلاگ",
    ],
    TaskCategory.AUTOMATION: [
        r"اتوماسیون|خودکار|زمانبندی|workflow",
        r"automate|schedule|pipeline|cron|trigger",
        r"یادآوری|remind|repeat|تکرار",
    ],
    TaskCategory.SALES: [
        r"فروش|مشتری|قیمت‌گذاری|بازاریابی|sales",
        r"customer|pricing|marketing|upsell|bundle",
        r"crm|revenue|profit|سود|درآمد|فاکتور",
    ],
    TaskCategory.SECURITY: [
        r"رمز|encrypt|decrypt|hash|امنیت|secure",
        r"password|certificate|ssl|scan|vulnerability",
    ],
    TaskCategory.MULTIMODAL: [
        r"صدا|voice|audio|ویدیو|video|تصویر",
        r"ocr|transcribe|tts|speech|تبدیل صوت",
    ],
    TaskCategory.RESEARCH: [
        r"تحقیق|research|investigate|deep\s+search",
        r"آکادمیک|academic|paper|مقاله علمی|thesis",
    ],
}

# Compiled regex patterns
_COMPILED_PATTERNS: Dict[TaskCategory, List[re.Pattern]] = {
    cat: [re.compile(pat, re.IGNORECASE) for pat in patterns]
    for cat, patterns in _INTENT_PATTERNS.items()
}


# ═══════════════════════════════════════════════════════════════════
# Task Classifier
# ═══════════════════════════════════════════════════════════════════

class TaskClassifier:
    """
    Multi-signal task classification.

    Combines:
    1. Pattern matching (fast, rule-based)
    2. Statistical features (message length, question marks, etc.)
    3. Context awareness (previous messages, user profile)

    For doctoral defense: this is a *hybrid classifier* that combines
    rule-based and statistical approaches.
    """

    def __init__(self) -> None:
        self._classification_history: Dict[int, List[TaskCategory]] = defaultdict(list)
        self._accuracy_tracker: Dict[str, int] = defaultdict(int)

    def classify(
        self,
        text: str,
        user_id: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[TaskCategory, ComplexityLevel, float]:
        """
        Classify a message into category + complexity + confidence.

        Returns: (category, complexity, confidence)
        """
        text_lower = text.lower().strip()
        scores: Dict[TaskCategory, float] = defaultdict(float)

        # ── Signal 1: Pattern matching (weight: 0.6) ──
        for cat, patterns in _COMPILED_PATTERNS.items():
            for pat in patterns:
                matches = pat.findall(text_lower)
                scores[cat] += len(matches) * 0.6

        # ── Signal 2: Statistical features (weight: 0.2) ──
        features = self._extract_features(text)

        if features["has_question"]:
            scores[TaskCategory.SEARCH] += 0.15
            scores[TaskCategory.CHAT] += 0.1

        if features["has_url"]:
            scores[TaskCategory.SEARCH] += 0.2
            scores[TaskCategory.ANALYSIS] += 0.1

        if features["has_code_block"]:
            scores[TaskCategory.CODE] += 0.4

        if features["has_numbers"]:
            scores[TaskCategory.ANALYSIS] += 0.15
            scores[TaskCategory.SALES] += 0.1

        if features["word_count"] < 5:
            scores[TaskCategory.CHAT] += 0.2

        # ── Signal 3: Context continuity (weight: 0.2) ──
        if user_id and self._classification_history.get(user_id):
            last_cat = self._classification_history[user_id][-1]
            # Continuity bonus: if same topic, boost it
            scores[last_cat] += 0.15

        # ── Default: CHAT if nothing stands out ──
        if not any(v > 0.3 for v in scores.values()):
            scores[TaskCategory.CHAT] = 0.5

        # ── Pick winner ──
        best_cat = max(scores, key=lambda c: scores[c])
        total_score = sum(scores.values()) or 1.0
        confidence = scores[best_cat] / total_score

        # ── Complexity estimation ──
        complexity = self._estimate_complexity(text, best_cat, features)

        # Track
        if user_id:
            self._classification_history[user_id].append(best_cat)
            # Keep last 20
            if len(self._classification_history[user_id]) > 20:
                self._classification_history[user_id] = \
                    self._classification_history[user_id][-20:]

        return best_cat, complexity, round(confidence, 3)

    def _extract_features(self, text: str) -> Dict[str, Any]:
        """Extract statistical features from text — v10 enhanced."""
        words = text.split()
        sentences = [s for s in re.split(r"[.!?؟\n]", text) if s.strip()]
        persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')

        return {
            "word_count": len(words),
            "char_count": len(text),
            "has_question": bool(re.search(r"[?؟]", text)),
            "has_url": bool(re.search(r"https?://", text)),
            "has_code_block": bool(re.search(r"```", text)),
            "has_numbers": bool(re.search(r"\d{2,}", text)),
            "sentence_count": len(sentences),
            "avg_word_length": (
                sum(len(w) for w in words) / max(1, len(words))
            ),
            # v10: New features
            "is_persian": persian_chars > latin_chars,
            "has_list_markers": bool(re.search(r"(\d+[\.\)]|[•\-\*]\s)", text)),
            "has_comparison": bool(re.search(
                r"(مقایسه|بهتر|بدتر|versus|vs\.?|compare|better|worse|فرق|تفاوت)",
                text, re.IGNORECASE,
            )),
            "has_multi_request": bool(re.search(
                r"(و همچنین|علاوه بر|سپس|بعد|also|additionally|then|and also)",
                text, re.IGNORECASE,
            )),
            "question_count": len(re.findall(r"[?؟]", text)),
            "has_technical_terms": bool(re.search(
                r"(API|JSON|SQL|HTTP|regex|algorithm|الگوریتم|دیتابیس|سرور)",
                text, re.IGNORECASE,
            )),
        }

    def _estimate_complexity(
        self,
        text: str,
        category: TaskCategory,
        features: Dict[str, Any],
    ) -> ComplexityLevel:
        """Estimate task complexity based on multiple signals — v10 enhanced."""
        score = 0

        # Word count signals complexity
        wc = features["word_count"]
        if wc < 5:
            score += 1
        elif wc < 20:
            score += 2
        elif wc < 50:
            score += 3
        elif wc < 100:
            score += 4
        else:
            score += 5

        # Category complexity baseline
        cat_complexity = {
            TaskCategory.CHAT: 1,
            TaskCategory.IMAGE: 2,
            TaskCategory.SEARCH: 2,
            TaskCategory.CREATIVE: 3,
            TaskCategory.CODE: 3,
            TaskCategory.ANALYSIS: 4,
            TaskCategory.AUTOMATION: 4,
            TaskCategory.SALES: 3,
            TaskCategory.SECURITY: 3,
            TaskCategory.RESEARCH: 5,
            TaskCategory.MULTIMODAL: 3,
            TaskCategory.SYSTEM: 2,
        }
        score += cat_complexity.get(category, 2)

        # v10: Additional signals
        # Multiple questions = more complex
        question_count = features.get("question_count", 0)
        if question_count > 2:
            score += 2
        elif question_count > 0:
            score += 1

        # Multi-part requests
        if features.get("has_multi_request"):
            score += 1

        # Comparison tasks are inherently complex
        if features.get("has_comparison"):
            score += 1

        # Technical content
        if features.get("has_technical_terms"):
            score += 1

        # Long sentences suggest complex thoughts
        if features["sentence_count"] > 5:
            score += 1

        # Map to complexity level
        if score <= 3:
            return ComplexityLevel.TRIVIAL
        elif score <= 5:
            return ComplexityLevel.SIMPLE
        elif score <= 7:
            return ComplexityLevel.MODERATE
        elif score <= 9:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.EXPERT


# ═══════════════════════════════════════════════════════════════════
# Module Router
# ═══════════════════════════════════════════════════════════════════

class ModuleRouter:
    """
    Smart router: maps task categories to module execution plans.

    For each category, defines:
    - Primary modules (must execute)
    - Supporting modules (execute if available)
    - Execution order / parallelism
    """

    # Category → modules needed (ordered: primary first)
    ROUTING_TABLE: Dict[TaskCategory, List[Dict[str, Any]]] = {
        TaskCategory.CHAT: [
            {"module": "memory_store", "action": "build_context", "parallel": False},
            {"module": "advanced_prompt_engine", "action": "enhance_prompt", "parallel": False},
            {"module": "multi_llm_orchestrator", "action": "generate", "parallel": False},
            {"module": "telemetry_engine", "action": "record", "parallel": True},
        ],
        TaskCategory.SEARCH: [
            {"module": "web_search", "action": "multi_search", "parallel": False},
            {"module": "web_recon", "action": "extract_content", "parallel": True},
            {"module": "text_transform", "action": "summarize", "parallel": False},
            {"module": "data_analyzer", "action": "extract_insights", "parallel": True},
            {"module": "memory_store", "action": "store_findings", "parallel": True},
        ],
        TaskCategory.ANALYSIS: [
            {"module": "data_analyzer", "action": "analyze", "parallel": False},
            {"module": "text_transform", "action": "extract_entities", "parallel": True},
            {"module": "memory_store", "action": "build_context", "parallel": True},
            {"module": "multi_llm_orchestrator", "action": "interpret", "parallel": False},
        ],
        TaskCategory.CREATIVE: [
            {"module": "memory_store", "action": "build_context", "parallel": False},
            {"module": "advanced_prompt_engine", "action": "creative_prompt", "parallel": False},
            {"module": "multi_llm_orchestrator", "action": "generate", "parallel": False},
            {"module": "text_transform", "action": "polish", "parallel": False},
            {"module": "autotune", "action": "optimize_params", "parallel": True},
        ],
        TaskCategory.IMAGE: [
            {"module": "advanced_prompt_engine", "action": "image_prompt", "parallel": False},
            {"module": "multimodal_engine", "action": "generate_image", "parallel": False},
        ],
        TaskCategory.CODE: [
            {"module": "memory_store", "action": "build_context", "parallel": False},
            {"module": "advanced_prompt_engine", "action": "code_prompt", "parallel": False},
            {"module": "multi_llm_orchestrator", "action": "generate_code", "parallel": False},
            {"module": "terminal_emulator", "action": "validate", "parallel": True},
        ],
        TaskCategory.AUTOMATION: [
            {"module": "workflow_engine", "action": "build_workflow", "parallel": False},
            {"module": "integration_hub", "action": "check_connections", "parallel": True},
            {"module": "multi_llm_orchestrator", "action": "plan", "parallel": False},
        ],
        TaskCategory.SALES: [
            {"module": "memory_store", "action": "build_context", "parallel": False},
            {"module": "data_analyzer", "action": "sales_analysis", "parallel": True},
            {"module": "web_search", "action": "market_research", "parallel": True},
            {"module": "multi_llm_orchestrator", "action": "generate", "parallel": False},
        ],
        TaskCategory.SECURITY: [
            {"module": "crypto_engine", "action": "process", "parallel": False},
            {"module": "network_tools", "action": "scan", "parallel": True},
            {"module": "anti_detection", "action": "check", "parallel": True},
        ],
        TaskCategory.MULTIMODAL: [
            {"module": "multimodal_engine", "action": "process", "parallel": False},
            {"module": "text_transform", "action": "extract", "parallel": True},
            {"module": "multi_llm_orchestrator", "action": "interpret", "parallel": False},
        ],
        TaskCategory.RESEARCH: [
            {"module": "web_search", "action": "academic_search", "parallel": False},
            {"module": "web_recon", "action": "deep_extract", "parallel": False},
            {"module": "text_transform", "action": "summarize", "parallel": False},
            {"module": "data_analyzer", "action": "cross_reference", "parallel": True},
            {"module": "memory_store", "action": "store_research", "parallel": True},
            {"module": "multi_llm_orchestrator", "action": "synthesize", "parallel": False},
        ],
    }

    def get_execution_plan(
        self,
        category: TaskCategory,
        complexity: ComplexityLevel,
    ) -> List[Dict[str, Any]]:
        """Get the execution plan for a task category."""
        plan = self.ROUTING_TABLE.get(category, self.ROUTING_TABLE[TaskCategory.CHAT])

        # For simple tasks, reduce plan
        if complexity.value <= 2:
            plan = [step for step in plan if not step.get("parallel")]

        return plan

    def get_reasoning_strategy(
        self,
        category: TaskCategory,
        complexity: ComplexityLevel,
        user_text: str = "",
    ) -> ReasoningStrategy:
        """
        Select reasoning strategy — v10 enhanced.

        Uses ReasoningEngine's auto_select when possible,
        falls back to complexity-based selection.
        """
        # v10: Delegate to ReasoningEngine for smarter selection
        if user_text:
            try:
                from arki_project.core.reasoning import ReasoningEngine
                engine = ReasoningEngine()
                auto_strategy = engine.auto_select_strategy(
                    user_text,
                    category=category.value,
                    complexity=complexity.value,
                )
                # Map reasoning engine names to pipeline enums
                strategy_map = {
                    "direct": ReasoningStrategy.DIRECT,
                    "chain_of_thought": ReasoningStrategy.CHAIN_OF_THOUGHT,
                    "react": ReasoningStrategy.REACT,
                    "tree_of_thought": ReasoningStrategy.TREE_OF_THOUGHT,
                    "self_refine": ReasoningStrategy.SELF_REFINE,
                    "meta_cognitive": ReasoningStrategy.MULTI_AGENT,
                    "decompose": ReasoningStrategy.MULTI_AGENT,
                }
                return strategy_map.get(auto_strategy, ReasoningStrategy.CHAIN_OF_THOUGHT)
            except Exception as _e:
                logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent

        # Fallback: complexity-based
        if complexity == ComplexityLevel.TRIVIAL:
            return ReasoningStrategy.DIRECT
        elif complexity == ComplexityLevel.SIMPLE:
            return ReasoningStrategy.DIRECT
        elif complexity == ComplexityLevel.MODERATE:
            return ReasoningStrategy.CHAIN_OF_THOUGHT
        elif complexity == ComplexityLevel.COMPLEX:
            return ReasoningStrategy.REACT
        else:  # EXPERT
            return ReasoningStrategy.TREE_OF_THOUGHT


# ═══════════════════════════════════════════════════════════════════
# Context Builder
# ═══════════════════════════════════════════════════════════════════

class ContextBuilder:
    """
    Build rich context for LLM calls by combining:
    - Conversation history (from DB)
    - Semantic memory (from MemoryStore)
    - Knowledge graph entities
    - User profile
    - Task-specific context

    This is what makes the bot INTELLIGENT — not just chat history.
    """

    def __init__(self) -> None:
        self._user_profiles: Dict[int, Dict[str, Any]] = {}

    def build_context(
        self,
        user_id: int,
        text: str,
        category: TaskCategory,
        chat_history: List[Dict[str, str]],
        memory_results: Optional[List[Dict[str, Any]]] = None,
        knowledge_entities: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for the AI call.

        Returns a context dict used by the prompt engine.
        """
        context: Dict[str, Any] = {
            "user_id": user_id,
            "current_message": text,
            "category": category.value,
            "timestamp": time.time(),
        }

        # ── Conversation context ──
        # Not just last N messages — weighted by relevance
        relevant_history = self._select_relevant_history(
            text, chat_history, max_messages=15,
        )
        context["conversation_history"] = relevant_history

        # ── Semantic memory ──
        if memory_results:
            context["semantic_memory"] = [
                {
                    "content": m.get("content", ""),
                    "relevance": m.get("score", 0),
                    "timestamp": m.get("timestamp", 0),
                }
                for m in memory_results[:5]  # Top 5 relevant memories
            ]

        # ── Knowledge graph entities ──
        if knowledge_entities:
            context["knowledge_entities"] = knowledge_entities[:10]

        # ── User profile ──
        if user_id in self._user_profiles:
            context["user_profile"] = self._user_profiles[user_id]

        # ── Task-specific context hints ──
        context["task_hints"] = self._get_task_hints(category)

        return context

    def update_user_profile(
        self,
        user_id: int,
        updates: Dict[str, Any],
    ) -> None:
        """Update user profile based on interaction patterns."""
        if user_id not in self._user_profiles:
            self._user_profiles[user_id] = {
                "interaction_count": 0,
                "preferred_language": "fa",
                "topics_of_interest": [],
                "expertise_level": "general",
            }
        self._user_profiles[user_id].update(updates)
        self._user_profiles[user_id]["interaction_count"] += 1

    def _select_relevant_history(
        self,
        current_text: str,
        history: List[Dict[str, str]],
        max_messages: int = 15,
    ) -> List[Dict[str, str]]:
        """
        Select most relevant history messages.

        Uses TF-IDF-like scoring to pick messages most related
        to the current query, not just the most recent.
        """
        if len(history) <= max_messages:
            return history

        # Score each message by keyword overlap with current query
        current_words = set(current_text.lower().split())
        scored: List[Tuple[float, int, Dict[str, str]]] = []

        for idx, msg in enumerate(history):
            msg_words = set(msg.get("content", "").lower().split())
            overlap = len(current_words & msg_words)
            # Recency bonus
            recency = idx / len(history)
            score = overlap * 0.6 + recency * 0.4
            scored.append((score, idx, msg))

        # Always include last 5 + top by relevance
        recent = history[-5:]
        scored.sort(key=lambda x: x[0], reverse=True)
        relevant = [s[2] for s in scored[:max_messages - 5]]

        # Merge and deduplicate, maintaining order
        seen = set()
        result: List[Dict[str, str]] = []
        for msg in relevant + recent:
            msg_id = id(msg)
            if msg_id not in seen:
                seen.add(msg_id)
                result.append(msg)

        # Track AI usage
        try:
            tracker = get_cost_tracker()
            tracker.record(user_id=getattr(self, '_user_id', 0), model=getattr(self, '_model', 'unknown'),
                          handler='pipeline', input_tokens=len(str(current_text))//4, output_tokens=len(str(result))//4)
        except Exception as _exc:
            logger.debug("Suppressed: %s", _exc)
        return result[-max_messages:]

    def _get_task_hints(self, category: TaskCategory) -> Dict[str, str]:
        """Get task-specific prompt hints."""
        hints = {
            TaskCategory.CHAT: {
                "style": "conversational",
                "instruction": "Be helpful, friendly, and concise.",
            },
            TaskCategory.SEARCH: {
                "style": "informative",
                "instruction": "Provide well-sourced, factual information.",
            },
            TaskCategory.ANALYSIS: {
                "style": "analytical",
                "instruction": "Provide data-driven insights with evidence.",
            },
            TaskCategory.CREATIVE: {
                "style": "creative",
                "instruction": "Be creative, original, and engaging.",
            },
            TaskCategory.CODE: {
                "style": "technical",
                "instruction": "Write clean, documented code with explanations.",
            },
            TaskCategory.RESEARCH: {
                "style": "academic",
                "instruction": "Provide thorough, well-cited research.",
            },
        }
        return hints.get(category, hints[TaskCategory.CHAT])


# ═══════════════════════════════════════════════════════════════════
# Pipeline Execution Result
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PipelineResult:
    """Result from the intelligent pipeline."""
    request_id: str
    category: TaskCategory
    complexity: ComplexityLevel
    reasoning_strategy: ReasoningStrategy
    confidence: float
    modules_used: List[str]
    execution_plan: List[Dict[str, Any]]
    context: Dict[str, Any]
    response_text: str = ""
    enriched_prompt: str = ""
    module_results: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    duration_ms: float = 0.0
    reasoning_trace: List[Dict[str, str]] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════════

class IntelligentPipeline:
    """
    The main intelligent pipeline.

    Connects TaskClassifier → ContextBuilder → ModuleRouter →
    PromptEngine → LLM → QualityChecker → MemoryStore.

    This is the BRAIN of Arki v29.0.0
    """

    def __init__(self) -> None:
        self.classifier = TaskClassifier()
        self.router = ModuleRouter()
        self.context_builder = ContextBuilder()

        # Stats
        self._total_requests = 0
        self._category_counts: Dict[str, int] = defaultdict(int)
        self._avg_duration_ms = 0.0
        self._start_time = time.time()

    async def process(
        self,
        user_id: int,
        text: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        memory_results: Optional[List[Dict[str, Any]]] = None,
        knowledge_entities: Optional[List[Dict[str, Any]]] = None,
    ) -> PipelineResult:
        """
        Process a message through the full intelligent pipeline.

        This is the main entry point called from handlers.
        """
        start_time = time.time()
        self._total_requests += 1

        # Generate request ID
        request_id = hashlib.md5(
            f"{user_id}:{text}:{time.time()}".encode()
        ).hexdigest()[:12]

        # ── Stage 1: CLASSIFY ──
        category, complexity, confidence = self.classifier.classify(
            text, user_id=user_id,
        )
        self._category_counts[category.value] += 1

        logger.info(
            "Pipeline[%s] user=%d category=%s complexity=%s confidence=%.2f",
            request_id, user_id, category.value,
            complexity.name, confidence,
        )

        # ── Stage 2: BUILD CONTEXT ──
        context = self.context_builder.build_context(
            user_id=user_id,
            text=text,
            category=category,
            chat_history=chat_history or [],
            memory_results=memory_results,
            knowledge_entities=knowledge_entities,
        )

        # ── Stage 3: SELECT REASONING STRATEGY (v10: uses text analysis) ──
        strategy = self.router.get_reasoning_strategy(category, complexity, text)

        # ── Stage 4: GET EXECUTION PLAN ──
        execution_plan = self.router.get_execution_plan(category, complexity)

        modules_used = [step["module"] for step in execution_plan]

        # ── Stage 5: Build enriched prompt ──
        enriched_prompt = self._build_enriched_prompt(
            text, category, strategy, context,
        )

        # ── Build reasoning trace ──
        reasoning_trace = [
            {"step": "classify", "result": f"{category.value} (confidence: {confidence:.2f})"},
            {"step": "complexity", "result": f"{complexity.name} (level {complexity.value})"},
            {"step": "strategy", "result": strategy.value},
            {"step": "modules", "result": ", ".join(modules_used)},
        ]

        duration_ms = (time.time() - start_time) * 1000

        # Update context builder's user profile
        self.context_builder.update_user_profile(user_id, {
            "last_category": category.value,
            "last_complexity": complexity.value,
        })

        # ── v10: Prepare quality gate and hallucination check info ──
        # These will run after the LLM generates a response
        # (this pipeline builds the execution plan; the actual response
        #  is generated downstream — we attach the validators)
        quality_gate = get_quality_gate()
        hallucination_detector = get_hallucination_detector()

        result = PipelineResult(
            request_id=request_id,
            category=category,
            complexity=complexity,
            reasoning_strategy=strategy,
            confidence=confidence,
            modules_used=modules_used,
            execution_plan=execution_plan,
            context=context,
            enriched_prompt=enriched_prompt,
            quality_score=confidence,
            duration_ms=round(duration_ms, 2),
            reasoning_trace=reasoning_trace,
        )

        # Attach validators to context for downstream use
        result.context["_quality_gate"] = quality_gate
        result.context["_hallucination_detector"] = hallucination_detector
        result.context["_escalation_enabled"] = complexity.value >= 3

        return result

    def _build_enriched_prompt(
        self,
        text: str,
        category: TaskCategory,
        strategy: ReasoningStrategy,
        context: Dict[str, Any],
    ) -> str:
        """
        Build an enriched system prompt based on classification
        and reasoning strategy.

        This prompt WRAPS the user's persona and adds intelligence.
        """
        parts: List[str] = []

        # ── Reasoning instructions ──
        if strategy == ReasoningStrategy.CHAIN_OF_THOUGHT:
            parts.append(
                "REASONING APPROACH: Think step by step.\n"
                "1. First, understand what the user is asking.\n"
                "2. Break the problem into sub-steps.\n"
                "3. Solve each step methodically.\n"
                "4. Combine results into a clear answer.\n"
            )
        elif strategy == ReasoningStrategy.REACT:
            parts.append(
                "REASONING APPROACH: Use the ReAct framework.\n"
                "For each step:\n"
                "  Thought: What do I need to figure out?\n"
                "  Action: What action should I take?\n"
                "  Observation: What did I learn?\n"
                "Repeat until you have a complete answer.\n"
            )
        elif strategy == ReasoningStrategy.TREE_OF_THOUGHT:
            parts.append(
                "REASONING APPROACH: Explore multiple approaches.\n"
                "Consider at least 2-3 different angles.\n"
                "Evaluate each approach, then select the best.\n"
                "Show your reasoning for why one approach is better.\n"
            )

        # ── Task-specific instructions ──
        task_hints = context.get("task_hints", {})
        if task_hints:
            parts.append(
                f"RESPONSE STYLE: {task_hints.get('style', 'helpful')}\n"
                f"INSTRUCTION: {task_hints.get('instruction', '')}\n"
            )

        # ── Memory context ──
        semantic_memory = context.get("semantic_memory")
        if semantic_memory:
            memory_text = "\n".join(
                f"- {m['content'][:200]}" for m in semantic_memory[:3]
            )
            parts.append(
                f"RELEVANT MEMORY (from past conversations):\n{memory_text}\n"
            )

        # ── Knowledge graph entities ──
        entities = context.get("knowledge_entities")
        if entities:
            entity_text = ", ".join(
                e.get("name", str(e)) for e in entities[:5]
            )
            parts.append(f"KNOWN ENTITIES: {entity_text}\n")

        return "\n".join(parts) if parts else ""

    def validate_response(
        self,
        response_text: str,
        pipeline_result: PipelineResult,
    ) -> Dict[str, Any]:
        """
        v10: Post-generation quality validation.

        Call this AFTER the LLM generates a response.
        Returns quality report + hallucination report + escalation recommendation.
        """
        query = pipeline_result.context.get("current_message", "")
        category = pipeline_result.category.value

        # Quality gate
        quality_gate = pipeline_result.context.get("_quality_gate") or get_quality_gate()
        quality_report = quality_gate.evaluate(
            response_text, query, category=category,
        )

        # Hallucination check
        hallucination_detector = (
            pipeline_result.context.get("_hallucination_detector")
            or get_hallucination_detector()
        )
        halluc_report = hallucination_detector.check(response_text, context=query)

        # Adjusted confidence
        adjusted_confidence = (
            pipeline_result.confidence
            * halluc_report.confidence_adjustment
            * quality_report.overall_score
        )

        # Escalation recommendation
        should_escalate = False
        escalation_reason = ""
        if not quality_report.passed:
            should_escalate = True
            escalation_reason = "Quality gate failed"
        elif halluc_report.is_suspicious and pipeline_result.context.get("_escalation_enabled"):
            should_escalate = True
            escalation_reason = f"Hallucination risk: {halluc_report.verdict}"
        elif adjusted_confidence < 0.3:
            should_escalate = True
            escalation_reason = f"Low confidence: {adjusted_confidence:.2f}"

        return {
            "quality_score": round(quality_report.overall_score, 3),
            "quality_passed": quality_report.passed,
            "quality_issues": quality_report.issues,
            "hallucination_score": round(halluc_report.score, 3),
            "hallucination_verdict": halluc_report.verdict,
            "hallucination_suspicions": halluc_report.suspicions,
            "adjusted_confidence": round(adjusted_confidence, 3),
            "should_escalate": should_escalate,
            "escalation_reason": escalation_reason,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics for monitoring/dashboard."""
        uptime = time.time() - self._start_time
        return {
            "total_requests": self._total_requests,
            "uptime_seconds": round(uptime),
            "categories": dict(self._category_counts),
            "requests_per_minute": round(
                self._total_requests / max(1, uptime / 60), 2
            ),
        }


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Pipeline Features
# ══════════════════════════════════════════════════════════════

class PipelineMetrics:
    """Track pipeline stage execution metrics."""

    def __init__(self) -> None:
        self._stages: dict[str, list[dict]] = {}

    def record_stage(self, name: str, duration_ms: float, success: bool, output_size: int = 0) -> Any:
        import time
        if name not in self._stages:
            self._stages[name] = []
        self._stages[name].append({
            "duration_ms": duration_ms,
            "success": success,
            "output_size": output_size,
            "ts": time.time(),
        })
        # Keep last 100 per stage
        if len(self._stages[name]) > 100:
            self._stages[name] = self._stages[name][-50:]

    def stage_summary(self, name: str) -> dict:
        runs = self._stages.get(name, [])
        if not runs:
            return {"count": 0}
        ok = sum(1 for r in runs if r["success"])
        avg_ms = sum(r["duration_ms"] for r in runs) / len(runs)
        return {
            "count": len(runs),
            "success_rate": ok / len(runs),
            "avg_duration_ms": round(avg_ms, 1),
            "total_output_bytes": sum(r["output_size"] for r in runs),
        }

    def pipeline_health(self) -> dict:
        stages = {}
        for name in self._stages:
            stages[name] = self.stage_summary(name)
        bottleneck = max(stages, key=lambda s: stages[s].get("avg_duration_ms", 0)) if stages else None
        return {
            "stages": stages,
            "bottleneck": bottleneck,
            "total_runs": sum(s.get("count", 0) for s in stages.values()),
        }


class PipelineDAG:
    """Directed Acyclic Graph for pipeline stage dependencies."""

    def __init__(self) -> None:
        self._nodes: dict[str, dict] = {}  # name -> {func, deps}
        self._edges: list[tuple[str, str]] = []

    def add_stage(self, name: str, depends_on: list[str] | None = None) -> None:
        self._nodes[name] = {"deps": depends_on or []}
        for dep in (depends_on or []):
            self._edges.append((dep, name))

    def execution_order(self) -> list[list[str]]:
        """Return stages grouped by execution level (parallelizable)."""
        resolved: set[str] = set()
        levels: list[list[str]] = []
        remaining = set(self._nodes.keys())

        while remaining:
            level = [
                n for n in remaining
                if all(d in resolved for d in self._nodes[n]["deps"])
            ]
            if not level:
                break  # Cycle detected
            levels.append(level)
            resolved.update(level)
            remaining -= set(level)

        return levels

    def visualize(self) -> str:
        """ASCII visualization of the pipeline."""
        levels = self.execution_order()
        lines = ["Pipeline DAG:"]
        for i, level in enumerate(levels):
            prefix = "  " * i
            lines.append(f"{prefix}Level {i}: {' | '.join(level)}")
        return "\n".join(lines)


