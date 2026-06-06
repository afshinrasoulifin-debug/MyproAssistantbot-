
from __future__ import annotations
"""
tg_bot/utils/hallucination_detector.py — Hallucination Detection v10 (Re-enabled)
═══════════════════════════════════════════════════════════════════════════════════
Detect potentially hallucinated content in AI responses.

v10: Re-enabled with smart thresholds — warns but doesn't block.
     Adds Persian language patterns, contradiction detection,
     confidence scoring, and structured output.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


@dataclass
class HallucinationReport:
    """Structured hallucination analysis result."""
    is_suspicious: bool = False
    score: float = 0.0
    suspicions: List[Dict[str, str]] = field(default_factory=list)
    verdict: str = "clean"
    confidence_adjustment: float = 1.0  # Multiply with response confidence
    suggestion: str = ""


class HallucinationDetector:
    """Detect potential hallucinations in AI-generated text."""

    # Patterns that suggest fabricated information (English + Persian)
    SUSPICION_PATTERNS = [
        # Fabricated citations
        (r"\b(published|founded|established) in (1[89]\d{2}|20[0-2]\d)\b", 0.2, "specific_date",
         "Specific historical date — may be fabricated"),
        (r"\b(study|research|paper) by .{5,40} et al\.?", 0.3, "fake_citation",
         "Academic citation — verify if real"),
        (r"\b(ISBN|DOI|PMID|arXiv)\s*[:.]?\s*[\d\-\.\/]+", 0.4, "fake_id",
         "Identifier reference — often hallucinated"),

        # Fabricated statistics
        (r"\b\d{1,2}\.\d+%\b", 0.15, "precise_stat",
         "Very precise statistic — may be fabricated"),
        (r"\b(exactly|precisely|approximately) \d+", 0.15, "exact_number",
         "Exact number claim — verify"),

        # Fabricated quotes and attributions
        (r'"[^"]{20,}".*(?:said|stated|wrote|noted)', 0.3, "fake_quote",
         "Direct quote attribution — may be fabricated"),
        (r"(?:according to|as reported by|طبق گزارش|به گفته) .{5,50}", 0.2, "attribution",
         "Attribution — verify source"),

        # Persian-specific patterns
        (r"طبق آمار .{5,50}", 0.2, "fa_stat_claim",
         "ادعای آماری — ممکن است ساختگی باشد"),
        (r"تحقیقات .{5,40} نشان می‌دهد", 0.25, "fa_research_claim",
         "ارجاع به تحقیقات — بررسی کنید"),
        (r"در سال \d{4}", 0.1, "fa_year_claim",
         "ذکر سال مشخص"),
    ]

    # Known hallucination indicators
    CONFIDENCE_HEDGES = [
        "I believe", "I think", "probably", "likely", "might",
        "فکر می‌کنم", "احتمالاً", "شاید", "ممکن است",
    ]

    def check(self, text: str, context: str = "") -> HallucinationReport:
        """
        Analyze text for potential hallucinations.

        Returns a report with score and specific suspicions.
        Does NOT block — only flags and adjusts confidence.
        """
        if not text or len(text) < 50:
            return HallucinationReport(verdict="clean")

        report = HallucinationReport()
        total_score = 0.0

        # 1. Pattern-based detection
        for pattern, weight, tag, description in self.SUSPICION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                match_score = min(weight * len(matches), weight * 3)
                total_score += match_score
                report.suspicions.append({
                    "type": tag,
                    "description": description,
                    "matches": len(matches),
                    "score": round(match_score, 2),
                })

        # 2. Contradiction detection
        contradiction_score = self._check_contradictions(
            re.split(r'[.!?؟\n]', text)
        )
        if contradiction_score > 0:
            total_score += contradiction_score
            report.suspicions.append({
                "type": "contradiction",
                "description": "Potential contradictory statements detected",
                "score": round(contradiction_score, 2),
            })

        # 3. Overconfidence detection (too many absolute statements)
        absolute_patterns = [
            r"\b(always|never|definitely|certainly|absolutely)\b",
            r"\b(همیشه|هرگز|قطعاً|حتماً|بدون شک)\b",
        ]
        absolute_count = sum(
            len(re.findall(p, text, re.IGNORECASE))
            for p in absolute_patterns
        )
        if absolute_count > 3:
            over_score = min(absolute_count * 0.05, 0.3)
            total_score += over_score
            report.suspicions.append({
                "type": "overconfidence",
                "description": "Excessive absolute statements",
                "matches": absolute_count,
                "score": round(over_score, 2),
            })

        # 4. Context consistency (if context provided)
        if context:
            context_score = self._check_context_consistency(text, context)
            if context_score > 0:
                total_score += context_score

        # Normalize score (0-1)
        report.score = min(total_score, 1.0)

        # Determine verdict and confidence adjustment
        if report.score < 0.2:
            report.verdict = "clean"
            report.confidence_adjustment = 1.0
        elif report.score < 0.4:
            report.verdict = "low_risk"
            report.confidence_adjustment = 0.9
            report.suggestion = "Response may contain unverified claims. Consider fact-checking."
        elif report.score < 0.7:
            report.verdict = "moderate_risk"
            report.confidence_adjustment = 0.7
            report.suggestion = "Multiple potential hallucination indicators detected. Verify key claims."
            report.is_suspicious = True
        else:
            report.verdict = "high_risk"
            report.confidence_adjustment = 0.5
            report.suggestion = "High hallucination risk. Strongly recommend verification."
            report.is_suspicious = True

        if report.is_suspicious:
            logger.warning(
                "Hallucination detector: score=%.2f verdict=%s suspicions=%d",
                report.score, report.verdict, len(report.suspicions),
            )

        return report

    def _check_contradictions(self, sentences: List[str]) -> float:
        """Check for contradictory statements."""
        score = 0.0
        negation_words = {
            "not", "never", "no", "isn't", "wasn't", "doesn't", "didn't",
            "cannot", "won't", "shouldn't",
            "نه", "نیست", "نبود", "هرگز", "هیچ", "نمی", "ندارد", "نکرد",
        }
        # Filter empty sentences
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        for i, s1 in enumerate(sentences):
            words1 = set(s1.lower().split())
            neg1 = bool(words1 & negation_words)
            for s2 in sentences[i+1:]:
                words2 = set(s2.lower().split())
                neg2 = bool(words2 & negation_words)
                # Significant word overlap but different negation = contradiction
                overlap = len(words1 & words2 - negation_words)
                if overlap > 3 and neg1 != neg2:
                    score += 0.25
        return min(score, 0.5)

    def _check_context_consistency(self, text: str, context: str) -> float:
        """Check if response is consistent with provided context."""
        score = 0.0
        # Simple: check if response introduces entities not in context or query
        # This is a lightweight check — not a full NLI system
        text_words = set(text.lower().split())
        context_words = set(context.lower().split())

        # Check for proper nouns in response not present in context
        proper_noun_pattern = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
        for noun in proper_noun_pattern:
            if noun.lower() not in context_words and noun.lower() not in {
                "the", "this", "that", "however", "therefore", "also",
            }:
                score += 0.05

        return min(score, 0.3)


_detector = None

def get_hallucination_detector() -> HallucinationDetector:
    global _detector
    if _detector is None:
        _detector = HallucinationDetector()
    return _detector


