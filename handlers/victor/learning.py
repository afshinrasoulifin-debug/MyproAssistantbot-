
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""Victor v7.0 TITAN — Adaptive Learning System (Phase 8)

Self-improving through interaction — learns from every conversation:
- CorrectionLearner: learns from user corrections and feedback
- UserModeler: builds per-user preference/topic profiles
- PatternMiner: extracts patterns from conversation history
- ConfidenceCalibrator: calibrates confidence based on past accuracy
- ActiveLearner: generates clarifying questions when uncertain
"""

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .nlp import PersianNLP
from .constants import BRAIN_DIR

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1. CORRECTION LEARNER — Learn from mistakes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Correction:
    original_query: str
    wrong_answer: str
    correct_answer: str
    timestamp: str
    topic: str = ""
    pattern_extracted: bool = False


class CorrectionLearner:
    """
    Learns from corrections:
    - Records what went wrong
    - Extracts patterns from corrections
    - Adjusts confidence for similar queries
    - Generates correction rules
    """

    def __init__(self, brain_dir: Path = None) -> None:
        self.brain_dir = brain_dir or BRAIN_DIR
        self.corrections: List[Correction] = []
        self.correction_patterns: Dict[str, str] = {}  # pattern → correct answer
        self.error_topics: Counter = Counter()
        self._load()

    def record(self, query: str, wrong: str, correct: str, topic: str = "") -> Correction:
        """Record a correction."""
        corr = Correction(
            original_query=query,
            wrong_answer=wrong,
            correct_answer=correct,
            timestamp=datetime.now(timezone.utc).isoformat(),
            topic=topic,
        )
        self.corrections.append(corr)
        self.error_topics[topic] += 1

        # Extract pattern
        keywords = PersianNLP.extract_keywords(query)
        if keywords:
            pattern_key = "|".join(sorted(keywords[:5]))
            self.correction_patterns[pattern_key] = correct
            corr.pattern_extracted = True

        self._save()
        return corr

    def check_correction(self, query: str) -> Optional[str]:
        """Check if there's a correction for this query pattern."""
        keywords = PersianNLP.extract_keywords(query)
        if not keywords:
            return None

        pattern_key = "|".join(sorted(keywords[:5]))
        if pattern_key in self.correction_patterns:
            return self.correction_patterns[pattern_key]

        # Fuzzy match against correction patterns
        query_set = set(keywords)
        for pattern, answer in self.correction_patterns.items():
            pattern_set = set(pattern.split("|"))
            overlap = len(query_set & pattern_set) / max(len(query_set | pattern_set), 1)
            if overlap > 0.6:
                return answer

        return None

    def get_weak_topics(self, top_k: int = 5) -> List[Tuple[str, int]]:
        """Get topics where Victor makes the most mistakes."""
        return self.error_topics.most_common(top_k)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_corrections": len(self.corrections),
            "patterns_learned": len(self.correction_patterns),
            "weak_topics": dict(self.error_topics.most_common(10)),
        }

    def _save(self) -> Any:
        path = self.brain_dir / "corrections_v2.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "corrections": [
                {
                    "query": c.original_query, "wrong": c.wrong_answer,
                    "correct": c.correct_answer, "ts": c.timestamp,
                    "topic": c.topic, "extracted": c.pattern_extracted,
                }
                for c in self.corrections[-500:]
            ],
            "patterns": self.correction_patterns,
            "error_topics": dict(self.error_topics),
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> Any:
        path = self.brain_dir / "corrections_v2.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data.get("corrections", []):
                self.corrections.append(Correction(
                    original_query=item["query"],
                    wrong_answer=item["wrong"],
                    correct_answer=item["correct"],
                    timestamp=item.get("ts", ""),
                    topic=item.get("topic", ""),
                    pattern_extracted=item.get("extracted", False),
                ))
            self.correction_patterns = data.get("patterns", {})
            self.error_topics = Counter(data.get("error_topics", {}))
        except HandlerError as e:
            logger.warning("Failed to load corrections: %s", e)


