
"""SessionNode — Session-aware node with eviction."""
import time
from arki_project.infrastructure.nodes.ai_node import AINode



MAX_SESSIONS = 10_000
SESSION_TTL = 3600  # 1 hour of inactivity


class SessionNode(AINode):
    def __init__(self) -> None:
        super().__init__("session")
        self._sessions: dict = {}
        self._last_access: dict = {}

    def get_session(self, user_id: int) -> dict:
        now = time.time()
        self._last_access[user_id] = now

        if user_id not in self._sessions:
            self._sessions[user_id] = {"messages": [], "context": {}}
            # Evict stale sessions if over limit
            if len(self._sessions) > MAX_SESSIONS:
                self._evict_stale()

        return self._sessions[user_id]

    def _evict_stale(self) -> int:
        """Remove sessions inactive for > SESSION_TTL seconds."""
        cutoff = time.time() - SESSION_TTL
        stale = [uid for uid, ts in self._last_access.items() if ts < cutoff]
        for uid in stale:
            self._sessions.pop(uid, None)
            self._last_access.pop(uid, None)
        return len(stale)


