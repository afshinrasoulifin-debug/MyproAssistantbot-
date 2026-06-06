
from __future__ import annotations
"""
ContextSyncMemory — Combines context synchronization + persistent memory.
"""
import logging, time
from typing import Any, Dict, List



logger = logging.getLogger(__name__)

class ContextSyncMemory:
    """Synchronized context with persistent memory across sessions."""

    def __init__(self) -> None:
        self._contexts: Dict[int, List[Dict]] = {}
        self._memory: Dict[int, Dict[str, Any]] = {}

    def add_message(self, user_id: int, message: Dict) -> None:
        if user_id not in self._contexts:
            self._contexts[user_id] = []
        self._contexts[user_id].append({**message, "timestamp": time.time()})

    def get_context(self, user_id: int, limit: int = 200) -> List[Dict]:
        return (self._contexts.get(user_id) or [])[-limit:]

    def remember(self, user_id: int, key: str, value: Any) -> Any:
        if user_id not in self._memory:
            self._memory[user_id] = {}
        self._memory[user_id][key] = value

    def recall(self, user_id: int, key: str) -> Any:
        return (self._memory.get(user_id) or {}).get(key)

    def get_full_state(self, user_id: int) -> Dict:
        return {
            "context": self.get_context(user_id),
            "memory": self._memory.get(user_id, {}),
        }