# ═══════════════════════════════════════════════════════════════════
# 2. USER MODELER — Per-user profiles
# ═══════════════════════════════════════════════════════════════════

@dataclass
class UserProfile:
    user_id: int
    topics: Counter = field(default_factory=Counter)
    sentiments: Counter = field(default_factory=Counter)
    formality: str = "neutral"
    avg_msg_length: float = 0.0
    total_messages: int = 0
    preferred_response_style: str = "balanced"  # brief, detailed, balanced
    active_hours: Counter = field(default_factory=Counter)
    keywords: Counter = field(default_factory=Counter)
    last_active: str = ""
    satisfaction_score: float = 0.5  # 0-1

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "topics": dict(self.topics),
            "sentiments": dict(self.sentiments),
            "formality": self.formality,
            "avg_msg_length": self.avg_msg_length,
            "total_messages": self.total_messages,
            "preferred_response_style": self.preferred_response_style,
            "active_hours": dict(self.active_hours),
            "keywords": dict(self.keywords.most_common(50)),
            "last_active": self.last_active,
            "satisfaction_score": self.satisfaction_score,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "UserProfile":
        prof = cls(user_id=data.get("user_id", 0))
        prof.topics = Counter(data.get("topics", {}))
        prof.sentiments = Counter(data.get("sentiments", {}))
        prof.formality = data.get("formality", "neutral")
        prof.avg_msg_length = data.get("avg_msg_length", 0.0)
        prof.total_messages = data.get("total_messages", 0)
        prof.preferred_response_style = data.get("preferred_response_style", "balanced")
        prof.active_hours = Counter(data.get("active_hours", {}))
        prof.keywords = Counter(data.get("keywords", {}))
        prof.last_active = data.get("last_active", "")
        prof.satisfaction_score = data.get("satisfaction_score", 0.5)
        return prof


class UserModeler:
    """
    Builds and maintains per-user profiles:
    - Topic preferences
    - Sentiment patterns
    - Formality level
    - Active hours
    - Response style preference
    """

    def __init__(self, brain_dir: Path = None) -> None:
        self.brain_dir = brain_dir or BRAIN_DIR
        self.profiles: Dict[int, UserProfile] = {}
        self._load()

    def update(self, user_id: int, text: str, topic: str = "") -> Any:
        """Update user profile from a message."""
        prof = self.profiles.setdefault(user_id, UserProfile(user_id=user_id))
        prof.total_messages += 1
        prof.last_active = datetime.now(timezone.utc).isoformat()

        # Topic
        if topic:
            prof.topics[topic] += 1

        # Keywords
        keywords = PersianNLP.extract_keywords(text)
        prof.keywords.update(keywords)

        # Sentiment
        sentiment = PersianNLP.simple_sentiment(text)
        prof.sentiments[sentiment] += 1

        # Formality
        formality = PersianNLP.detect_formality(text)
        prof.formality = formality

        # Message length (running average)
        tokens = PersianNLP.tokenize(text)
        n = prof.total_messages
        prof.avg_msg_length = ((n - 1) * prof.avg_msg_length + len(tokens)) / n

        # Active hour
        hour = str(datetime.now().hour)
        prof.active_hours[hour] += 1

        # Infer preferred response style from message length
        if prof.avg_msg_length > 20:
            prof.preferred_response_style = "detailed"
        elif prof.avg_msg_length < 5:
            prof.preferred_response_style = "brief"
        else:
            prof.preferred_response_style = "balanced"

        if prof.total_messages % 10 == 0:
            self._save()

    def get_profile(self, user_id: int) -> Optional[UserProfile]:
        return self.profiles.get(user_id)

    def get_top_topics(self, user_id: int, top_k: int = 5) -> List[Tuple[str, int]]:
        prof = self.profiles.get(user_id)
        if not prof:
            return []
        return prof.topics.most_common(top_k)

    def get_response_hints(self, user_id: int) -> Dict[str, str]:
        """Get hints for how to respond to this user."""
        prof = self.profiles.get(user_id)
        if not prof:
            return {"style": "balanced", "formality": "neutral"}
        return {
            "style": prof.preferred_response_style,
            "formality": prof.formality,
            "favorite_topics": [t for t, _ in prof.topics.most_common(3)],
        }

    def format_profile(self, user_id: int) -> str:
        prof = self.profiles.get(user_id)
        if not prof:
            return "👤 پروفایل کاربر یافت نشد."
        lines = [
            f"👤 *پروفایل کاربر {user_id}:*",
            f"  📊 پیام‌ها: {prof.total_messages}",
            f"  📝 میانگین طول: {prof.avg_msg_length:.0f} کلمه",
            f"  🎭 سبک: {prof.preferred_response_style}",
            f"  📋 رسمیت: {prof.formality}",
        ]
        top_topics = prof.topics.most_common(5)
        if top_topics:
            lines.append("  📚 موضوعات مورد علاقه:")
            for topic, count in top_topics:
                lines.append(f"    • {topic} ({count})")
        return "\n".join(lines)

    def _save(self) -> Any:
        path = self.brain_dir / "user_profiles.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {str(uid): prof.to_dict() for uid, prof in self.profiles.items()}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> Any:
        path = self.brain_dir / "user_profiles.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for uid_str, prof_data in data.items():
                uid = int(uid_str)
                self.profiles[uid] = UserProfile.from_dict(prof_data)
        except HandlerError as e:
            logger.warning("Failed to load user profiles: %s", e)


