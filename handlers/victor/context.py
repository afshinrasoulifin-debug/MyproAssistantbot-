
from __future__ import annotations
"""Victor v7.0 TITAN — Context window, caching, tracking, learning"""

import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .models import Turn
from .nlp import PersianNLP

class ContextWindowV6:
    """
    v6 Short-term memory: keeps last N conversation turns.
    Topic tracking, intent history, turn summarization.
    """

    def __init__(self, max_turns: int = 50) -> None:
        self.max_turns = max_turns
        self.turns: List[Turn] = []
        self._topic_history: List[str] = []
        self._intent_counts: Counter = Counter()

    def add(self, role: str, text: str, intent: str = "", confidence: float = 0.0,
            entities: Dict[str, List[str]] = None) -> Turn:
        turn = Turn(role=role, text=text, intent=intent, confidence=confidence,
                    entities=entities or {})
        self.turns.append(turn)
        if intent:
            self._intent_counts[intent] += 1
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
        return turn

    def get_recent(self, n: int = 10) -> List[Turn]:
        return self.turns[-n:]

    def get_context_text(self, n: int = 5) -> str:
        recent = self.get_recent(n)
        return "\n".join(
            f"{'👤' if t.role == 'user' else '🤖'} {t.text}" for t in recent
        )

    def get_dominant_intent(self) -> Optional[str]:
        if not self._intent_counts:
            return None
        return self._intent_counts.most_common(1)[0][0]

    def search(self, keyword: str) -> List[Turn]:
        kw = keyword.lower()
        return [t for t in self.turns if kw in t.text.lower()]

    def clear(self) -> Any:
        self.turns.clear()
        self._topic_history.clear()
        self._intent_counts.clear()

    def to_dict(self) -> Dict:
        return {"turns": [{"role": t.role, "text": t.text, "timestamp": t.timestamp,
                           "intent": t.intent, "confidence": t.confidence}
                          for t in self.turns],
                "topic_history": self._topic_history}

    @classmethod
    def from_dict(cls, data: Dict, max_turns: int = 50) -> "ContextWindowV6":
        cw = cls(max_turns=max_turns)
        for td in data.get("turns", []):
            turn = Turn(**{k: td[k] for k in ("role", "text", "timestamp", "intent", "confidence") if k in td})
            cw.turns.append(turn)
            if turn.intent:
                cw._intent_counts[turn.intent] += 1
        cw._topic_history = data.get("topic_history", [])
        return cw

class SmartCache:
    """v6: LRU cache with TTL for frequently asked questions."""

    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600) -> None:
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_count: Counter = Counter()

    def _normalize_key(self, text: str) -> str:
        key = re.sub(r"\s+", " ", text.strip().lower())
        key = re.sub(r"[\u064B-\u065F]", "", key)  # Remove Arabic diacritics
        return key

    def get(self, query: str) -> Optional[Any]:
        key = self._normalize_key(query)
        if key in self._cache:
            value, ts = self._cache[key]
            if time.time() - ts < self.ttl:
                self._access_count[key] += 1
                return value
            else:
                del self._cache[key]
        return None

    def put(self, query: str, result: Any) -> Any:
        key = self._normalize_key(query)
        if len(self._cache) >= self.max_size:
            if self._access_count:
                least = self._access_count.most_common()[-1][0]
                self._cache.pop(least, None)
                del self._access_count[least]
        self._cache[key] = (result, time.time())
        self._access_count[key] = 1

    def invalidate(self, query: str = None) -> Any:
        if query:
            self._cache.pop(self._normalize_key(query), None)
        else:
            self._cache.clear()
            self._access_count.clear()

    def stats(self) -> Dict:
        return {"size": len(self._cache), "max_size": self.max_size,
                "hit_count": sum(self._access_count.values()),
                "top_queries": self._access_count.most_common(5)}

class ConversationTracker:
    """v6: Track user behavior patterns for smarter responses."""

    def __init__(self) -> None:
        self.users: Dict[int, Dict] = {}

    def track(self, user_id: int, intent: str, topic: str = "",
              response_length: int = 0, was_helpful: bool = True) -> Any:
        if user_id not in self.users:
            self.users[user_id] = {
                "first_seen": time.time(), "interaction_count": 0,
                "intent_counts": Counter(), "topics": Counter(),
                "preferred_length": [], "satisfaction_rate": [],
            }
        p = self.users[user_id]
        p["interaction_count"] += 1
        p["last_seen"] = time.time()
        if intent:
            p["intent_counts"][intent] += 1
        if topic:
            p["topics"][topic] += 1
        if response_length:
            p["preferred_length"].append(response_length)
            p["preferred_length"] = p["preferred_length"][-50:]
        p["satisfaction_rate"].append(1.0 if was_helpful else 0.0)
        p["satisfaction_rate"] = p["satisfaction_rate"][-100:]

    def get_profile(self, user_id: int) -> Dict[str, Any]:
        if user_id not in self.users:
            return {"status": "new_user"}
        p = self.users[user_id]
        avg_len = sum(p["preferred_length"]) / len(p["preferred_length"]) if p["preferred_length"] else 200
        sat = sum(p["satisfaction_rate"]) / len(p["satisfaction_rate"]) if p["satisfaction_rate"] else 0.5
        return {
            "interaction_count": p["interaction_count"],
            "top_intents": p["intent_counts"].most_common(3),
            "top_topics": p["topics"].most_common(5),
            "preferred_response_length": int(avg_len),
            "satisfaction_rate": round(sat, 2),
            "is_power_user": p["interaction_count"] > 50,
        }

class LearningEngineV6:
    """v6: Auto-learns from conversations — fact extraction, Q&A, knowledge gaps."""

    def __init__(self, memory_store: Any) -> None:
        self.memory = memory_store
        self._knowledge_gaps: List[str] = []

    def learn_from_turn(self, user_text: str, bot_response: str,
                        intent: str = "", confidence: float = 0.0) -> Any:
        if confidence < 0.3:
            self._knowledge_gaps.append(user_text)
            return

        # Extract facts from user statements
        facts = self._extract_facts(user_text)
        for fact_content, fact_topic in facts:
            self.memory.store(
                content=fact_content, topic=fact_topic,
                memory_type="learned_fact",
                keywords=PersianNLP.extract_keywords(fact_content),
            )

        # Learn Q&A patterns for high-confidence interactions
        if intent in ("question", "teach", "ask") and confidence > 0.6:
            self.memory.store(
                content=f"Q: {user_text} → A: {bot_response}",
                topic=intent, memory_type="qa_pair",
                keywords=PersianNLP.extract_keywords(user_text),
            )

    def _extract_facts(self, text: str) -> List[Tuple[str, str]]:
        facts = []
        patterns = [
            r"(.+?)\s+(?:هست|است|هستند|بود|میشه|میشود)\s+(.+)",
            r"(.+?)\s*=\s*(.+)",
            r"(.+?)\s+یعنی\s+(.+)",
            r"(.+?)\s+برابر\s+(?:است\s+)?(?:با\s+)?(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                subj = match.group(1).strip()
                pred = match.group(2).strip()
                if len(subj) > 2 and len(pred) > 2:
                    facts.append((f"{subj}: {pred}", subj))
        return facts

    def get_knowledge_gaps(self) -> List[str]:
        return self._knowledge_gaps[-20:]


