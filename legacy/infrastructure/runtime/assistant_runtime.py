
from __future__ import annotations
"""AssistantRuntime — Runtime for AI assistant sessions."""
import logging, time
from typing import Dict, List, Any



logger = logging.getLogger(__name__)

class AssistantSession:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self.messages: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}
        self.created_at = time.time()

class AssistantRuntime:
    """Manage persistent assistant sessions with context."""

    def __init__(self, max_sessions: int = 100000) -> None:
        self._sessions: Dict[int, AssistantSession] = {}
        self._max = max_sessions

    def get_session(self, user_id: int) -> AssistantSession:
        if user_id not in self._sessions:
            self._sessions[user_id] = AssistantSession(user_id)
        return self._sessions[user_id]

    def clear_session(self, user_id: int) -> None:
        self._sessions.pop(user_id, None)

    @property
    def active_count(self) -> Any: return len(self._sessions)