# ═══════════════════════════════════════════════════════════════════
# 3. PATTERN MINER — Extract patterns from conversations
# ═══════════════════════════════════════════════════════════════════

class PatternMiner:
    """
    Mines conversation logs for recurring patterns:
    - Frequently asked questions
    - Common topic sequences
    - Q&A pairs that should become rules
    - Conversation templates
    """

    def __init__(self, brain_dir: Path = None) -> None:
        self.brain_dir = brain_dir or BRAIN_DIR
        self.query_clusters: Dict[str, List[str]] = defaultdict(list)
        self.qa_pairs: List[Tuple[str, str, int]] = []  # (question, answer, count)
        self.topic_sequences: List[List[str]] = []

    def add_interaction(self, query: str, response: str, topic: str = "") -> None:
        """Record an interaction for mining."""
        # Normalize query
        norm_query = self._normalize_query(query)

        # Cluster similar queries
        added = False
        for cluster_key, members in self.query_clusters.items():
            if self._query_similarity(norm_query, cluster_key) > 0.7:
                members.append(query)
                added = True
                break
        if not added:
            self.query_clusters[norm_query] = [query]

        # Record QA pair
        self.qa_pairs.append((query, response, 1))

    def get_frequent_questions(self, min_count: int = 3, top_k: int = 10) -> List[Tuple[str, int]]:
        """Get frequently asked questions."""
        frequent = []
        for cluster_key, members in self.query_clusters.items():
            if len(members) >= min_count:
                # Use the most common form
                most_common = Counter(members).most_common(1)[0][0]
                frequent.append((most_common, len(members)))
        frequent.sort(key=lambda x: -x[1])
        return frequent[:top_k]

    def suggest_rules(self, min_occurrences: int = 3) -> List[Dict[str, str]]:
        """Suggest queries that should become automatic rules."""
        suggestions = []
        for cluster_key, members in self.query_clusters.items():
            if len(members) >= min_occurrences:
                # Find the most common answer for this cluster
                answers = Counter()
                for qa_q, qa_a, _ in self.qa_pairs:
                    if self._query_similarity(self._normalize_query(qa_q), cluster_key) > 0.7:
                        answers[qa_a[:200]] += 1
                if answers:
                    best_answer = answers.most_common(1)[0][0]
                    suggestions.append({
                        "pattern": cluster_key,
                        "response": best_answer,
                        "frequency": len(members),
                        "example": members[0],
                    })
        return suggestions

    def _normalize_query(self, query: str) -> str:
        """Normalize a query for clustering."""
        tokens = PersianNLP.tokenize(query)
        keywords = [t for t in tokens if t not in PersianNLP.STOPWORDS and len(t) > 1]
        return "|".join(sorted(keywords[:6]))

    def _query_similarity(self, norm_a: str, norm_b: str) -> float:
        """Similarity between two normalized queries."""
        a_set = set(norm_a.split("|"))
        b_set = set(norm_b.split("|"))
        if not a_set or not b_set:
            return 0.0
        return len(a_set & b_set) / len(a_set | b_set)


