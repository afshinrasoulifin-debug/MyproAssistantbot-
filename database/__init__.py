
"""
tg_bot/database — Async SQLAlchemy database layer.

Key exports:
    init_db       — Initialize engine + create tables
    close_db      — Dispose connection pool
    get_session   — Async context manager for DB sessions
    Base          — Declarative base for models
"""

try:
    from arki_project.database.connection import init_db, close_db, get_session
except (ImportError, ModuleNotFoundError):
    try:
        from database.connection import init_db, close_db, get_session
    except (ImportError, ModuleNotFoundError):
        init_db = None  # type: ignore
        close_db = None  # type: ignore
        get_session = None  # type: ignore

__all__ = ["init_db", "close_db", "get_session"]


