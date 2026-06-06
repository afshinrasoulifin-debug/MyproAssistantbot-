
from __future__ import annotations
"""Victor v7.0 TITAN — Persian NLP Engine & Text Toolkit"""

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any, Dict, List, Set, Tuple


# ═══════════════════════════════════════════════════════════════════
# 0. PERSIAN NLP ENGINE — No external deps
# ═══════════════════════════════════════════════════════════════════

class PersianNLP:
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


    # ── v6 Additions ──────────────────────────────────────────

    COMPOUND_WORDS = {
        # AI / ML
        "هوش مصنوعی": "هوش_مصنوعی",
        "یادگیری ماشین": "یادگیری_ماشین",
        "یادگیری عمیق": "یادگیری_عمیق",
        "پردازش زبان": "پردازش_زبان",
        "پردازش زبان طبیعی": "پردازش_زبان_طبیعی",
        "شبکه عصبی": "شبکه_عصبی",
        "شبکه عصبی عمیق": "شبکه_عصبی_عمیق",
        "بینایی ماشین": "بینایی_ماشین",
        "بینایی کامپیوتر": "بینایی_کامپیوتر",
        "داده کاوی": "داده_کاوی",
        "علم داده": "علم_داده",
        "مدل زبانی": "مدل_زبانی",
        "مدل زبانی بزرگ": "مدل_زبانی_بزرگ",
        # Software / Tech
        "پایگاه داده": "پایگاه_داده",
        "سیستم عامل": "سیستم_عامل",
        "نرم افزار": "نرم_افزار",
        "سخت افزار": "سخت_افزار",
        "برنامه نویسی": "برنامه_نویسی",
        "کد نویسی": "کد_نویسی",
        "وب سایت": "وب_سایت",
        "اپلیکیشن موبایل": "اپلیکیشن_موبایل",
        "رابط کاربری": "رابط_کاربری",
        "تجربه کاربری": "تجربه_کاربری",
        "فضای ابری": "فضای_ابری",
        "امنیت سایبری": "امنیت_سایبری",
        "اینترنت اشیا": "اینترنت_اشیا",
        "واقعیت مجازی": "واقعیت_مجازی",
        "واقعیت افزوده": "واقعیت_افزوده",
        "بلاک چین": "بلاک_چین",
        "رایانش ابری": "رایانش_ابری",
        "توسعه دهنده": "توسعه_دهنده",
        "مهندس نرم افزار": "مهندس_نرم_افزار",
        "تست نرم افزار": "تست_نرم_افزار",
        "کنترل نسخه": "کنترل_نسخه",
        "پشته فناوری": "پشته_فناوری",
        # Networking
        "شبکه اجتماعی": "شبکه_اجتماعی",
        "پروتکل ارتباطی": "پروتکل_ارتباطی",
        "آدرس آی‌پی": "آدرس_آی_پی",
        "نام دامنه": "نام_دامنه",
        # Science
        "تغییر اقلیم": "تغییر_اقلیم",
        "انرژی تجدیدپذیر": "انرژی_تجدیدپذیر",
        "سلول خورشیدی": "سلول_خورشیدی",
        "ژن درمانی": "ژن_درمانی",
        "مهندسی ژنتیک": "مهندسی_ژنتیک",
        "فیزیک کوانتوم": "فیزیک_کوانتوم",
        "نانو تکنولوژی": "نانو_تکنولوژی",
        # Business
        "بازار سرمایه": "بازار_سرمایه",
        "کسب و کار": "کسب_و_کار",
        "مدیر عامل": "مدیر_عامل",
        "هیئت مدیره": "هیئت_مدیره",
        "بورس اوراق بهادار": "بورس_اوراق_بهادار",
        "صندوق سرمایه گذاری": "صندوق_سرمایه_گذاری",
        # Daily life
        "حمل و نقل": "حمل_و_نقل",
        "بهداشت و درمان": "بهداشت_و_درمان",
        "آموزش و پرورش": "آموزش_و_پرورش",
        "صنایع دستی": "صنایع_دستی",
        "میراث فرهنگی": "میراث_فرهنگی",
        "حقوق بشر": "حقوق_بشر",
    }

    SPELL_MAP = {
        # Tech terms
        "هوش مصنوی": "هوش مصنوعی",
        "برنامه نویصی": "برنامه نویسی",
        "کامپیوطر": "کامپیوتر",
        "سیسطم": "سیستم",
        "بانک اطلاعاطی": "بانک اطلاعاتی",
        "اینطرنت": "اینترنت",
        "الگوریطم": "الگوریتم",
        "دیطابیس": "دیتابیس",
        "فریم ورک": "فریمورک",
        "سرور": "سرور",
        "ربات": "ربات",
        "پایطون": "پایتون",
        "جاواسکریپط": "جاواسکریپت",
        "لاینوکس": "لینوکس",
        "ویندز": "ویندوز",
        "داکر": "داکر",
        # Common misspellings - letter swaps
        "تلگرام": "تلگرام",
        "بلوطوث": "بلوتوث",
        "اپلیکیشن": "اپلیکیشن",
        "دسطرسی": "دسترسی",
        "امنییت": "امنیت",
        "سرویص": "سرویس",
        "پروتکل": "پروتکل",
        # ط/ت confusion (very common in Persian typing)
        "اطلاعاط": "اطلاعات",
        "اینطرنطی": "اینترنتی",
        "طکنولوژی": "تکنولوژی",
        "طوسعه": "توسعه",
        "طحقیق": "تحقیق",
        "طغییر": "تغییر",
        "طشکر": "تشکر",
        "طمام": "تمام",
        "طوضیح": "توضیح",
        "طجربه": "تجربه",
        "طعریف": "تعریف",
        "طعداد": "تعداد",
        "طصویر": "تصویر",
        "طصمیم": "تصمیم",
        "طوجه": "توجه",
        "طعامل": "تعامل",
        # ص/س confusion
        "صلام": "سلام",
        "صیستم": "سیستم",
        "صوال": "سوال",
        "صاعت": "ساعت",
        "صرعت": "سرعت",
        "صرویس": "سرویس",
        "صطح": "سطح",
        "صاختار": "ساختار",
        "صاده": "ساده",
        "صیاست": "سیاست",
        # ض/ز confusion
        "ضمان": "زمان",
        "ضبان": "زبان",
        "ضیاد": "زیاد",
        "ضندگی": "زندگی",
        "ضمین": "زمین",
        # ذ/ز confusion
        "ذیاد": "زیاد",
        "ذبان": "زبان",
        "ذمان": "زمان",
        # غ/ق confusion
        "غانون": "قانون",
        "غدرت": "قدرت",
        "غابل": "قابل",
        "غیمت": "قیمت",
        "غسمت": "قسمت",
        # Colloquial → Standard
        "میخوام": "می‌خواهم",
        "میشه": "می‌شود",
        "نمیشه": "نمی‌شود",
        "نمیدونم": "نمی‌دانم",
        "میدونم": "می‌دانم",
        "بزار": "بگذار",
        "میتونم": "می‌توانم",
        "نمیتونم": "نمی‌توانم",
        "اینجوری": "اینطوری",
        "چیکار": "چه کار",
        "چجوری": "چطوری",
        # Half-space missing (common)
        "میکنم": "می‌کنم",
        "میکنی": "می‌کنی",
        "میکنه": "می‌کند",
        "نمیکنم": "نمی‌کنم",
        "میگم": "می‌گویم",
        "میگه": "می‌گوید",
        "نمیگه": "نمی‌گوید",
        "میدم": "می‌دهم",
        "میده": "می‌دهد",
        "میره": "می‌رود",
        "میام": "می‌آیم",
        "میاد": "می‌آید",
        "میشم": "می‌شوم",
        "نمیشم": "نمی‌شوم",
        "میخورم": "می‌خورم",
        "میخونم": "می‌خوانم",
        "مینویسم": "می‌نویسم",
        "میفهمم": "می‌فهمم",
        "نمیفهمم": "نمی‌فهمم",
        # Doubled letters
        "اللبته": "البته",
        "ممنونن": "ممنون",
        "سللام": "سلام",
    }

    @classmethod
    def handle_compounds(cls, text: str) -> str:
        """Join compound words for better matching."""
        for compound, joined in cls.COMPOUND_WORDS.items():
            text = text.replace(compound, joined)
        return text

    @classmethod
    def spell_check(cls, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """Basic Persian spell correction. Returns (corrected, [(wrong, right)])."""
        corrections = []
        for wrong, right in cls.SPELL_MAP.items():
            if wrong in text:
                text = text.replace(wrong, right)
                corrections.append((wrong, right))
        return text, corrections

    @classmethod
    def extract_numbers(cls, text: str) -> List[str]:
        """Extract Persian and Latin numbers from text."""
        persian_nums = re.findall(r"[\u06F0-\u06F9]+(?:\.[\u06F0-\u06F9]+)?", text)
        latin_nums = re.findall(r"[0-9]+(?:\.[0-9]+)?", text)
        return persian_nums + latin_nums

    @classmethod
    def normalize_numbers(cls, text: str) -> str:
        """Convert Persian/Arabic numerals to Latin."""
        persian = "۰۱۲۳۴۵۶۷۸۹"
        arabic = "٠١٢٣٤٥٦٧٨٩"
        for i, (p, a) in enumerate(zip(persian, arabic)):
            text = text.replace(p, str(i)).replace(a, str(i))
        return text

    @classmethod
    def detect_question_type(cls, text: str) -> str:
        """Detect Persian question type."""
        t = text.strip()
        if any(t.startswith(w) for w in ["چرا", "به چه دلیل", "علت"]):
            return "why"
        if any(t.startswith(w) for w in ["چطور", "چگونه", "چجوری", "چطوری"]):
            return "how"
        if any(t.startswith(w) for w in ["کجا", "کجاست"]):
            return "where"
        if any(t.startswith(w) for w in ["چی", "چیه", "چیست", "چه چیزی"]):
            return "what"
        if any(t.startswith(w) for w in ["آیا", "ایا"]):
            return "yes_no"
        if any(t.startswith(w) for w in ["چند", "چقدر", "چه مقدار"]):
            return "quantity"
        if "؟" in text or "?" in text:
            return "general_question"
        return "statement"

    @classmethod
    def enhanced_sentiment(cls, text: str) -> Dict[str, Any]:
        """v6: Multi-emotion sentiment analysis (joy, anger, sadness, surprise, fear)."""
        emotions = {"joy": 0.0, "anger": 0.0, "sadness": 0.0, "surprise": 0.0, "fear": 0.0}

        joy_words = {"خوشحال", "عالی", "ممنون", "مرسی", "آفرین", "بهترین", "خوب",
                     "عشقه", "دمت", "فوق‌العاده", "محشر", "لذت", "شاد", "خنده"}
        anger_words = {"عصبانی", "بد", "افتضاح", "مزخرف", "گند", "خراب", "زشت",
                       "بیشعور", "احمق", "مسخره", "نفرت", "لعنت"}
        sad_words = {"غمگین", "ناراحت", "متاسف", "افسوس", "بدبخت", "گریه", "درد",
                     "تنها", "غم", "اشک", "سخت"}
        surprise_words = {"واقعا", "عجب", "باورنکردنی", "شگفت", "عجیب", "وای", "نه"}
        fear_words = {"ترس", "خطر", "وحشت", "نگران", "اضطراب", "خطرناک", "ترسناک"}

        normalized = cls.normalize(text)
        words = set(cls.tokenize(normalized)) | set(normalized.split())
        emotions["joy"] = len(words & joy_words) * 0.25
        emotions["anger"] = len(words & anger_words) * 0.25
        emotions["sadness"] = len(words & sad_words) * 0.25
        emotions["surprise"] = len(words & surprise_words) * 0.2
        emotions["fear"] = len(words & fear_words) * 0.25

        total = sum(emotions.values()) or 1.0
        emotions = {k: min(1.0, v / total) if total > 1 else v for k, v in emotions.items()}

        positive = emotions["joy"] + emotions["surprise"] * 0.3
        negative = emotions["anger"] + emotions["sadness"] + emotions["fear"]
        score = max(-1.0, min(1.0, positive - negative))

        sentiment = "positive" if score > 0.2 else ("negative" if score < -0.2 else "neutral")
        return {"sentiment": sentiment, "score": score, "emotions": emotions}

    # ── v7 TITAN Additions ──────────────────────────────────────

    @classmethod
    def enhanced_sentiment_v7(cls, text: str) -> Dict[str, Any]:
        """v7: 10-emotion sentiment analysis with intensity scaling."""
        emotions = {
            "joy": 0.0, "anger": 0.0, "sadness": 0.0, "surprise": 0.0,
            "fear": 0.0, "trust": 0.0, "disgust": 0.0, "anticipation": 0.0,
            "love": 0.0, "curiosity": 0.0,
        }

        lexicon = {
            "joy": {
                "خوشحال", "شاد", "خنده", "لبخند", "عالی", "خوب", "مثبت",
                "هیجان", "جشن", "تبریک", "پیروز", "برد", "موفقیت", "لذت",
                "شادی", "نشاط", "سرور", "وجد", "شعف", "سرخوش", "خرم",
                "شکوفا", "بهجت", "مسرت", "فرح", "طرب", "خوشی", "خوشنود",
                "راضی", "خرسند", "خندان", "بشاش", "شنگول", "سرحال",
                "دلشاد", "جذل", "ذوق", "هلهله", "شادمانی", "خوشوقت",
                "ایول", "عجب", "محشر", "بمب", "توپ", "خفن", "باحال",
            },
            "anger": {
                "عصبانی", "خشم", "غضب", "بد", "افتضاح", "مزخرف", "گند",
                "خراب", "زشت", "بیشعور", "احمق", "مسخره", "نفرت", "لعنت",
                "کثیف", "پست", "رذل", "دنی", "حقیر", "خائن", "منافق",
                "ظالم", "ستمگر", "بیدادگر", "وقیح", "بی‌شرم", "پررو",
                "عوضی", "نامرد", "بی‌انصاف", "جلاد", "سفاک", "بی‌رحم",
                "آتشی", "کفری", "قاطی", "جوش", "داغ", "برزخ",
                "اعصابم", "عصبی", "دیوونه", "جنون", "خشمگین",
            },
            "sadness": {
                "غمگین", "ناراحت", "متاسف", "افسوس", "بدبخت", "گریه",
                "درد", "تنها", "غم", "اشک", "سخت", "دلتنگ", "افسرده",
                "محزون", "اندوهگین", "غصه", "حسرت", "ماتم", "عزا",
                "سوگ", "فراق", "هجران", "جدایی", "دوری", "تنهایی",
                "بیچاره", "مسکین", "بینوا", "درمانده", "عاجز",
                "شکسته", "خسته", "فرسوده", "داغدار", "سیاه‌بخت",
                "دلشکسته", "دل‌مرده", "بغض", "زار", "نالان",
            },
            "surprise": {
                "واقعا", "عجب", "باورنکردنی", "شگفت", "عجیب", "وای",
                "نه", "جدی", "شوکه", "متحیر", "حیرت", "تعجب",
                "غافلگیر", "ناگهانی", "غیرمنتظره", "بی‌سابقه",
                "عجیب‌وغریب", "شگفت‌انگیز", "شگفت‌آور", "خارق‌العاده",
                "اعجاب", "حیرت‌آور", "مبهوت", "بهت", "گیج",
                "باورم‌نمیشه", "چطوری‌ممکنه", "مگه‌میشه", "یعنی‌چی",
                "نه‌بابا", "وای‌خدا", "خدای‌من", "ای‌بابا", "اوه",
            },
            "fear": {
                "ترس", "خطر", "وحشت", "نگران", "اضطراب", "خطرناک",
                "ترسناک", "هول", "هراس", "دلهره", "وحشتناک",
                "مخوف", "رعب", "رعب‌آور", "مهیب", "سهمگین",
                "بیم", "خوف", "واهمه", "هیبت", "دلشوره",
                "استرس", "تشویش", "پریشان", "مضطرب", "نگرانی",
                "بلا", "آفت", "مصیبت", "فاجعه", "بحران",
                "تهدید", "خطرساز", "ناامن", "آسیب‌پذیر",
            },
            "trust": {
                "اعتماد", "صادق", "وفادار", "قابل‌اعتماد", "مطمئن",
                "باوفا", "راستگو", "امین", "درستکار", "پاک",
                "صداقت", "وفا", "عهد", "پیمان", "قول",
                "اطمینان", "ایمان", "باور", "یقین", "اتکا",
                "اعتبار", "حسن‌نیت", "خیرخواه", "دلسوز", "مهربان",
                "حامی", "پشتیبان", "یاور", "همراه", "همدل",
                "مسئول", "متعهد", "پایبند", "وظیفه‌شناس",
            },
            "anticipation": {
                "منتظر", "امیدوار", "آینده", "فردا", "هدف", "برنامه",
                "پیش‌بینی", "انتظار", "آماده", "هیجان", "مشتاق",
                "طالب", "خواهان", "آرزو", "حسرت", "تشنه",
                "بی‌صبر", "بی‌تاب", "لحظه‌شماری", "چشم‌انتظار",
                "ترقب", "توقع", "امید", "آرزومند", "متمنی",
                "طرح", "نقشه", "استراتژی", "چشم‌انداز", "افق",
                "رویا", "خیال", "تصور", "پندار",
            },
            "love": {
                "عشق", "دوست", "عاشق", "جان", "عزیز", "قلب",
                "محبت", "دلبر", "یار", "جانم", "عزیزم", "نازنین",
                "دلدار", "معشوق", "محبوب", "دلنشین", "دلربا",
                "شیرین", "مهربان", "مهرآمیز", "صمیمی", "گرم",
                "آغوش", "بوسه", "نوازش", "لطف", "مهر",
                "وابسته", "شیفته", "فریفته", "دلباخته", "شیدا",
                "مجنون", "خاطرخواه", "دلداده", "گرفتار", "مفتون",
                "عشقم", "قربونت", "فدات",
            },
            "curiosity": {
                "جالب", "کنجکاو", "سوال", "چرا", "چطور", "چگونه",
                "بگو", "توضیح", "بفهمم", "یاد", "دانش", "علم",
                "کاوش", "جستجو", "تحقیق", "بررسی", "تجزیه",
                "تحلیل", "پژوهش", "مطالعه", "آزمایش", "آموزش",
                "کشف", "اکتشاف", "نوآوری", "ابتکار", "ایده",
                "فهم", "درک", "شناخت", "آگاهی", "بینش",
                "تعجب", "حس‌کنجکاوی", "می‌خوام‌بدونم", "بگو‌ببینم",
            },
        }

        # Use proper tokenizer (handles half-spaces, normalization)
        normalized = cls.normalize(text)
        words = set(cls.tokenize(normalized)) | set(normalized.split())
        for emotion, word_set in lexicon.items():
            count = len(words & word_set)
            emotions[emotion] = min(1.0, count * 0.2)

        # Boost based on punctuation intensity
        exclaim_count = text.count("!") + text.count("!")
        question_count = text.count("?") + text.count("؟")
        if exclaim_count >= 3:
            for e in ("anger", "joy", "surprise"):
                emotions[e] = min(1.0, emotions[e] + 0.2)
        if question_count >= 2:
            emotions["curiosity"] = min(1.0, emotions["curiosity"] + 0.3)

        total = sum(emotions.values()) or 1.0
        dominant = max(emotions, key=emotions.get)
        score = emotions.get("joy", 0) + emotions.get("love", 0) - emotions.get("anger", 0) - emotions.get("sadness", 0)
        score = max(-1.0, min(1.0, score))

        return {
            "sentiment": "positive" if score > 0.15 else ("negative" if score < -0.15 else "neutral"),
            "score": round(score, 3),
            "emotions": emotions,
            "dominant_emotion": dominant,
            "intensity": round(total / len(emotions), 3),
        }

    @classmethod
    def decompose_question(cls, text: str) -> List[str]:
        """v7: Decompose compound questions into sub-questions."""
        # Split on conjunctions and question markers
        parts = re.split(r'[،,]\s*(?:و\s+)?(?:همچنین\s+)?|(?:\s+و\s+)', text)
        questions = []
        for part in parts:
            part = part.strip()
            if len(part) > 5:
                # If it doesn't have a question marker, inherit from original
                if "؟" not in part and "?" not in part:
                    q_type = cls.detect_question_type(text)
                    if q_type != "statement":
                        part = part.rstrip("؟? ") + "؟"
                questions.append(part)
        return questions if len(questions) > 1 else [text]

    @classmethod
    def detect_formality(cls, text: str) -> str:
        """v7: Detect if text is formal or informal Persian."""
        informal_markers = {
            "نمیشه", "میخوام", "بگو", "چیه", "کجاست", "نمیدونم",
            "میشه", "اینجوری", "اونجوری", "چجوری", "بده", "بزن",
            "دمت", "ایول", "خفن", "باحال", "چرت", "اسکل",
            "اگه", "بره", "بیاد", "بشه", "نشه", "نمیتونم",
        }
        formal_markers = {
            "می‌شود", "می‌خواهم", "بفرمایید", "لطفاً", "خواهشمند",
            "نمی‌توانم", "می‌توانید", "نمی‌شود", "بنده", "جنابعالی",
            "حضرتعالی", "محترم", "ارجمند", "مستدعی", "تقاضا",
        }
        normalized = cls.normalize(text)
        words = set(cls.tokenize(normalized)) | set(normalized.split())
        informal_score = len(words & informal_markers)
        formal_score = len(words & formal_markers)
        if informal_score > formal_score:
            return "informal"
        elif formal_score > informal_score:
            return "formal"
        return "neutral"

    @classmethod
    def resolve_coreference(cls, text: str, context_turns: list) -> str:
        """v7: Resolve pronouns/references using conversation context.
        
        Strategy: Only resolve when we have HIGH confidence about what
        the pronoun refers to. A wrong resolution is worse than none.
        
        Rules:
        - Only resolve if the ENTIRE message is a short follow-up (< 6 words)
        - Only resolve specific referential pronouns, not demonstratives used normally
        - Only use the topic from the immediately previous turn (not random keyword)
        - Append context rather than replace (safer — preserves original)
        """
        # Only attempt for very short follow-ups that are clearly referential
        words = text.split()
        if len(words) > 6 or not context_turns:
            return text

        # Referential pronouns that clearly point to something said before
        referential_fa = {"اون", "همون", "اونا"}
        referential_en = {"it", "that"}
        text_words = set(cls.tokenize(text))
        found_pronouns = text_words & (referential_fa | referential_en)

        if not found_pronouns:
            return text

        # Get the topic from the LAST bot or user turn only
        last_turn = context_turns[-1] if context_turns else None
        if not last_turn:
            return text

        turn_text = last_turn.text if hasattr(last_turn, 'text') else str(last_turn)
        keywords = cls.extract_keywords(turn_text, max_keywords=3)
        if not keywords:
            return text

        # Instead of replacing the pronoun (risky), append context hint
        # This way the retrieval system gets both the original and the context
        topic_hint = keywords[0]
        return f"{text} [{topic_hint}]"

    @classmethod
    def extract_relations_from_text(cls, text: str) -> List[Tuple[str, str, str]]:
        """v7: Auto-extract subject-relation-object triples from text.
        
        Covers 30+ Persian relation patterns across:
        - Classification (is_a, type_of, instance_of)
        - Composition (part_of, has, contains)
        - Causation (causes, leads_to, prevents)
        - Comparison (similar_to, opposite_of, better_than)
        - Dependency (requires, depends_on, enables)
        - Creation (produces, creates, invented_by)
        - Purpose (used_for, designed_for)
        - Location (located_in, belongs_to)
        - Temporal (before, after, during)
        """
        relations = []
        patterns = [
            # Classification
            (r"(.+?)\s+(?:یک|یه|یکی از)\s+(.+?)\s+(?:است|هست|هستند|بود|باشد)", "is_a"),
            (r"(.+?)\s+(?:نوعی|نوع|گونه‌ای)\s+(.+?)(?:\s+است|\s|$)", "type_of"),
            (r"(.+?)\s+(?:از نوع|از جنس|از دسته)\s+(.+?)(?:\s|$|؟)", "type_of"),
            # Composition / Structure
            (r"(.+?)\s+(?:قسمتی از|بخشی از|جزئی از|زیرمجموعه)\s+(.+)", "part_of"),
            (r"(.+?)\s+(?:دارای|شامل|دارد|داره|محتوی)\s+(.+)", "has"),
            (r"(.+?)\s+(?:تشکیل شده از|ساخته شده از|متشکل از)\s+(.+)", "composed_of"),
            (r"(.+?)\s+(?:حاوی|شامل|دربرگیرنده)\s+(.+?)(?:\s|$)", "contains"),
            # Causation
            (r"(.+?)\s+(?:باعث|علت|دلیل|سبب)\s+(.+?)\s+(?:است|هست|میشه|می‌شود|شد)", "causes"),
            (r"(.+?)\s+(?:منجر به|منتهی به)\s+(.+?)\s+(?:می‌شود|میشه|شد)", "leads_to"),
            (r"(.+?)\s+(?:جلوگیری|پیشگیری|مانع)\s+(?:از\s+)?(.+?)(?:\s|$)", "prevents"),
            (r"(.+?)\s+(?:تاثیر|اثر|نقش)\s+(?:در|بر|روی)\s+(.+?)(?:\s|$)", "affects"),
            # Dependency
            (r"(.+?)\s+(?:نیاز به|نیازمند|وابسته به)\s+(.+?)(?:\s+دارد|\s+داره|\s|$)", "requires"),
            (r"(.+?)\s+(?:بدون)\s+(.+?)\s+(?:نمی‌شود|نمیشه|ممکن نیست|کار نمی‌کند)", "requires"),
            (r"(.+?)\s+(?:امکان|اجازه|فرصت)\s+(.+?)\s+(?:می‌دهد|میده|فراهم)", "enables"),
            # Comparison
            (r"(.+?)\s+(?:شبیه|مشابه|مانند|مثل|همانند)\s+(.+?)(?:\s|$|؟)", "similar_to"),
            (r"(.+?)\s+(?:برعکس|مخالف|ضد|متضاد|عکس)\s+(.+?)(?:\s|$|؟)", "opposite_of"),
            (r"(.+?)\s+(?:بهتر|برتر|قوی‌تر|سریع‌تر)\s+(?:از|نسبت به)\s+(.+?)(?:\s|$)", "better_than"),
            (r"(.+?)\s+(?:فرق|تفاوت|اختلاف)\s+(?:با|و)\s+(.+?)(?:\s|$)", "differs_from"),
            # Creation / Production
            (r"(.+?)\s+(?:تولید|ایجاد|ساخت|خلق)\s+(.+?)\s+(?:می‌کند|میکنه|کرد)", "produces"),
            (r"(.+?)\s+(?:توسط|به دست|ساخته)\s+(.+?)\s+(?:ساخته شد|ایجاد شد|بود)", "created_by"),
            (r"(.+?)\s+(?:اختراع|ابداع|کشف)\s+(.+?)(?:\s|$)", "invented"),
            # Purpose / Usage
            (r"(.+?)\s+(?:استفاده|کاربرد|کارایی)\s+(?:در|برای)\s+(.+)", "used_for"),
            (r"(.+?)\s+(?:برای|جهت|به منظور)\s+(.+?)\s+(?:طراحی|ساخته|استفاده)", "designed_for"),
            (r"(.+?)\s+(?:به کار|مورد استفاده)\s+(?:در|برای)\s+(.+)", "applied_in"),
            # Example / Instance
            (r"(.+?)\s+(?:مثال|نمونه|نمونه‌ای)\s+(?:از\s+)?(.+?)(?:\s|$|؟)", "example_of"),
            (r"(.+?)\s+(?:مانند|از جمله|مثلا)\s+(.+?)(?:\s|$|,|،)", "instance_of"),
            # Location / Belonging
            (r"(.+?)\s+(?:در|واقع در|مستقر در)\s+(.+?)\s+(?:قرار دارد|واقع است|هست)", "located_in"),
            (r"(.+?)\s+(?:متعلق به|مال|مربوط به)\s+(.+?)(?:\s+است|\s|$)", "belongs_to"),
            # Temporal
            (r"(.+?)\s+(?:قبل از|پیش از)\s+(.+?)(?:\s|$)", "before"),
            (r"(.+?)\s+(?:بعد از|پس از)\s+(.+?)(?:\s|$)", "after"),
        ]
        for pattern, rel_type in patterns:
            match = re.search(pattern, text)
            if match:
                subj = match.group(1).strip()
                obj = match.group(2).strip()
                if 2 < len(subj) < 50 and 2 < len(obj) < 50:
                    relations.append((subj, rel_type, obj))
        return relations

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