# ═══════════════════════════════════════════════════════════════════
# 4. CONFIDENCE CALIBRATOR — Know when you're uncertain
# ═══════════════════════════════════════════════════════════════════

class ConfidenceCalibrator:
    """
    Calibrates confidence scores based on historical accuracy:
    - Tracks prediction vs actual outcome
    - Adjusts confidence for topics with poor history
    - Identifies knowledge gaps
    """

    def __init__(self, brain_dir: Path = None) -> None:
        self.brain_dir = brain_dir or BRAIN_DIR
        self.topic_accuracy: Dict[str, List[bool]] = defaultdict(list)
        self.confidence_history: List[Tuple[float, bool]] = []  # (predicted_conf, was_correct)
        self._load()

    def record_outcome(self, topic: str, predicted_confidence: float, was_correct: bool) -> Any:
        """Record whether a prediction was correct."""
        self.topic_accuracy[topic].append(was_correct)
        self.confidence_history.append((predicted_confidence, was_correct))

        # Keep history manageable
        if len(self.confidence_history) > 1000:
            self.confidence_history = self.confidence_history[-500:]
        for t in self.topic_accuracy:
            if len(self.topic_accuracy[t]) > 200:
                self.topic_accuracy[t] = self.topic_accuracy[t][-100:]

        if len(self.confidence_history) % 20 == 0:
            self._save()

    def calibrate(self, raw_confidence: float, topic: str = "") -> float:
        """
        Adjust confidence based on historical accuracy.
        If Victor has been wrong often on this topic, reduce confidence.
        """
        if not self.confidence_history:
            return raw_confidence

        # Topic-specific adjustment
        topic_history = self.topic_accuracy.get(topic, [])
        if len(topic_history) >= 5:
            topic_accuracy = sum(topic_history) / len(topic_history)
            # Blend raw confidence with topic accuracy
            raw_confidence = raw_confidence * 0.6 + (topic_accuracy * 100) * 0.4

        # Global calibration: check if we tend to be overconfident
        if len(self.confidence_history) >= 10:
            # Group by confidence bucket
            buckets = defaultdict(list)
            for conf, correct in self.confidence_history:
                bucket = int(conf / 10) * 10  # 0, 10, 20, ..., 90
                buckets[bucket].append(correct)

            # Find the bucket for current confidence
            bucket = int(raw_confidence / 10) * 10
            if bucket in buckets and len(buckets[bucket]) >= 3:
                actual_accuracy = sum(buckets[bucket]) / len(buckets[bucket])
                expected = bucket / 100
                if expected > 0:
                    calibration_ratio = actual_accuracy / expected
                    raw_confidence *= min(calibration_ratio, 1.2)  # Don't inflate too much

        return max(5, min(95, raw_confidence))

    def get_knowledge_gaps(self, min_questions: int = 5) -> List[Tuple[str, float]]:
        """Find topics where accuracy is lowest."""
        gaps = []
        for topic, history in self.topic_accuracy.items():
            if len(history) >= min_questions:
                accuracy = sum(history) / len(history)
                if accuracy < 0.6:
                    gaps.append((topic, accuracy))
        return sorted(gaps, key=lambda x: x[1])

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.confidence_history)
        correct = sum(1 for _, c in self.confidence_history if c)
        return {
            "total_predictions": total,
            "overall_accuracy": correct / max(total, 1),
            "topics_tracked": len(self.topic_accuracy),
            "knowledge_gaps": self.get_knowledge_gaps(),
        }

    def _save(self) -> Any:
        path = self.brain_dir / "calibration.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "topic_accuracy": {t: h[-100:] for t, h in self.topic_accuracy.items()},
            "confidence_history": self.confidence_history[-500:],
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> Any:
        path = self.brain_dir / "calibration.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.topic_accuracy = defaultdict(list, {
                t: h for t, h in data.get("topic_accuracy", {}).items()
            })
            self.confidence_history = [
                (c, b) for c, b in data.get("confidence_history", [])
            ]
        except HandlerError as e:
            logger.warning("Failed to load calibration: %s", e)


