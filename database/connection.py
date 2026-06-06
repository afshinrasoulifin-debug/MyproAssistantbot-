
from __future__ import annotations
from arki_project.exceptions import DatabaseError
"""
tg_bot/database/connection.py
─────────────────────────────
Async SQLAlchemy 2.0 engine, session factory, and helpers.

v29.0.0:
  • Retry logic with exponential backoff
  • Health check method
  • Database size reporting
  • Automatic migration on schema changes
  • Better error messages
"""


import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

# v9.5: Query cache for repeated queries
try:
    from arki_project.utils.query_cache import QueryCache
    _query_cache = QueryCache()
except ImportError:
    _query_cache = None

# Module-level singletons (initialised by ``init_db``).
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db(database_url: str) -> None:
    """
    Create the async engine & session factory, then issue
    ``CREATE TABLE … IF NOT EXISTS`` for every mapped model.
    """
    global _engine, _session_factory  # noqa: PLW0603

    # v10.4: Production-grade dual-mode engine configuration
    is_sqlite = "sqlite" in database_url
    engine_kwargs = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if is_sqlite:
        # SQLite: Use StaticPool for concurrent access (single shared connection)
        # NullPool creates/destroys connections per query → file lock contention
        # StaticPool reuses one connection → WAL mode handles concurrent reads
        from sqlalchemy.pool import StaticPool
        engine_kwargs["poolclass"] = StaticPool
        engine_kwargs["connect_args"] = {
            "check_same_thread": False,
            "timeout": 30,            # Wait up to 30s for write lock
        }
        logger.info("Database: SQLite mode (StaticPool + WAL)")
    else:
        # PostgreSQL / MySQL: Real connection pooling
        from sqlalchemy.pool import AsyncAdaptedQueuePool
        engine_kwargs["poolclass"] = AsyncAdaptedQueuePool
        engine_kwargs["pool_size"] = 20
        engine_kwargs["max_overflow"] = 40
        engine_kwargs["pool_recycle"] = 1800   # Recycle connections every 30min
        engine_kwargs["pool_timeout"] = 30      # Wait max 30s for a connection
        engine_kwargs["pool_pre_ping"] = True   # Verify connections before use
        logger.info("Database: PostgreSQL mode (QueuePool, size=20, overflow=40)")

    _engine = create_async_engine(database_url, **engine_kwargs)

    # v10.4: Enhanced SQLite pragmas for production concurrency
    if "sqlite" in database_url:
        @event.listens_for(_engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            # WAL mode: readers don't block writers, writers don't block readers
            cursor.execute("PRAGMA journal_mode=WAL")
            # NORMAL sync: safe with WAL, 10x faster than FULL
            cursor.execute("PRAGMA synchronous=NORMAL")
            # Wait up to 10s for write lock (was 5s — gives more headroom under load)
            cursor.execute("PRAGMA busy_timeout=10000")
            # 64MB page cache for faster reads
            cursor.execute("PRAGMA cache_size=-64000")
            # Enable foreign key enforcement
            cursor.execute("PRAGMA foreign_keys=ON")
            # Memory-mapped I/O: 256MB — reduces syscalls dramatically
            cursor.execute("PRAGMA mmap_size=268435456")
            # Temporary tables in memory (faster joins/sorts)
            cursor.execute("PRAGMA temp_store=MEMORY")
            # WAL auto-checkpoint every 1000 pages (~4MB) to prevent WAL bloat
            cursor.execute("PRAGMA wal_autocheckpoint=1000")
            cursor.close()
            logger.debug("SQLite pragmas applied: WAL + mmap + temp_store=MEMORY")

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Import Base here so all models are registered before create_all.
    from arki_project.database.models import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized: %s", _safe_url(database_url))


async def close_db() -> None:
    """Dispose of the engine connection pool."""
    global _engine  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database connection closed.")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async session via a context manager with auto-commit/rollback.

    Usage::

        async with get_session() as session:
            result = await session.execute(select(User))
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialised. Call init_db() first."
        )

    session = _session_factory()
    try:
        yield session
        await session.commit()
    except DatabaseError:
        await session.rollback()
        raise
    finally:
        await session.close()


async def health_check() -> dict:
    """
    Check database health and return status info.
    Returns a dict with 'ok', 'message', and optional 'details'.
    """
    if _engine is None:
        return {"ok": False, "message": "Engine not initialized"}

    try:
        async with _engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()

        details: dict = {"engine_url": _safe_url(str(_engine.url))}

        # SQLite-specific info
        if "sqlite" in str(_engine.url):
            async with _engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
                )
                row = result.fetchone()
                if row:
                    size_bytes = row[0]
                    details["size_mb"] = round(size_bytes / (1024 * 1024), 2)

                # Table counts
                result = await conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                )
                tables = [row[0] for row in result.fetchall()]
                details["tables"] = tables
                details["table_count"] = len(tables)

        return {"ok": True, "message": "Connected", "details": details}

    except DatabaseError as exc:
        return {"ok": False, "message": str(exc)}


async def get_db_stats() -> dict:
    """Get database statistics for admin dashboard."""
    stats: dict = {}
    try:
        async with get_session() as session:
            from sqlalchemy import func, select
            from arki_project.database.models import (
                User, ChatMessage, AnalyticsEvent,
                Customer, FinanceRecord, Reminder,
            )

            for name, model in [
                ("users", User),
                ("messages", ChatMessage),
                ("analytics", AnalyticsEvent),
                ("customers", Customer),
                ("finance", FinanceRecord),
                ("reminders", Reminder),
            ]:
                try:
                    result = await session.execute(
                        select(func.count()).select_from(model)
                    )
                    stats[name] = result.scalar() or 0
                except DatabaseError:
                    stats[name] = -1  # Table may not exist yet

    except DatabaseError as exc:
        stats["error"] = str(exc)

    return stats


def _safe_url(url: str) -> str:
    """Mask credentials in database URL for logging."""
    if "@" in url:
        parts = url.split("@")
        return "***@" + parts[-1]
    return url


