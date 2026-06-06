
from __future__ import annotations
"""
tg_bot/utils/quality_gate.py — Response Quality Gate v10
═══════════════════════════════════════════════════════════
Validates and scores AI responses before delivery to users.

Quality dimensions:
  1. Completeness — Does it fully address the query?
  2. Coherence — Is it internally consistent and well-structured?
  3. Relevance — Does it stay on topic?
  4. Language quality — Grammar, formatting, readability
  5. Safety — No harmful content
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Quality assessment of an AI response."""
    overall_score: float = 0.0  # 0-1
    completeness: float = 0.0
    coherence: float = 0.0
    relevance: float = 0.0
    language_quality: float = 0.0
    passed: bool = True
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class QualityGate:
    """
    Validate AI responses before delivery.

    Lightweight checks that run fast (no LLM calls).
    Serious issues flag for escalation/regeneration.
    """

    # Minimum acceptable score to pass
    MIN_SCORE = 0.35

    def evaluate(
        self,
        response: str,
        query: str,
        category: str = "chat",
        language: str = "auto",
    ) -> QualityReport:
        """Evaluate response quality across all dimensions."""
        report = QualityReport()

        if not response or not response.strip():
            report.overall_score = 0.0
            report.passed = False
            report.issues.append("Empty response")
            return report

        # Auto-detect language
        if language == "auto":
            language = "fa" if _is_persian(query) else "en"

        # Evaluate each dimension
        report.completeness = self._check_completeness(response, query, category)
        report.coherence = self._check_coherence(response)
        report.relevance = self._check_relevance(response, query)
        report.language_quality = self._check_language(response, language)

        # Weighted overall score
        weights = {
            "completeness": 0.30,
            "coherence": 0.25,
            "relevance": 0.30,
            "language_quality": 0.15,
        }
        report.overall_score = (
            report.completeness * weights["completeness"]
            + report.coherence * weights["coherence"]
            + report.relevance * weights["relevance"]
            + report.language_quality * weights["language_quality"]
        )

        report.passed = report.overall_score >= self.MIN_SCORE

        if not report.passed:
            logger.warning(
                "Quality gate FAILED: score=%.2f (completeness=%.2f coherence=%.2f "
                "relevance=%.2f language=%.2f)",
                report.overall_score, report.completeness, report.coherence,
                report.relevance, report.language_quality,
            )

        return report

    def _check_completeness(self, response: str, query: str, category: str) -> float:
        """Check if the response adequately addresses the query."""
        score = 0.5  # baseline

        # Length-based heuristic (relative to query complexity)
        query_words = len(query.split())
        response_words = len(response.split())

        if query_words > 20 and response_words < 30:
            score -= 0.2  # Complex query, short response
        elif response_words > query_words * 0.5:
            score += 0.2

        # Check if response contains query keywords
        query_keywords = _extract_keywords(query)
        response_lower = response.lower()
        keyword_coverage = sum(1 for kw in query_keywords if kw in response_lower)
        if query_keywords:
            coverage_ratio = keyword_coverage / len(query_keywords)
            score += coverage_ratio * 0.3

        # Category-specific completeness
        if category == "code":
            if "```" in response or re.search(r"def |class |function |import ", response):
                score += 0.15
            else:
                score -= 0.1
        elif category == "analysis":
            # Should have some structure
            if any(marker in response for marker in ["1.", "•", "-", "نتیجه", "conclusion"]):
                score += 0.1

        return max(0.0, min(1.0, score))

    def _check_coherence(self, response: str) -> float:
        """Check internal consistency, flow, and structure quality."""
        score = 0.75  # v26.1: higher baseline — deduct for real problems

        # Split into meaningful segments (not headers or short fragments)
        raw_segments = [s.strip() for s in re.split(r'[.!?؟\n]', response) if len(s.strip()) > 5]
        # Filter out markdown headers and list markers (they aren't "sentences")
        sentences = [s for s in raw_segments if not re.match(r'^#{1,4}\s|^[\-\*•]\s|^\d+[\.\)]\s', s)]

        if len(sentences) < 2:
            return 0.80  # Short but coherent by default

        # Check for abrupt topic changes (vocabulary overlap between consecutive sentences)
        prev_words = set()
        topic_shifts = 0
        for sent in sentences:
            current_words = set(re.findall(r'\w{3,}', sent.lower()))
            if prev_words and current_words:
                overlap = len(prev_words & current_words)
                # Only count as shift if zero overlap AND both sentences are substantial
                if overlap == 0 and len(current_words) > 4 and len(prev_words) > 4:
                    topic_shifts += 1
            prev_words = current_words

        shift_ratio = topic_shifts / max(len(sentences) - 1, 1)
        if shift_ratio > 0.5:
            score -= 0.20
        elif shift_ratio > 0.3:
            score -= 0.10

        # Check for repetition
        sent_set = set()
        repetitions = 0
        for sent in sentences:
            normalized = sent.strip().lower()
            if normalized in sent_set:
                repetitions += 1
            sent_set.add(normalized)

        if repetitions > 0:
            score -= repetitions * 0.12
            score = max(score, 0.2)

        # Reward proper structure (headers, lists, numbered points)
        has_headers = bool(re.search(r'#{1,3}\s', response))
        has_lists = bool(re.search(r'(\d+[\.\)]|[•\-\*]\s)', response))
        has_sequence = bool(re.search(r'(firstly|secondly|thirdly|اول|دوم|سوم|ابتدا|سپس|در نهایت)', response, re.IGNORECASE))
        
        structure_bonus = 0
        if has_headers: structure_bonus += 0.05
        if has_lists: structure_bonus += 0.05
        if has_sequence: structure_bonus += 0.05
        if len(sentences) > 5 and structure_bonus > 0:
            score += min(structure_bonus, 0.15)

        # Penalize incomplete/cut-off responses
        last_segment = raw_segments[-1] if raw_segments else ""
        if last_segment and not re.search(r'[.!?؟:»"\)\]]$', last_segment.strip()):
            score -= 0.05

        return max(0.0, min(1.0, score))

    def _check_relevance(self, response: str, query: str) -> float:
        """Check if the response stays on topic."""
        score = 0.5  # baseline

        query_keywords = _extract_keywords(query)
        response_keywords = _extract_keywords(response)

        if not query_keywords:
            return 0.7  # Can't assess

        # Keyword overlap ratio
        overlap = len(query_keywords & response_keywords)
        relevance_ratio = overlap / len(query_keywords) if query_keywords else 0
        score += relevance_ratio * 0.4

        # Check if response starts with something related to the query
        first_100 = response[:100].lower()
        if any(kw in first_100 for kw in query_keywords):
            score += 0.1

        return max(0.0, min(1.0, score))

    def _check_language(self, response: str, language: str) -> float:
        """Check language quality and formatting."""
        score = 0.7  # baseline

        # Check for formatting issues
        if response.count("```") % 2 != 0:
            score -= 0.1  # Unclosed code block

        # Check for excessive repetition of words
        words = response.lower().split()
        if words:
            word_freq = {}
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1
            max_freq = max(word_freq.values())
            if max_freq > len(words) * 0.15 and max_freq > 5:
                score -= 0.15

        # Check for broken markdown
        if response.count("**") % 2 != 0 or response.count("*") % 2 != 0:
            score -= 0.05

        # Language-specific checks
        if language == "fa":
            # Check for mixed direction issues (too much Latin in Persian response)
            persian_ratio = sum(1 for c in response if '\u0600' <= c <= '\u06FF') / max(1, len(response))
            if persian_ratio < 0.3:
                score -= 0.1  # Response might be in wrong language

        return max(0.0, min(1.0, score))

    # ═══════════════════ v26.0: DEEP QUALITY SCORING ═══════════════════

    def deep_evaluate(
        self,
        response: str,
        query: str,
        category: str = "chat",
        language: str = "auto",
        tier: str = "standard",
    ) -> QualityReport:
        """
        Deep quality evaluation with tier-aware scoring.

        Enhanced checks:
          - Hallucination risk (based on hedging language vs assertions)
          - Completeness depth (query decomposition)
          - Structural quality (formatting, sections)
          - Factual consistency (internal contradictions)
          - Response-to-query alignment
        """
        report = self.evaluate(response, query, category, language)

        if not response or not response.strip():
            return report

        # Deep checks
        hallu_score = self._deep_hallucination_check(response, query)
        completeness_depth = self._deep_completeness_check(response, query)
        structure_score = self._deep_structure_check(response, tier)
        consistency_score = self._deep_consistency_check(response)

        # Weighted deep score
        deep_score = (
            hallu_score * 0.25 +
            completeness_depth * 0.30 +
            structure_score * 0.20 +
            consistency_score * 0.25
        )

        # Combine with original score
        report.overall_score = report.overall_score * 0.4 + deep_score * 0.6

        # Tier-specific minimum thresholds
        tier_min = {
            "fast": 0.25, "standard": 0.35, "smart": 0.45,
            "pro": 0.50, "power": 0.55, "ultra": 0.60,
        }
        report.passed = report.overall_score >= tier_min.get(tier, 0.35)

        if not report.passed:
            report.suggestions.append(
                f"Quality {report.overall_score:.2f} below {tier} threshold "
                f"{tier_min.get(tier, 0.35)}. Consider retry."
            )

        return report

    def _deep_hallucination_check(self, response: str, query: str) -> float:
        """
        Check for hallucination risk indicators.

        High confidence language + unverifiable claims = higher risk.
        Hedging language + qualified statements = lower risk.
        """
        response_lower = response.lower()
        
        # Hedging (good — shows calibrated confidence)
        hedge_patterns = [
            "شاید", "احتمالاً", "ممکن است", "به نظر می‌رسد",
            "maybe", "perhaps", "likely", "possibly", "it seems",
            "I think", "I believe", "based on", "according to",
            "generally", "typically", "often", "usually",
        ]
        hedge_count = sum(1 for p in hedge_patterns if p.lower() in response_lower)

        # Overconfident assertions (risky)
        assertion_patterns = [
            "قطعاً", "حتماً", "بدون شک", "100%", "همیشه", "هرگز",
            "definitely", "absolutely", "always", "never", "certainly",
            "guaranteed", "proven fact", "undoubtedly",
        ]
        assertion_count = sum(1 for p in assertion_patterns if p.lower() in response_lower)

        # Made-up statistics (risky)
        import re
        fake_stats = len(re.findall(r'\d{2,3}%|\d+\.\d+ (million|billion|percent)', response_lower))

        # Score: 1.0 = no hallucination risk, 0.0 = high risk
        risk = 0.0
        risk += assertion_count * 0.15
        risk += fake_stats * 0.2
        risk -= hedge_count * 0.1  # Hedging reduces risk

        return max(0.0, min(1.0, 1.0 - risk))

    def _deep_completeness_check(self, response: str, query: str) -> float:
        """Check if response addresses all parts of the query."""
        import re
        
        # Decompose query into sub-questions
        # Split on: question marks, "and also", numbered items, semicolons
        query_parts = re.split(r'[?؟;]|\bو\s+همچنین\b|\bعلاوه\s+بر\b|\d+[.)\-]', query)
        query_parts = [p.strip() for p in query_parts if len(p.strip()) > 5]

        if not query_parts:
            return 0.7  # Simple query, likely complete

        response_lower = response.lower()
        addressed = 0
        for part in query_parts:
            # Check if key words from this part appear in response
            part_words = set(part.lower().split()) - {
                "و", "از", "به", "در", "که", "را", "با", "این",
                "the", "a", "is", "are", "to", "for", "of", "with",
            }
            if part_words:
                matches = sum(1 for w in part_words if w in response_lower)
                if matches / len(part_words) > 0.3:
                    addressed += 1

        return addressed / max(1, len(query_parts))

    def _deep_structure_check(self, response: str, tier: str) -> float:
        """Check response structure quality relative to tier expectations."""
        score = 0.5

        has_paragraphs = "\n\n" in response
        has_headers = any(h in response for h in ["##", "**", "###"])
        has_list = any(m in response for m in ["\n- ", "\n• ", "\n* ", "\n1.", "\n2."])
        has_code = "```" in response
        word_count = len(response.split())

        # Fast: penalize over-structuring short responses
        if tier == "fast":
            if word_count < 100 and not has_headers:
                score += 0.3  # Simple is good for fast
            if has_paragraphs:
                score += 0.1
            return min(1.0, score)

        # Standard+: reward good structure
        if has_paragraphs:
            score += 0.15
        if has_headers and word_count > 100:
            score += 0.15
        if has_list:
            score += 0.1

        # Pro/Ultra: expect rich structure for long responses
        if tier in ("pro", "power", "ultra") and word_count > 200:
            if has_headers:
                score += 0.1
            if has_list or has_code:
                score += 0.1

        return min(1.0, score)

    def _deep_consistency_check(self, response: str) -> float:
        """Check for internal contradictions in the response."""
        import re
        
        sentences = [s.strip() for s in re.split(r'[.!؟?\n]', response) if len(s.strip()) > 15]
        
        if len(sentences) < 2:
            return 0.8  # Too short to have contradictions

        # Simple contradiction detection: look for negation patterns
        contradiction_signals = 0
        for i, s1 in enumerate(sentences[:-1]):
            s1_lower = s1.lower()
            for s2 in sentences[i+1:]:
                s2_lower = s2.lower()
                # Check if one sentence negates a claim in another
                if any(neg in s2_lower for neg in ["نیست", "نمی", "نه ", "هرگز", "isn't", "doesn't", "never", "not "]):
                    # Check if they're about the same topic (shared words)
                    s1_words = set(s1_lower.split())
                    s2_words = set(s2_lower.split())
                    overlap = len(s1_words & s2_words)
                    if overlap > 3:  # Significant overlap + negation = potential contradiction
                        contradiction_signals += 1

        # Score: fewer contradictions = higher score
        if contradiction_signals == 0:
            return 0.9
        elif contradiction_signals == 1:
            return 0.6
        else:
            return max(0.2, 0.6 - contradiction_signals * 0.1)



def _extract_keywords(text: str, min_length: int = 3) -> set:
    """Extract meaningful keywords from text."""
    # Stop words (English + Persian)
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "this", "that", "these", "those",
        "it", "its", "of", "in", "on", "at", "to", "for", "with", "by",
        "from", "and", "or", "but", "not", "what", "how", "why", "when",
        "where", "who", "which", "about", "more", "very", "just", "also",
        "که", "و", "در", "از", "به", "با", "این", "آن", "یک", "برای",
        "است", "هست", "بود", "شد", "می", "رو", "هم", "هر", "چه",
        "تا", "یا", "اما", "ولی", "اگر", "خیلی", "هم",
    }
    words = set(re.findall(r'\b\w{' + str(min_length) + r',}\b', text.lower()))
    return words - stop_words


def _is_persian(text: str) -> bool:
    """Quick check for Persian/Arabic text — v26.2: uses unified lang_detect."""
    try:
        from arki_project.utils.lang_detect import is_persian
        return is_persian(text)
    except ImportError:
        if not text:
            return False
        persian_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
        return persian_chars > latin_chars


_gate = None

def get_quality_gate() -> QualityGate:
    global _gate
    if _gate is None:
        _gate = QualityGate()
    return _gate


