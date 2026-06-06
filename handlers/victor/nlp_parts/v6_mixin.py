
"""PersianNLP v6 additions — advanced analysis, sentiment, keyword extraction."""
from __future__ import annotations


class PersianNLPv6Mixin:
    """v6 NLP additions: advanced analysis, sentiment, keywords."""

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



