
from __future__ import annotations
"""
sessions — Persistent Browser Session Management
══════════════════════════════════════════════════
Manages encrypted, provider-specific browser sessions for stealth operations.
"""
try:
    from .session_store import SessionStore, get_session_store
except ImportError:
    SessionStore = None  # type: ignore
    get_session_store = None  # type: ignore