# ═══════════════════════════════════════════════════════════════════
# 5. ACTIVE LEARNER — Ask clarifying questions
# ═══════════════════════════════════════════════════════════════════

class ActiveLearner:
    """
    When uncertain, generates intelligent clarifying questions.
    Uses:
    - Ambiguity detection
    - Missing info detection
    - Confidence-based question generation
    - Topic-aware question templates
    """

    QUESTION_TEMPLATES = {
        "ambiguous_topic": [
            "منظورت {topic_a} هست یا {topic_b}؟",
            "درباره کدوم {topic_a} صحبت می‌کنی؟",
        ],
        "missing_detail": [
            "می‌تونی بیشتر توضیح بدی درباره {detail}؟",
            "کدوم {detail} رو میگی دقیقاً؟",
        ],
        "confirm": [
            "یعنی {statement}؟ درسته؟",
            "اگه درست فهمیده باشم: {statement}. درسته؟",
        ],
        "low_confidence": [
            "مطمئن نیستم. منظورت اینه که {guess}؟",
            "شاید {guess}. ولی بهتره تأیید کنی.",
        ],
    }

    def __init__(self, memory_store: Any, confidence_calibrator: ConfidenceCalibrator) -> None:
        self.memory = memory_store
        self.calibrator = confidence_calibrator

    def should_ask(self, query: str, confidence: float, topic: str = "") -> bool:
        """Decide if we should ask a clarifying question."""
        calibrated = self.calibrator.calibrate(confidence, topic)

        # Ask if very uncertain
        if calibrated < 30:
            return True

        # Ask if ambiguous (multiple possible topics)
        ambiguous = self._detect_ambiguity(query)
        if ambiguous and calibrated < 60:
            return True

        return False

    def generate_question(self, query: str, confidence: float,
                          possible_answers: List[str] = None) -> Optional[str]:
        """Generate a clarifying question."""
        # Detect ambiguity
        ambiguous_topics = self._detect_ambiguity(query)
        if ambiguous_topics and len(ambiguous_topics) >= 2:
            template = self.QUESTION_TEMPLATES["ambiguous_topic"][0]
            return template.format(
                topic_a=ambiguous_topics[0],
                topic_b=ambiguous_topics[1]
            )

        # Missing detail
        missing = self._detect_missing_info(query)
        if missing:
            template = self.QUESTION_TEMPLATES["missing_detail"][0]
            return template.format(detail=missing)

        # Low confidence guess
        if possible_answers and confidence < 40:
            template = self.QUESTION_TEMPLATES["low_confidence"][0]
            return template.format(guess=possible_answers[0][:100])

        return None

    def _detect_ambiguity(self, query: str) -> List[str]:
        """Detect if query could match multiple topics."""
        keywords = PersianNLP.extract_keywords(query)
        if not keywords:
            return []

        matching_topics = Counter()
        for mem in self.memory.memories.values():
            overlap = len(set(keywords) & set(mem.keywords))
            if overlap > 0:
                matching_topics[mem.topic] += overlap

        # If multiple topics match similarly, it's ambiguous
        top = matching_topics.most_common(3)
        if len(top) >= 2 and top[0][1] - top[1][1] < 2:
            return [t for t, _ in top[:2]]
        return []

    def _detect_missing_info(self, query: str) -> Optional[str]:
        """Detect what info is missing to answer the query."""
        tokens = PersianNLP.tokenize(query)

        # Short queries often need more detail
        content_tokens = [t for t in tokens if t not in PersianNLP.STOPWORDS]
        if len(content_tokens) <= 2:
            return content_tokens[0] if content_tokens else None

        # Questions with pronouns need resolution
        pronouns = {"این", "آن", "اون", "همون", "اینا"}
        if set(tokens) & pronouns:
            return "موضوع مورد نظر"

        return None


