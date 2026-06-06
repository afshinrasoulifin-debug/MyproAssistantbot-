
"""PersianTextToolkit — text utilities and formatting."""
from __future__ import annotations
"""Victor v7.0 TITAN — Persian NLP Engine & Text Toolkit"""

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Dict, List, Set, Tuple


# ═══════════════════════════════════════════════════════════════════
# 0. PERSIAN NLP ENGINE — No external deps
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# PERSIAN TEXT TOOLKIT — v7 TITAN Extended Capabilities
# ═══════════════════════════════════════════════════════════════════

class PersianTextToolkit:
    """
    Extended text processing capabilities for Victor:
    - Text statistics (readability, complexity)
    - Keyword extraction with TF ranking
    - Text comparison (diff)
    - Persian number handling (۱۲۳ ↔ 123)
    - Date/time extraction from Persian text
    - Word frequency analysis
    - N-gram extraction
    - Text classification hints
    """

    # Persian digits
    FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
    EN_DIGITS = "0123456789"

    # Persian months
    PERSIAN_MONTHS = {
        "فروردین": 1, "اردیبهشت": 2, "خرداد": 3,
        "تیر": 4, "مرداد": 5, "شهریور": 6,
        "مهر": 7, "آبان": 8, "آذر": 9,
        "دی": 10, "بهمن": 11, "اسفند": 12,
    }

    # Time patterns
    TIME_MARKERS = {
        "صبح": "morning", "ظهر": "noon", "بعدازظهر": "afternoon",
        "عصر": "evening", "شب": "night", "نیمه‌شب": "midnight",
        "فردا": "tomorrow", "دیروز": "yesterday", "امروز": "today",
        "هفته بعد": "next_week", "ماه بعد": "next_month",
        "پارسال": "last_year", "امسال": "this_year",
    }

    @classmethod
    def persian_to_english_digits(cls, text: str) -> str:
        """Convert Persian digits to English."""
        result = text
        for fa, en in zip(cls.FA_DIGITS, cls.EN_DIGITS):
            result = result.replace(fa, en)
        # Also handle Arabic digits
        arabic = "٠١٢٣٤٥٦٧٨٩"
        for ar, en in zip(arabic, cls.EN_DIGITS):
            result = result.replace(ar, en)
        return result

    @classmethod
    def english_to_persian_digits(cls, text: str) -> str:
        """Convert English digits to Persian."""
        result = text
        for en, fa in zip(cls.EN_DIGITS, cls.FA_DIGITS):
            result = result.replace(en, fa)
        return result

    @classmethod
    def extract_numbers(cls, text: str) -> List[float]:
        """Extract all numbers from text (Persian + English)."""
        normalized = cls.persian_to_english_digits(text)
        numbers = re.findall(r'-?\d+(?:\.\d+)?', normalized)
        return [float(n) for n in numbers]

    @classmethod
    def extract_dates(cls, text: str) -> List[Dict[str, Any]]:
        """Extract date references from Persian text."""
        dates = []
        normalized = cls.persian_to_english_digits(text)

        # Pattern: ۱۴۰۳/۰۶/۱۵ or 1403/06/15
        date_pattern = r'(\d{2,4})[/\-.](\d{1,2})[/\-.](\d{1,2})'
        for match in re.finditer(date_pattern, normalized):
            dates.append({
                "type": "exact",
                "year": int(match.group(1)),
                "month": int(match.group(2)),
                "day": int(match.group(3)),
                "raw": match.group(0),
            })

        # Pattern: ۱۵ خرداد ۱۴۰۳
        for month_name, month_num in cls.PERSIAN_MONTHS.items():
            pattern = rf'(\d{{1,2}})\s*{month_name}\s*(\d{{2,4}})?'
            for match in re.finditer(pattern, normalized):
                dates.append({
                    "type": "persian",
                    "day": int(match.group(1)),
                    "month": month_num,
                    "month_name": month_name,
                    "year": int(match.group(2)) if match.group(2) else None,
                    "raw": match.group(0),
                })

        # Relative time markers
        for marker, meaning in cls.TIME_MARKERS.items():
            if marker in text:
                dates.append({
                    "type": "relative",
                    "marker": marker,
                    "meaning": meaning,
                    "raw": marker,
                })

        return dates

    @classmethod
    def text_statistics(cls, text: str) -> Dict[str, Any]:
        """Comprehensive text statistics."""
        words = text.split()
        sentences = re.split(r'[.!?؟\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        word_lengths = [len(w) for w in words]
        sent_lengths = [len(s.split()) for s in sentences]

        # Unique words ratio (lexical diversity)
        unique = len(set(w.lower() for w in words))
        diversity = unique / max(1, len(words))

        # Average word length
        avg_word_len = sum(word_lengths) / max(1, len(word_lengths))

        # Readability estimate (simple Flesch-like for Persian)
        avg_sent_len = sum(sent_lengths) / max(1, len(sent_lengths))
        # Higher = harder to read
        complexity = (avg_word_len * 3 + avg_sent_len * 1.5) / 4.5

        return {
            "chars": len(text),
            "words": len(words),
            "unique_words": unique,
            "sentences": len(sentences),
            "paragraphs": len(text.split("\n\n")),
            "avg_word_length": round(avg_word_len, 1),
            "avg_sentence_length": round(avg_sent_len, 1),
            "lexical_diversity": round(diversity, 3),
            "complexity_score": round(complexity, 2),
            "complexity_label": (
                "ساده" if complexity < 3 else
                "متوسط" if complexity < 5 else
                "پیچیده" if complexity < 7 else
                "خیلی پیچیده"
            ),
            "longest_word": max(words, key=len) if words else "",
            "longest_sentence": max(sentences, key=lambda s: len(s.split())) if sentences else "",
        }

    @classmethod
    def word_frequency(cls, text: str, top_n: int = 20) -> List[Tuple[str, int]]:
        """Get word frequency distribution, excluding stopwords."""
        words = PersianNLP.tokenize(text)
        stopwords = PersianNLP.STOP_WORDS
        filtered = [w for w in words if w not in stopwords and len(w) > 1]
        return Counter(filtered).most_common(top_n)

    @classmethod
    def extract_ngrams(cls, text: str, n: int = 2, top_k: int = 10) -> List[Tuple[str, int]]:
        """Extract n-grams from text."""
        words = PersianNLP.tokenize(text)
        stopwords = PersianNLP.STOP_WORDS
        words = [w for w in words if w not in stopwords and len(w) > 1]

        if len(words) < n:
            return []

        ngrams: Counter = Counter()
        for i in range(len(words) - n + 1):
            gram = " ".join(words[i:i+n])
            ngrams[gram] += 1

        return ngrams.most_common(top_k)

    @classmethod
    def compare_texts(cls, text1: str, text2: str) -> Dict[str, Any]:
        """Compare two texts and show differences."""
        words1 = set(text1.split())
        words2 = set(text2.split())

        only_in_1 = words1 - words2
        only_in_2 = words2 - words1
        common = words1 & words2

        sim = PersianNLP.similarity(text1, text2)

        return {
            "similarity": round(sim, 3),
            "common_words": len(common),
            "only_in_first": len(only_in_1),
            "only_in_second": len(only_in_2),
            "total_first": len(words1),
            "total_second": len(words2),
            "unique_to_first": list(only_in_1)[:20],
            "unique_to_second": list(only_in_2)[:20],
        }

    @classmethod
    def classify_text_type(cls, text: str) -> str:
        """Classify text type (question, command, statement, greeting, etc.)."""
        text_lower = text.strip().lower()

        # Question
        if any(text_lower.endswith(m) for m in ["؟", "?"]):
            return "سوال"
        if any(text_lower.startswith(m) for m in ["آیا", "چرا", "چطور", "کجا", "کی", "چه", "کدام"]):
            return "سوال"

        # Command
        if any(text_lower.startswith(m) for m in ["بگو", "نشان", "بده", "حذف", "اضافه", "بساز", "بنویس"]):
            return "دستور"

        # Greeting
        greetings = {"سلام", "درود", "صبح بخیر", "شب بخیر", "خسته نباشی", "چطوری", "حالت چطوره"}
        if any(g in text_lower for g in greetings):
            return "احوال‌پرسی"

        # Farewell
        farewells = {"خداحافظ", "بای", "فعلا", "خدانگهدار", "شب خوش", "موفق باشی"}
        if any(f in text_lower for f in farewells):
            return "خداحافظی"

        # Thank
        if any(w in text_lower for w in ["ممنون", "مرسی", "تشکر", "دمت گرم", "سپاس", "متشکر"]):
            return "تشکر"

        # Complaint
        if any(w in text_lower for w in ["مشکل", "خراب", "ارور", "باگ", "درست نمیشه", "کار نمیکنه"]):
            return "شکایت"

        return "جمله"

    @classmethod
    def format_statistics_report(cls, text: str) -> str:
        """Generate a full text analysis report."""
        stats = cls.text_statistics(text)
        freq = cls.word_frequency(text, top_n=10)
        bigrams = cls.extract_ngrams(text, n=2, top_k=5)
        text_type = cls.classify_text_type(text)
        numbers = cls.extract_numbers(text)
        dates = cls.extract_dates(text)

        lines = [
            "📊 *تحلیل جامع متن:*\n",
            f"📝 نوع: {text_type}",
            f"🔤 کاراکترها: {stats['chars']}",
            f"📏 کلمات: {stats['words']} (یکتا: {stats['unique_words']})",
            f"📄 جملات: {stats['sentences']}",
            f"📐 میانگین طول کلمه: {stats['avg_word_length']}",
            f"📐 میانگین طول جمله: {stats['avg_sentence_length']} کلمه",
            f"🎯 تنوع واژگانی: {stats['lexical_diversity']:.1%}",
            f"📈 سطح پیچیدگی: {stats['complexity_label']} ({stats['complexity_score']})",
        ]

        if freq:
            lines.append("\n📊 *پرتکرارترین کلمات:*")
            for word, count in freq[:10]:
                bar = "█" * min(count, 20)
                lines.append(f"  {word}: {bar} ({count})")

        if bigrams:
            lines.append("\n📊 *عبارات پرتکرار:*")
            for gram, count in bigrams:
                lines.append(f"  «{gram}» — {count} بار")

        if numbers:
            lines.append(f"\n🔢 اعداد: {', '.join(str(n) for n in numbers[:10])}")

        if dates:
            lines.append("\n📅 تاریخ‌ها:")
            for d in dates[:5]:
                lines.append(f"  • {d['raw']} ({d['type']})")

        return "\n".join(lines)


