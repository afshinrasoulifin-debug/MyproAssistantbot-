
from __future__ import annotations
"""Victor v7.0 TITAN — Response Generator (template engine + fusion)"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .models import Memory
from .memory import MemoryStore
from .nlp import PersianNLP

# ═══════════════════════════════════════════════════════════════════
# 5. RESPONSE GENERATOR — Template engine with variables
# ═══════════════════════════════════════════════════════════════════

class ResponseGenerator:
    """
    v7 TITAN: Smart response generation with multi-source fusion,
    confidence calibration, response templates, and follow-up generation.
    """

    # Response quality templates by confidence level
    CONFIDENCE_TEMPLATES = {
        "high": [
            "📚 {answer}",
            "{answer}",
        ],
        "medium": [
            "🤔 بر اساس دانشم:\n{answer}",
            "📖 تا جایی که می‌دونم:\n{answer}",
        ],
        "low": [
            "💭 مطمئن نیستم ولی:\n{answer}\n\n⚠️ ممکنه کامل نباشه.",
            "🔍 اطلاعات محدودی دارم:\n{answer}",
        ],
    }

    # Follow-up question templates
    FOLLOW_UP_TEMPLATES = [
        "آیا می‌خوای بیشتر درباره {topic} بدونی؟",
        "سوال دیگه‌ای درباره {topic} داری؟",
        "می‌خوای {related} رو هم بررسی کنیم؟",
    ]

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory
        self._response_history: List[str] = []  # avoid repetition

    def render(self, template: str, context: Dict[str, Any] = None) -> str:
        """
        Render a response template with variable substitution.
        Variables: {memory_count}, {graph_count}, {context_greeting}, etc.
        """
        if not template:
            return ""

        ctx = context or {}

        # Add default variables
        stats = self.memory.get_stats()
        defaults = {
            "memory_count": str(stats["total_memories"]),
            "graph_count": str(stats["graph_edges"]),
            "rule_count": str(stats["inference_rules"]),
            "interaction_count": str(stats["total_interactions"]),
            "vocab_size": str(stats["vocabulary_size"]),
        }

        # Context-aware greeting
        recent = self.memory.conversation_context[-3:] if self.memory.conversation_context else []
        if recent:
            last_sentiment = recent[-1].get("sentiment", "neutral")
            if last_sentiment == "positive":
                defaults["context_greeting"] = "خوشحالم که حالت خوبه! 😊"
            elif last_sentiment == "negative":
                defaults["context_greeting"] = "اگه مشکلی داری، من اینجام 💪"
            else:
                defaults["context_greeting"] = "چطور می‌تونم کمکت کنم؟"
        else:
            defaults["context_greeting"] = "آماده‌ام!"

        defaults.update(ctx)

        # Substitute variables
        result = template
        for key, value in defaults.items():
            result = result.replace(f"{{{key}}}", str(value))

        return result

    def compose_answer(self, strategies: List[Tuple[str, float]],
                       query: str, context: List[Dict] = None) -> Tuple[str, float]:
        """
        v7 TITAN: Intelligent answer composition from multiple strategies.
        - Deduplicates overlapping info
        - Calibrates confidence
        - Picks complementary pieces
        - Formats cleanly
        """
        if not strategies:
            return "", 0.0

        # Sort by confidence
        strategies.sort(key=lambda x: x[1], reverse=True)

        best_answer, best_conf = strategies[0]

        # If only one strategy or best is high confidence, use it
        if len(strategies) == 1 or best_conf > 85:
            return self._format_by_confidence(best_answer, best_conf, query)

        # Try to merge top strategies if they add different info
        merged_parts = [best_answer]
        merged_conf = best_conf

        for answer, conf in strategies[1:3]:  # Check top 3
            if conf < best_conf * 0.4:
                break  # Too low confidence to merge

            # Check if this adds new information
            similarity = PersianNLP.similarity(best_answer, answer)
            if similarity < 0.5:
                # Different info — merge it
                new_info = self._extract_new_info(answer, best_answer)
                if new_info:
                    merged_parts.append(f"➕ {new_info}")
                    merged_conf = min(95, merged_conf + conf * 0.15)

        final_answer = "\n\n".join(merged_parts)
        return self._format_by_confidence(final_answer, merged_conf, query)

    def generate_follow_up(self, query: str, answer: str,
                           context: List[Dict] = None) -> Optional[str]:
        """Generate a relevant follow-up question."""
        keywords = PersianNLP.extract_keywords(query, max_keywords=3)
        if not keywords:
            return None

        main_topic = keywords[0]

        # Find related topics in knowledge graph
        related = self.memory.get_related(main_topic, max_hops=2)
        if related:
            related_topic = related[0][0]  # First related concept
            return f"\n\n💡 آیا می‌خوای درباره *{related_topic}* هم بدونی؟"

        return None

    def generate_summary(self, memories: List[Memory], query: str = "") -> str:
        """
        Generate an extractive summary from a set of memories.
        v7: Improved with sentence scoring and deduplication.
        """
        if not memories:
            return ""

        # Score sentences by relevance to query
        query_keywords = set(PersianNLP.extract_keywords(query)) if query else set()

        scored_sentences = []
        for mem in memories:
            sentences = re.split(r'[.!?؟\n]+', mem.content)
            for sent in sentences:
                sent = sent.strip()
                if len(sent) < 10:
                    continue
                score = 0.0
                sent_keywords = set(PersianNLP.extract_keywords(sent))
                if query_keywords:
                    overlap = len(sent_keywords & query_keywords)
                    score += overlap * 10
                score += mem.strength * 2
                score += 5  # base score
                # Prefer shorter, more focused sentences
                if 20 < len(sent) < 200:
                    score += 3
                scored_sentences.append((score, sent))

        scored_sentences.sort(key=lambda x: x[0], reverse=True)

        # Pick top sentences (deduped)
        seen = set()
        summary_parts = []
        for _, sent in scored_sentences[:5]:
            sent_norm = PersianNLP.normalize(sent.lower())
            if sent_norm not in seen:
                seen.add(sent_norm)
                summary_parts.append(sent)

        return " ".join(summary_parts)

    def _format_by_confidence(self, answer: str, confidence: float,
                              query: str) -> Tuple[str, float]:
        """Format answer based on confidence level."""
        if confidence >= 70:
            level = "high"
        elif confidence >= 40:
            level = "medium"
        else:
            level = "low"

        templates = self.CONFIDENCE_TEMPLATES[level]
        template = templates[hash(query) % len(templates)]  # Deterministic variety
        formatted = template.format(answer=answer)

        return formatted, confidence

    def _extract_new_info(self, new_answer: str, existing: str) -> str:
        """Extract parts of new_answer not already in existing."""
        existing_keywords = set(PersianNLP.extract_keywords(existing))
        new_lines = new_answer.split("\n")
        unique_lines = []
        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            line_keywords = set(PersianNLP.extract_keywords(line))
            # If less than 50% overlap, it's new info
            if line_keywords and len(line_keywords & existing_keywords) < len(line_keywords) * 0.5:
                unique_lines.append(line)

        return "\n".join(unique_lines[:3])


