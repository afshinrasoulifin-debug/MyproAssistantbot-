
from __future__ import annotations
"""Victor v7.0 TITAN — Dialogue State Tracker (multi-turn)"""

from typing import Any, Dict, List


# ═══════════════════════════════════════════════════════════════════
# 9. DIALOGUE STATE TRACKER — v7 Multi-Turn Mastery
# ═══════════════════════════════════════════════════════════════════

class DialogueStateTracker:
    """
    v7: Tracks conversation state for multi-turn dialogue.
    Handles follow-up questions, coreference, topic continuity.
    """

    def __init__(self) -> None:
        self._states: Dict[int, Dict[str, Any]] = {}  # user_id → state

    def _get_state(self, user_id: int) -> Dict[str, Any]:
        if user_id not in self._states:
            self._states[user_id] = {
                "current_topic": "",
                "topic_history": [],
                "active_entities": {},
                "last_intent": "",
                "pending_clarification": False,
                "turn_count": 0,
                "follow_up_context": "",
            }
        return self._states[user_id]

    def update(self, user_id: int, text: str, intent: str = "",
               entities: Dict[str, List[str]] = None, topic: str = "") -> Any:
        """Update dialogue state with new turn."""
        state = self._get_state(user_id)
        state["turn_count"] += 1

        # Update topic
        if topic:
            if state["current_topic"] and state["current_topic"] != topic:
                state["topic_history"].append(state["current_topic"])
                state["topic_history"] = state["topic_history"][-10:]
            state["current_topic"] = topic

        # Update entities
        if entities:
            for ent_type, ent_values in entities.items():
                if ent_values:
                    state["active_entities"][ent_type] = ent_values

        # Update intent
        if intent:
            state["last_intent"] = intent

        # Detect follow-up
        follow_up_markers = {"همین", "اون", "بعدش", "ادامه", "بیشتر", "دوباره",
                             "also", "more", "continue", "again", "what about"}
        text_words = set(text.lower().split())
        if text_words & follow_up_markers:
            state["follow_up_context"] = state["current_topic"]

    def is_follow_up(self, user_id: int, text: str) -> bool:
        """Check if this is a follow-up question."""
        state = self._get_state(user_id)
        follow_up_markers = {"همین", "اون", "بعدش", "ادامه", "بیشتر", "دوباره",
                             "چی دیگه", "also", "more", "and", "what about"}
        text_words = set(text.lower().split())
        return bool(text_words & follow_up_markers) or (
            state["turn_count"] > 0 and len(text.split()) < 5
        )

    def get_context_enrichment(self, user_id: int, text: str) -> str:
        """Enrich a query with context from dialogue state."""
        state = self._get_state(user_id)
        if not state["current_topic"]:
            return text

        # If this is a short follow-up, add topic context
        if len(text.split()) < 5 and state["current_topic"]:
            return f"{state['current_topic']} {text}"
        return text

    def get_state_summary(self, user_id: int) -> str:
        """Get dialogue state summary."""
        state = self._get_state(user_id)
        lines = [
            f"🔄 *وضعیت مکالمه:*",
            f"  موضوع فعلی: {state['current_topic'] or '—'}",
            f"  آخرین نیت: {state['last_intent'] or '—'}",
            f"  تعداد نوبت: {state['turn_count']}",
        ]
        if state["active_entities"]:
            ent_str = ", ".join(f"{k}: {v[0]}" for k, v in state["active_entities"].items() if v)
            lines.append(f"  موجودیت‌ها: {ent_str}")
        if state["topic_history"]:
            lines.append(f"  تاریخچه: {' → '.join(state['topic_history'][-5:])}")
        return "\n".join(lines)


