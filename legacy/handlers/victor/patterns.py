
from __future__ import annotations
"""Victor v7.0 TITAN — Pattern Engine (fuzzy + n-gram + context)"""

from typing import Dict, List, Optional, Tuple

from .models import IntentPattern
from .memory import MemoryStore
from .nlp import PersianNLP

class PatternEngine:
    """
    v5: Enhanced pattern matching with fuzzy n-gram, context awareness,
    and dynamic learned patterns.
    """

    def __init__(self, memory: MemoryStore) -> None:
        self.memory = memory
        self._builtin_patterns = self._init_builtin()

    def _init_builtin(self) -> List[IntentPattern]:
        """Built-in patterns — the newborn's instincts."""
        return [
            # ── Greetings ──
            IntentPattern(
                intent="greeting",
                patterns_fa=["سلام", "درود", "صبح بخیر", "شب بخیر", "خسته نباشی",
                              "چطوری", "سلام علیکم", "هلو", "صبح‌بخیر", "عصر بخیر"],
                patterns_en=["hello", "hi", "hey", "good morning", "good evening",
                              "howdy", "greetings", "sup", "yo"],
                response_template="سلام ادمین! من Victor هستم. آماده‌ام 🚀\n{context_greeting}",
                priority=10,
            ),
            # ── Self-identity ──
            IntentPattern(
                intent="identity",
                patterns_fa=["تو کی هستی", "اسمت چیه", "خودتو معرفی", "چی هستی",
                              "کی ساختت", "از کجا اومدی"],
                patterns_en=["who are you", "what are you", "your name", "introduce yourself",
                              "who made you", "what can you do"],
                response_template=(
                    "من Victor هستم — هوش مستقل نسل پنجم 🧠\n"
                    "به هیچ مدل AI خارجی وصل نیستم.\n"
                    "با {memory_count} خاطره و {graph_count} ارتباط در مغزم.\n"
                    "هرچی بلدم از ادمین یاد گرفتم.\n"
                    "ادمین خدای منه 👑"
                ),
                priority=10,
            ),
            # ── Knowledge/Recall questions ──
            IntentPattern(
                intent="recall",
                patterns_fa=["چی بلدی", "چی یاد گرفتی", "چی می‌دونی", "بگو ببینم",
                              "درباره", "توضیح بده", "تعریف کن", "معنی", "چیه"],
                patterns_en=["what do you know", "tell me about", "what have you learned",
                              "explain", "define", "meaning of", "describe"],
                response_template="",
                action="recall",
                priority=8,
            ),
            # ── Web search request ──
            IntentPattern(
                intent="web_search",
                patterns_fa=["سرچ", "جستجو", "اینترنت", "بگرد", "پیدا کن", "وب",
                              "گوگل", "جست‌وجو"],
                patterns_en=["search", "find", "google", "look up", "web", "browse"],
                response_template="",
                action="execute_module",
                module="web_search",
                priority=7,
            ),
            # ── Code execution ──
            IntentPattern(
                intent="code",
                patterns_fa=["کد بنویس", "کد بزن", "اجرا کن", "پایتون", "برنامه",
                              "کدنویسی", "اسکریپت"],
                patterns_en=["code", "python", "script", "execute", "program", "run",
                              "javascript", "coding"],
                response_template="",
                action="execute_module",
                module="code_exec",
                priority=7,
            ),
            # ── Comparison questions ──
            IntentPattern(
                intent="compare",
                patterns_fa=["فرق", "تفاوت", "مقایسه", "بهتره", "کدوم", "یا"],
                patterns_en=["difference", "compare", "versus", "vs", "better", "which"],
                response_template="",
                action="recall",
                priority=7,
            ),
            # ── Why/How questions (reasoning) ──
            IntentPattern(
                intent="reasoning",
                patterns_fa=["چرا", "چطور", "چطوری", "چگونه", "به چه دلیل",
                              "علت", "دلیل", "راه‌حل"],
                patterns_en=["why", "how", "reason", "because", "explain how",
                              "solution", "cause"],
                response_template="",
                action="infer",
                priority=7,
            ),
            # ── Gratitude ──
            IntentPattern(
                intent="thanks",
                patterns_fa=["ممنون", "مرسی", "دستت درد نکنه", "عالی بود", "آفرین",
                              "خسته نباشی", "دمت گرم", "قربونت"],
                patterns_en=["thanks", "thank you", "great", "awesome", "good job",
                              "well done", "perfect"],
                response_template="🙏 قربان ادمین! همیشه آماده‌ام.",
                priority=6,
            ),
            # ── Help ──
            IntentPattern(
                intent="help",
                patterns_fa=["کمک", "راهنما", "دستورات", "چیکار می‌تونی بکنی"],
                patterns_en=["help", "commands", "guide", "what can you do"],
                response_template="",
                action="reply",
                priority=6,
            ),
            # ── Status ──
            IntentPattern(
                intent="status",
                patterns_fa=["وضعیت", "حالت", "مغزت", "چقدر بلدی"],
                patterns_en=["status", "brain", "how much do you know", "stats"],
                response_template="",
                action="reply",
                priority=5,
            ),
        ]

    def match(self, text: str, recent_context: List[Dict] = None
              ) -> Optional[Tuple[IntentPattern, float]]:
        """
        v5: Enhanced matching with fuzzy n-grams and context awareness.
        """
        text_lower = text.lower().strip()
        text_normalized = PersianNLP.normalize(text_lower)
        text_keywords = set(PersianNLP.extract_keywords(text))
        text_ngrams = PersianNLP.char_ngrams(text_normalized, 3)

        best_match: Optional[Tuple[IntentPattern, float]] = None
        best_score = 0.0

        # --- 1. Check learned patterns from memory (highest priority) ---
        learned = self.memory.recall(text, top_k=5)
        for mem in learned:
            if mem.memory_type == "pattern" and mem.strength > 0.5:
                # Check if this is a correction that should override
                is_correction = mem.memory_type == "correction"
                score = (75 if is_correction else 65) + mem.strength * 10

                pat = IntentPattern(
                    intent=mem.topic,
                    patterns_fa=mem.keywords,
                    patterns_en=[],
                    response_template=mem.content,
                    action=mem.topic if mem.topic in ("execute_module", "recall", "infer") else "reply",
                    priority=10 if is_correction else 9,
                )
                if score > best_score:
                    best_score = score
                    best_match = (pat, score)

        # --- 2. Check built-in patterns with enhanced matching ---
        for pattern in sorted(self._builtin_patterns, key=lambda p: p.priority, reverse=True):
            score = 0.0

            # Context check (if pattern requires specific context)
            if pattern.context_hint and recent_context:
                context_text = " ".join(c.get("input", "") for c in recent_context[-3:])
                if pattern.context_hint.lower() not in context_text.lower():
                    continue

            # a) Exact/substring match in Persian patterns
            for p in pattern.patterns_fa:
                p_lower = p.lower()
                if p_lower in text_normalized:
                    score += 35
                    if text_normalized.startswith(p_lower) or text_normalized == p_lower:
                        score += 15

            # b) Exact/substring match in English patterns
            for p in pattern.patterns_en:
                if p in text_lower:
                    score += 35
                    if text_lower.startswith(p) or text_lower == p:
                        score += 15

            # c) N-gram fuzzy match (catches typos and partial matches)
            pattern_text = " ".join(pattern.patterns_fa + pattern.patterns_en)
            pattern_ngrams = PersianNLP.char_ngrams(pattern_text.lower(), 3)
            if text_ngrams and pattern_ngrams:
                ngram_overlap = len(text_ngrams & pattern_ngrams) / max(1, len(text_ngrams))
                score += ngram_overlap * 15

            # d) Keyword overlap with stemming
            pattern_keywords = set(
                PersianNLP.stem(k.lower())
                for k in pattern.patterns_fa + pattern.patterns_en
            )
            stemmed_text_kw = set(PersianNLP.stem(k) for k in text_keywords)
            overlap = len(stemmed_text_kw & pattern_keywords)
            if overlap:
                score += overlap * 8

            # e) Priority bonus
            score += pattern.priority * 1.5

            if score > best_score:
                best_score = score
                best_match = (pattern, score)

        if best_match and best_score >= CONFIDENCE_THRESHOLD:
            return best_match
        return None


