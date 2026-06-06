
from __future__ import annotations
"""
tg_bot/utils/persistent_memory.py — Persistent Memory Store v9.4
Stores user memories in SQLite (via SQLAlchemy) instead of in-memory dicts.
Survives restarts.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


class PersistentMemory:
    """Persistent user memory backed by database."""

    def __init__(self, session_factory: Optional[Any]=None) -> None:
        self._session_factory = session_factory
        self._cache: Dict[int, List[Dict]] = {}  # In-memory cache

    async def store(self, user_id: int, key: str, value: str, metadata: Dict = None) -> Any:
        """Store a memory item for a user."""
        entry = {
            "key": key,
            "value": value,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if user_id not in self._cache:
            self._cache[user_id] = []
        self._cache[user_id].append(entry)

        # Persist to DB if available
        if self._session_factory:
            try:
                async with self._session_factory() as session:
                    from arki_project.database.models import SemanticMemory
                    mem = SemanticMemory(
                        user_id=user_id,
                        content=value,
                        metadata_json=json.dumps(metadata or {}),
                    )
                    session.add(mem)
                    await session.commit()
            except Exception as e:
                logger.warning("Failed to persist memory: %s", e)

    async def recall(self, user_id: int, query: str = "", limit: int = 10) -> List[Dict]:
        """Recall memories for a user."""
        memories = self._cache.get(user_id, [])
        if query:
            # Simple keyword matching
            keywords = query.lower().split()
            scored = []
            for m in memories:
                score = sum(1 for kw in keywords if kw in m["value"].lower())
                if score > 0:
                    scored.append((score, m))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [m for _, m in scored[:limit]]
        return memories[-limit:]

    async def forget(self, user_id: int, key: str = None) -> Any:
        """Remove memories for a user."""
        if key:
            self._cache[user_id] = [
                m for m in self._cache.get(user_id, [])
                if m["key"] != key
            ]
        else:
            self._cache.pop(user_id, None)

    async def load_from_db(self, user_id: int) -> Any:
        """Load memories from database into cache."""
        if self._session_factory:
            try:
                async with self._session_factory() as session:
                    from sqlalchemy import select
                    from arki_project.database.models import SemanticMemory
                    result = await session.execute(
                        select(SemanticMemory).where(
                            SemanticMemory.user_id == user_id
                        ).order_by(SemanticMemory.id.desc()).limit(100)
                    )
                    rows = result.scalars().all()
                    self._cache[user_id] = [
                        {
                            "key": f"mem_{r.id}",
                            "value": r.content,
                            "metadata": json.loads(r.metadata_json) if r.metadata_json else {},
                            "timestamp": str(r.created_at) if hasattr(r, 'created_at') else "",
                        }
                        for r in rows
                    ]
            except Exception as e:
                logger.warning("Failed to load memories from DB: %s", e)


_store: Optional[PersistentMemory] = None

def get_persistent_memory(session_factory: Optional[Any]=None) -> PersistentMemory:
    global _store
    if _store is None:
        _store = PersistentMemory(session_factory)
    return _store


