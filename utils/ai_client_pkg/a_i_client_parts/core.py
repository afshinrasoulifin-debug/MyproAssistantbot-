
"""
AIClient — Core mixin
"""
from __future__ import annotations

import logging

from sqlalchemy import select

try:
    from arki_project.database.connection import get_session
except Exception:
    get_session = None

try:
    from arki_project.database.models import ChatMessage as DBChatMessage
except Exception:
    DBChatMessage = None

logger = logging.getLogger(__name__)


class AIClientCoreMixin:
    """Methods related to core."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        model: str = "gemini-2.5-pro",  # v10.2: Pro default
        max_history: int = 500,  # v9.7.1: Deep context
        temperature: float = 0.7,
        max_tokens: int = 65536,  # v10.2: TITANIUM unlimited
        groq_api_key: str = "",
        openrouter_api_key: str = "",
    ) -> None:
        self._api_key = api_key
        # v3.3: Register keys with internal key manager for rotation
        if _INTERNAL_MGMT:
            try:
                km = get_key_manager()
                if api_key:
                    km.add_key("gemini", api_key, label="primary_gemini")
                if groq_api_key:
                    km.add_key("groq", groq_api_key, label="primary_groq")
                if openrouter_api_key:
                    km.add_key("openrouter", openrouter_api_key, label="primary_openrouter")
                km.load_from_env()  # Load any additional keys from env
                logger.info("v3.3: Internal key manager initialized with %s",
                           {p: km.get_provider_status(p)["total_keys"]
                            for p in ["gemini", "groq", "openrouter"]})
            except AIProviderError as e:
                logger.debug("Key manager init: %s (non-fatal)", e)
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_history = max_history
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._groq_api_key = groq_api_key
        self._openrouter_api_key = openrouter_api_key
        # In-memory caches.
        self._history: Dict[int, List[ChatMessage]] = defaultdict(list)
        self._loaded_users: set[int] = set()
        self._config_cache: dict[int, tuple[float, dict]] = {}  # user_id → (timestamp, config)
        self._config_cache_ttl: float = 300.0  # 5 minutes
        # Use centralized HTTP pool (shared across all modules)
        # No duplicate clients — saves memory and connections
        from arki_project.utils.http_pool import get_client as _get_pool_client
        self._get_pool_client = _get_pool_client
        # v9.5: Circuit breaker per provider
        self._breakers = {
            'gemini': CircuitBreaker('gemini', failure_threshold=5, recovery_timeout=60.0),
            'groq': CircuitBreaker('groq', failure_threshold=5, recovery_timeout=60.0),
            'openrouter': CircuitBreaker('openrouter', failure_threshold=3, recovery_timeout=120.0),
        }

    async def _append(self, user_id: int, role: str, content: str) -> None:
        self._history[user_id].append(ChatMessage(role=role, content=content))
        # Trim in-memory (keep max_history entries).
        if len(self._history[user_id]) > self._max_history * 2:
            self._history[user_id] = self._history[user_id][
                -self._max_history:
            ]
        # Persist to DB.
        async with get_session() as session:
            session.add(
                DBChatMessage(
                    user_id=user_id, role=role, content=content,
                ),
            )
            await session.flush()

    async def _ensure_loaded(self, user_id: int) -> None:
        if user_id in self._loaded_users:
            return
        async with get_session() as session:
            result = await session.execute(
                select(DBChatMessage)
                .where(DBChatMessage.user_id == user_id)
                .order_by(DBChatMessage.created_at.desc())
                .limit(self._max_history),
            )
            rows = result.scalars().all()
        for row in reversed(rows):
            self._history[user_id].append(
                ChatMessage(role=row.role, content=row.content),
            )
        self._loaded_users.add(user_id)

    async def close(self) -> None:
        """Close HTTP clients and release resources."""
        from arki_project.utils.http_pool import close_all
        await close_all()
        self._breakers.clear()  # v9.8.7: was _circuit_breakers (wrong name)

    def evict_stale_users(self, max_age_seconds: int = 3600) -> int:
        """Remove in-memory history for users inactive for > max_age_seconds.
        Also enforces MAX_CACHED_USERS hard limit.
        Returns the number of evicted users. Call periodically from a background task."""
        now = time.time()
        evicted = 0

        # 1. Evict stale users (inactive > max_age_seconds)
        stale = [
            uid for uid, msgs in self._history.items()
            if msgs and (now - msgs[-1].timestamp) > max_age_seconds
        ]
        for uid in stale:
            del self._history[uid]
            self._loaded_users.discard(uid)
            evicted += 1

        # 2. Enforce hard limit — evict oldest if over MAX_CACHED_USERS
        if len(self._history) > MAX_CACHED_USERS:
            sorted_users = sorted(
                self._history.items(),
                key=lambda x: x[1][-1].timestamp if x[1] else 0,
            )
            excess = len(self._history) - MAX_CACHED_USERS
            for uid, _ in sorted_users[:excess]:
                del self._history[uid]
                self._loaded_users.discard(uid)
                evicted += 1

        return evicted

    def get_last_transparency(self) -> "Optional[Dict[str, Any]]":
        """Get transparency info about the last model call.
        Returns dict with actual_model, was_fallback, etc. or None."""
        return self._last_transparency



