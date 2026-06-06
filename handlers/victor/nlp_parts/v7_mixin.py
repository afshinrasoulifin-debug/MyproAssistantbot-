
"""PersianNLP v7 TITAN additions — enterprise NLP features."""
from __future__ import annotations


class PersianNLPv7Mixin:
    """v7 TITAN NLP: enterprise features, advanced pipelines."""

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



