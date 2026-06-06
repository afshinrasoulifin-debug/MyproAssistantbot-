
"""PersianNLP — core Persian NLP class with mixin composition."""
from __future__ import annotations
"""Victor v7.0 TITAN — Persian NLP Engine & Text Toolkit"""

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Dict, List, Set, Tuple


# ═══════════════════════════════════════════════════════════════════
# 0. PERSIAN NLP ENGINE — No external deps
# ═══════════════════════════════════════════════════════════════════


from .v6_mixin import PersianNLPv6Mixin
from .v7_mixin import PersianNLPv7Mixin


class PersianNLP(PersianNLPv6Mixin, PersianNLPv7Mixin):
    """
    Pure-algorithmic Persian NLP toolkit.
    Handles stemming, normalization, tokenization, n-grams, and entity extraction.
    No ML models, no external dependencies.
    """

    # Common Persian prefixes and suffixes for stemming
    SUFFIXES = [
        # Superlative / Comparative (longest first)
        "ترین", "تری", "تر",
        # Plural forms
        "هایشان", "هایمان", "هایتان",
        "هایی", "های", "ها",
        "جات", "آت",
        # Possessive
        "مان", "تان", "شان",
        # Verb conjugation - past
        "اند", "اید", "ایم",
        # Verb conjugation - present
        "ند", "ید", "یم",
        # Infinitive / noun makers
        "یدن", "دن", "تن", "شتن", "ستن",
        # Adjective / noun derivation
        "انه", "مند", "وار", "گانه", "آنه",
        "ناک", "آلود", "آمیز", "آگین", "آسا",
        "گری", "گر", "چی", "بان", "دار", "کار", "ساز",
        "پذیر", "ناپذیر",
        # Place suffixes
        "ستان", "کده", "خانه", "گاه", "زار", "لاخ",
        # Abstract noun suffixes
        "یت", "گی", "شی", "ای",
        # Verbal noun
        "ش", "ار",
        # Object suffix
        "ات", "ان", "ون",
        # Single-char (last - least specific)
        "ی", "ه", "م", "ت",
    ]

    PREFIXES = [
        "می‌", "نمی‌", "بر‌", "در‌", "بی‌", "نا",
        "هم‌", "باز", "فرو", "پیش", "فرا", "ور",
        "بر", "در", "وا", "ب",
    ]

    # Comprehensive Persian stop words
    STOP_WORDS_FA = {
        # Conjunctions & Prepositions
        "و", "در", "به", "از", "که", "با", "تا", "بر", "برای", "جز",
        "مگر", "یا", "نه", "هم", "بلکه", "چون", "زیرا", "لذا", "پس",
        "اما", "ولی", "لیکن",
        # Pronouns
        "من", "تو", "او", "ما", "شما", "ایشان", "آنها", "اینها",
        "خود", "خودم", "خودت", "خودش", "خودمان", "خودتان", "خودشان",
        "این", "آن", "همین", "همان", "اون", "اینا", "اونا",
        # Demonstratives & Determiners
        "هر", "هیچ", "همه", "بعضی", "برخی", "چند", "هیچکدام",
        "یک", "یکی", "یه", "دیگر", "دیگه",
        # Auxiliary verbs / copula
        "است", "هست", "بود", "شد", "شده", "نیست", "نبود",
        "بودم", "بودی", "بوده", "بودیم", "بودید", "بودند",
        "هستم", "هستی", "هستیم", "هستید", "هستند",
        "باشم", "باشی", "باشد", "باشیم", "باشید", "باشند",
        "شدم", "شدی", "شدیم", "شدید", "شدند",
        "می‌شود", "می‌شوم", "می‌شوی", "می‌شویم", "می‌شوید", "می‌شوند",
        # Common verbs (light)
        "کردم", "کردی", "کرد", "کردیم", "کردید", "کردند",
        "می‌کنم", "می‌کنی", "می‌کند", "می‌کنیم", "می‌کنید", "می‌کنند",
        "کنم", "کنی", "کنه", "کنید", "کنند",
        "دارم", "داری", "داره", "داریم", "دارید", "دارند",
        "باید", "شاید", "بایست", "می‌بایست",
        "گفت", "گفتم", "می‌گه", "بگم", "بگو",
        # Adverbs of place/time
        "اینجا", "آنجا", "کجا", "بالا", "پایین", "جلو", "عقب",
        "الان", "حالا", "بعد", "قبل", "بعدا", "قبلا",
        "هنوز", "دوباره", "بازم", "تازه", "فعلا", "اکنون",
        "وقتی", "زمانی", "همیشه", "هرگز", "گاهی", "اغلب",
        # Adverbs of manner/degree
        "خیلی", "خوب", "بد", "فقط", "حتی", "تقریبا",
        "کاملا", "واقعا", "اصلا", "ابدا", "البته",
        # Question words
        "چی", "چه", "چیه", "چیست", "کی", "کجا", "کجاست",
        "چطور", "چطوری", "چگونه", "چرا", "چقدر", "چند",
        "آیا", "مگه", "مگر",
        # Discourse markers / fillers
        "خب", "خوب", "آره", "بله", "نه", "نخیر",
        "یعنی", "مثلا", "اصلا", "اتفاقا", "راستی", "ببین",
        "بذار", "ببینم", "بگذریم", "ضمنا", "بعلاوه",
        # Informal / colloquial
        "رو", "رو", "میشه", "بشه", "اگه", "دیگه", "چجوری",
        "اونجا", "اینجوری", "اونجوری", "الکی", "اینقدر", "اونقدر",
        # Relative / linking
        "مثل", "مانند", "بین", "توی", "روی", "پیش", "سر", "زیر",
        "درباره", "راجع", "نسبت", "طبق", "طی", "ضمن",
        "اینکه", "آنکه", "همانطور",
    }

    STOP_WORDS_EN = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "it", "its", "this", "that", "and", "or", "but", "not", "no",
        "if", "then", "else", "when", "where", "how", "what", "which",
        "who", "whom", "i", "you", "he", "she", "we", "they", "me",
        "my", "your", "his", "her", "our", "their", "am", "just",
        "so", "than", "too", "very", "also", "about", "up", "out",
    }

    # Persian character normalization map
    NORMALIZE_MAP = {
        "ك": "ک", "ي": "ی", "ى": "ی",
        "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
        "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
        "\u200c": " ",  # ZWNJ → space (for splitting compound words)
    }

    # Sentiment lexicon (rule-based)
    POSITIVE_FA = {
        # Joy / Happiness
        "عالی", "خوب", "بهترین", "فوق‌العاده", "ممنون", "مرسی", "زیبا",
        "قشنگ", "آفرین", "درست", "بهتر", "خوبه", "شاد", "خوشحال",
        "موفق", "پیروز", "سپاس", "تبریک", "خوشبختی", "امید",
        "قوی", "توانا", "هوشمند", "دقیق", "کامل", "حرفه‌ای", "باهوش",
        "سریع", "مثبت", "شگفت‌انگیز", "لذت", "دوست", "عشق",
        # Admiration / Praise
        "ایول", "دمت", "احسنت", "بارک‌الله", "خفن", "باحال", "توپ",
        "محشر", "بمب", "خدایی", "دمت‌گرم", "عجب", "ماشاالله",
        "چه‌خوب", "عالیه", "خوشگل", "ناز", "جذاب", "دلنشین",
        # Success / Achievement
        "پیشرفت", "ارتقا", "رشد", "بهبود", "توسعه", "دستاورد",
        "موفقیت", "کامیابی", "فتح", "غلبه", "برد", "قهرمان",
        "نخبه", "ممتاز", "برجسته", "شایسته", "لایق",
        # Positive emotions
        "آرامش", "صلح", "مهربان", "لطف", "محبت", "دلسوز",
        "صبور", "باوفا", "وفادار", "صادق", "راستگو", "مطمئن",
        "اعتماد", "ایمان", "باور", "امیدوار", "خوش‌بین",
        # Quality / Value
        "ارزشمند", "مفید", "سودمند", "کارآمد", "کاربردی",
        "اثربخش", "بهینه", "نوآورانه", "خلاقانه", "هوشمندانه",
        "جالب", "هیجان‌انگیز", "شورانگیز", "الهام‌بخش",
        # Gratitude / Thanks
        "تشکر", "سپاسگزار", "قدردان", "ممنونم", "مرسی",
        "متشکر", "لطف‌کردی", "زحمت‌کشیدی", "دستت‌درد‌نکنه",
        # Tech positive
        "بروز", "پایدار", "امن", "سالم", "بهینه‌سازی",
        "رفع", "حل", "اصلاح", "آپدیت", "ارتقاء",
    }
    NEGATIVE_FA = {
        # Anger / Frustration
        "بد", "افتضاح", "مشکل", "خراب", "اشتباه", "غلط", "ضعیف",
        "عصبانی", "خسته", "سخت", "خطا", "ایراد", "نقص",
        "بدترین", "وحشتناک", "شکست", "ناکامی", "شکایت", "گله",
        "مزخرف", "چرت", "بیخود", "زشت", "کثیف", "گند", "مسخره",
        # Sadness / Disappointment
        "ناامید", "ناراحت", "غم", "درد", "رنج", "ترس", "نگران",
        "غمگین", "دلتنگ", "افسرده", "بیچاره", "فلاکت", "بدبخت",
        "مصیبت", "فاجعه", "تراژدی", "متاسف", "افسوس", "حیف",
        # Fear / Danger
        "بحران", "خطر", "آسیب", "ضرر", "زیان", "تهدید",
        "خطرناک", "ترسناک", "وحشت", "هراس", "دلهره", "اضطراب",
        "نگرانی", "استرس", "فشار", "بار",
        # Failure / Problems
        "باگ", "کرش", "خرابی", "نقص", "عیب", "ایراد",
        "شکسته", "خراب‌شده", "کار‌نمی‌کنه", "ارور", "مشکلی",
        "ناقص", "معیوب", "پوکیده", "داغون", "له",
        # Insults / Strong negative
        "احمق", "نادان", "بیشعور", "اسکل", "بیسواد",
        "بی‌عرضه", "بی‌مصرف", "بی‌فایده", "الکی",
        # Negative emotions
        "نفرت", "لعنت", "انزجار", "تنفر", "کینه", "حسادت",
        "دروغ", "خیانت", "حقه", "کلک", "فریب", "تقلب",
        # Tech negative
        "هنگ", "لگ", "قطع", "قطعی", "کندی", "تاخیر",
        "ویروس", "هک", "نفوذ", "سرقت", "از‌دست‌رفته",
    }
    POSITIVE_EN = {
        "good", "great", "excellent", "amazing", "awesome", "wonderful",
        "fantastic", "perfect", "love", "best", "beautiful", "nice",
        "happy", "success", "win", "correct", "right", "smart",
        "brilliant", "superb", "outstanding", "impressive", "helpful",
    }
    NEGATIVE_EN = {
        "bad", "terrible", "awful", "horrible", "wrong", "error",
        "fail", "failure", "poor", "weak", "broken", "bug", "problem",
        "issue", "hate", "worst", "ugly", "stupid", "slow", "crash",
        "angry", "sad", "frustrated", "disappointed", "confused",
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        """Normalize Persian text: fix Arabic chars, digits, ZWNJ."""
        for src, dst in cls.NORMALIZE_MAP.items():
            text = text.replace(src, dst)
        # Remove diacritics (tashkil)
        text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """
        Smart tokenizer for mixed Persian/English text.
        Handles: Persian words, English words, numbers, URLs, emails.
        """
        text = cls.normalize(text)
        # Extract URLs and emails first
        urls = re.findall(r'https?://\S+|www\.\S+', text)
        emails = re.findall(r'\S+@\S+\.\S+', text)
        # Remove them from text
        for u in urls + emails:
            text = text.replace(u, ' ')
        # Tokenize: Persian chars + English chars + digits
        tokens = re.findall(r'[\u0600-\u06FF]+|[a-zA-Z]+|[0-9]+', text.lower())
        return tokens

    @classmethod
    def stem(cls, word: str) -> str:
        """
        Simple Persian stemmer — removes common suffixes/prefixes.
        Not as advanced as Hazm, but works without external deps.
        """
        original = word
        # Remove suffixes (longest first)
        for suffix in sorted(cls.SUFFIXES, key=len, reverse=True):
            if word.endswith(suffix) and len(word) - len(suffix) >= 2:
                word = word[:-len(suffix)]
                break
        # Remove prefixes
        for prefix in sorted(cls.PREFIXES, key=len, reverse=True):
            if word.startswith(prefix) and len(word) - len(prefix) >= 2:
                word = word[len(prefix):]
                break
        return word if len(word) >= 2 else original

    @classmethod
    def extract_keywords(cls, text: str, max_keywords: int = 25) -> List[str]:
        """Extract meaningful keywords with stemming."""
        tokens = cls.tokenize(text)
        stop_words = cls.STOP_WORDS_FA | cls.STOP_WORDS_EN
        keywords = []
        seen = set()
        for t in tokens:
            if t in stop_words or len(t) <= 1:
                continue
            stemmed = cls.stem(t)
            if stemmed not in seen:
                seen.add(stemmed)
                keywords.append(stemmed)
            # Also keep original if different
            if t != stemmed and t not in seen:
                seen.add(t)
                keywords.append(t)
        return keywords[:max_keywords]

    @classmethod
    def char_ngrams(cls, text: str, n: int = 3) -> Set[str]:
        """Generate character-level n-grams for fuzzy matching."""
        text = cls.normalize(text.lower())
        return {text[i:i+n] for i in range(len(text) - n + 1)} if len(text) >= n else {text}

    @classmethod
    def word_ngrams(cls, tokens: List[str], n: int = 2) -> List[str]:
        """Generate word-level n-grams (bigrams, trigrams)."""
        return [' '.join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]

    @classmethod
    def extract_entities(cls, text: str) -> Dict[str, List[str]]:
        """
        Rule-based entity extraction.
        Extracts: numbers, dates, URLs, emails, Persian names (heuristic).
        """
        entities: Dict[str, List[str]] = {
            "numbers": [],
            "dates": [],
            "urls": [],
            "emails": [],
            "mentions": [],
        }
        # Numbers (Persian + English digits)
        entities["numbers"] = re.findall(r'\b\d+(?:\.\d+)?\b', cls.normalize(text))
        # URLs
        entities["urls"] = re.findall(r'https?://\S+|www\.\S+', text)
        # Emails
        entities["emails"] = re.findall(r'[\w.-]+@[\w.-]+\.\w+', text)
        # Dates (various formats)
        entities["dates"] = re.findall(
            r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b'  # YYYY-MM-DD
            r'|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b'  # DD/MM/YYYY
            r'|\b\d{1,2}\s+(?:فروردین|اردیبهشت|خرداد|تیر|مرداد|شهریور|مهر|آبان|آذر|دی|بهمن|اسفند)\s+\d{2,4}\b',
            text
        )
        # @mentions
        entities["mentions"] = re.findall(r'@(\w+)', text)
        return entities

    @classmethod
    def analyze_sentiment(cls, text: str) -> Tuple[str, float]:
        """
        Rule-based sentiment analysis.
        Returns: (label: positive|negative|neutral, score: -1.0 to 1.0)
        """
        tokens = set(cls.tokenize(text))
        pos_count = len(tokens & cls.POSITIVE_FA) + len(tokens & cls.POSITIVE_EN)
        neg_count = len(tokens & cls.NEGATIVE_FA) + len(tokens & cls.NEGATIVE_EN)

        # Check for negation patterns
        negation_patterns = ["نه ", "نیست", "نمی", "نکن", "بدون", "مگه", "هیچ"]
        has_negation = any(p in text for p in negation_patterns)
        if has_negation:
            pos_count, neg_count = neg_count, pos_count  # flip

        total = pos_count + neg_count
        if total == 0:
            return "neutral", 0.0

        score = (pos_count - neg_count) / total
        if score > 0.2:
            return "positive", score
        elif score < -0.2:
            return "negative", score
        return "neutral", score

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Detect if text is primarily Persian or English."""
        persian_chars = len(re.findall(r'[\u0600-\u06FF]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        if persian_chars > english_chars:
            return "fa"
        elif english_chars > persian_chars:
            return "en"
        return "mixed"

    @classmethod
    def similarity(cls, text1: str, text2: str) -> float:
        """
        Enhanced similarity using multiple signals:
        1. Character n-gram Jaccard
        2. Token overlap
        3. Sequence matching
        Returns: 0.0 to 1.0
        """
        # 1. Character trigram Jaccard
        ngrams1 = cls.char_ngrams(text1, 3)
        ngrams2 = cls.char_ngrams(text2, 3)
        if ngrams1 and ngrams2:
            jaccard = len(ngrams1 & ngrams2) / len(ngrams1 | ngrams2)
        else:
            jaccard = 0.0

        # 2. Token overlap
        tokens1 = set(cls.tokenize(text1))
        tokens2 = set(cls.tokenize(text2))
        if tokens1 and tokens2:
            token_overlap = len(tokens1 & tokens2) / max(len(tokens1), len(tokens2))
        else:
            token_overlap = 0.0

        # 3. Sequence matching (for substring/ordering)
        seq_ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

        # Weighted combination
        return jaccard * 0.35 + token_overlap * 0.40 + seq_ratio * 0.25




