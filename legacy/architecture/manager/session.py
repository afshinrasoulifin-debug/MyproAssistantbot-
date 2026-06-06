
from __future__ import annotations
"""
architecture.manager.session — SessionManager, TokenManager
════════════════════════════════════════════════════════════
User session and token management with TTL and refresh.
Covers: session-manager, token-manager, client
"""
import logging, secrets, time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional



logger = logging.getLogger(__name__)

@dataclass
class Session:
    session_id: str
    user_id: int
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    ttl_s: float = 3600
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > self.ttl_s

    def touch(self) -> None:
        self.last_active = time.time()

class SessionManager:
    """User session management with TTL and cleanup."""
    def __init__(self, default_ttl: float = 3600) -> None:
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[int, str] = {}
        self._default_ttl = default_ttl

    def create(self, user_id: int, ttl_s: Optional[float] = None) -> Session:
        sid = secrets.token_hex(16)
        session = Session(session_id=sid, user_id=user_id, ttl_s=ttl_s or self._default_ttl)
        self._sessions[sid] = session
        self._user_sessions[user_id] = sid
        return session

    def get(self, session_id: str) -> Optional[Session]:
        session = self._sessions.get(session_id)
        if session and not session.is_expired:
            session.touch()
            return session
        elif session:
            self._sessions.pop(session_id, None)
        return None

    def get_by_user(self, user_id: int) -> Optional[Session]:
        sid = self._user_sessions.get(user_id)
        if sid:
            return self.get(sid)
        return None

    def destroy(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session:
            self._user_sessions.pop(session.user_id, None)
            return True
        return False

    def cleanup_expired(self) -> int:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired]
        for sid in expired:
            self.destroy(sid)
        return len(expired)

    @property
    def stats(self) -> Dict[str, Any]:
        active = sum(1 for s in self._sessions.values() if not s.is_expired)
        return {"total": len(self._sessions), "active": active}

@dataclass
class Token:
    token: str
    user_id: int
    scope: str = "default"
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0

    @property
    def is_valid(self) -> bool:
        return self.expires_at == 0 or time.time() < self.expires_at

class TokenManager:
    """Token generation, validation, and lifecycle."""
    def __init__(self) -> None:
        self._tokens: Dict[str, Token] = {}

    def generate(self, user_id: int, scope: str = "default", ttl_s: float = 86400) -> Token:
        raw = secrets.token_hex(32)
        token = Token(token=raw, user_id=user_id, scope=scope,
                      expires_at=time.time() + ttl_s if ttl_s else 0)
        self._tokens[raw] = token
        return token

    def validate(self, token_str: str) -> Optional[Token]:
        token = self._tokens.get(token_str)
        if token and token.is_valid:
            return token
        elif token:
            self._tokens.pop(token_str, None)
        return None

    def revoke(self, token_str: str) -> bool:
        return self._tokens.pop(token_str, None) is not None

    def revoke_user(self, user_id: int) -> int:
        to_remove = [t for t, tk in self._tokens.items() if tk.user_id == user_id]
        for t in to_remove:
            self._tokens.pop(t)
        return len(to_remove)


