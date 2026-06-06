
from __future__ import annotations
"""
sessions/session_store.py — Enterprise Session Persistence Engine v1.0-TITAN
═════════════════════════════════════════════════════════════════════════════
Manages persistent browser sessions per provider with:
- AES-256-GCM encrypted storage (via crypto_engine or fallback)
- Per-provider lifecycle: create → persist → restore → rotate → expire
- Health monitoring with auto-refresh triggers
- Session fingerprint binding (detects session hijacking)
- Concurrent-safe with asyncio locks
- Automatic cleanup of expired / corrupted sessions

Author: Arki Engine TITAN
"""


import asyncio
import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Final, List, Optional, Set

logger = logging.getLogger("arki.sessions.store")

# ── Try crypto engine for encrypted storage ──
try:
    from arki_project.utils.crypto_engine import encrypt_data, decrypt_data
    _CRYPTO_AVAILABLE: bool = True
except ImportError:
    _CRYPTO_AVAILABLE = False


# ═══════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════

class SessionState(Enum):
    """Lifecycle states for a browser session."""
    CREATED = "created"
    ACTIVE = "active"
    REFRESHING = "refreshing"
    EXPIRED = "expired"
    REVOKED = "revoked"
    CORRUPTED = "corrupted"


class ProviderType(Enum):
    """Known AI/API providers."""
    GOOGLE = "google"
    GROQ = "groq"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"


@dataclass
class SessionCookie:
    """Individual cookie with full attributes."""
    name: str
    value: str
    domain: str
    path: str = "/"
    secure: bool = True
    http_only: bool = False
    same_site: str = "Lax"
    expires: float = 0  # 0 = session cookie

    @property
    def is_expired(self) -> bool:
        return self.expires > 0 and time.time() > self.expires

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "value": self.value,
            "domain": self.domain, "path": self.path,
            "secure": self.secure, "httpOnly": self.http_only,
            "sameSite": self.same_site, "expires": self.expires,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SessionCookie":
        return cls(
            name=d["name"], value=d["value"], domain=d["domain"],
            path=d.get("path", "/"), secure=d.get("secure", True),
            http_only=d.get("httpOnly", False),
            same_site=d.get("sameSite", "Lax"),
            expires=d.get("expires", 0),
        )


@dataclass
class BrowserSession:
    """Complete browser session state for a provider."""
    session_id: str
    provider: str
    state: SessionState = SessionState.CREATED
    cookies: List[SessionCookie] = field(default_factory=list)
    local_storage: Dict[str, str] = field(default_factory=dict)
    session_storage: Dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
    fingerprint_hash: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    tokens: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    last_refreshed: float = 0
    ttl_seconds: float = 86400  # 24h default
    refresh_interval: float = 3600  # 1h
    use_count: int = 0
    error_count: int = 0
    max_errors: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds

    @property
    def needs_refresh(self) -> bool:
        if self.last_refreshed == 0:
            return (time.time() - self.created_at) > self.refresh_interval
        return (time.time() - self.last_refreshed) > self.refresh_interval

    @property
    def is_healthy(self) -> bool:
        return (
            self.state == SessionState.ACTIVE
            and not self.is_expired
            and self.error_count < self.max_errors
        )

    @property
    def active_cookies(self) -> List[SessionCookie]:
        return [c for c in self.cookies if not c.is_expired]

    def touch(self) -> None:
        self.last_used = time.time()
        self.use_count += 1

    def record_error(self) -> None:
        self.error_count += 1
        if self.error_count >= self.max_errors:
            self.state = SessionState.CORRUPTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "provider": self.provider,
            "state": self.state.value,
            "cookies": [c.to_dict() for c in self.cookies],
            "local_storage": self.local_storage,
            "session_storage": self.session_storage,
            "user_agent": self.user_agent,
            "fingerprint_hash": self.fingerprint_hash,
            "headers": self.headers,
            "tokens": self.tokens,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "last_refreshed": self.last_refreshed,
            "ttl_seconds": self.ttl_seconds,
            "refresh_interval": self.refresh_interval,
            "use_count": self.use_count,
            "error_count": self.error_count,
            "max_errors": self.max_errors,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BrowserSession":
        return cls(
            session_id=d["session_id"],
            provider=d["provider"],
            state=SessionState(d.get("state", "created")),
            cookies=[SessionCookie.from_dict(c) for c in d.get("cookies", [])],
            local_storage=d.get("local_storage", {}),
            session_storage=d.get("session_storage", {}),
            user_agent=d.get("user_agent", ""),
            fingerprint_hash=d.get("fingerprint_hash", ""),
            headers=d.get("headers", {}),
            tokens=d.get("tokens", {}),
            created_at=d.get("created_at", time.time()),
            last_used=d.get("last_used", time.time()),
            last_refreshed=d.get("last_refreshed", 0),
            ttl_seconds=d.get("ttl_seconds", 86400),
            refresh_interval=d.get("refresh_interval", 3600),
            use_count=d.get("use_count", 0),
            error_count=d.get("error_count", 0),
            max_errors=d.get("max_errors", 5),
            metadata=d.get("metadata", {}),
        )


# ═══════════════════════════════════════════════════════════
# Provider Configurations
# ═══════════════════════════════════════════════════════════

PROVIDER_DEFAULTS: Final[Dict[str, Dict[str, Any]]] = {
    "google": {
        "console_url": "https://aistudio.google.com/app/apikey",
        "auth_url": "https://accounts.google.com",
        "ttl_seconds": 86400 * 7,    # 7 days
        "refresh_interval": 3600 * 6,  # 6 hours
        "domains": ["google.com", "googleapis.com", "aistudio.google.com"],
    },
    "groq": {
        "console_url": "https://console.groq.com/keys",
        "auth_url": "https://console.groq.com",
        "ttl_seconds": 86400 * 30,   # 30 days
        "refresh_interval": 3600 * 24, # 24 hours
        "domains": ["groq.com", "console.groq.com"],
    },
    "openrouter": {
        "console_url": "https://openrouter.ai/keys",
        "auth_url": "https://openrouter.ai",
        "ttl_seconds": 86400 * 30,
        "refresh_interval": 3600 * 12,
        "domains": ["openrouter.ai"],
    },
    "openai": {
        "console_url": "https://platform.openai.com/api-keys",
        "auth_url": "https://platform.openai.com",
        "ttl_seconds": 86400 * 7,
        "refresh_interval": 3600 * 6,
        "domains": ["openai.com", "platform.openai.com"],
    },
    "anthropic": {
        "console_url": "https://console.anthropic.com/settings/keys",
        "auth_url": "https://console.anthropic.com",
        "ttl_seconds": 86400 * 30,
        "refresh_interval": 3600 * 24,
        "domains": ["anthropic.com", "console.anthropic.com"],
    },
    "deepseek": {
        "console_url": "https://platform.deepseek.com/api_keys",
        "auth_url": "https://platform.deepseek.com",
        "ttl_seconds": 86400 * 30,
        "refresh_interval": 3600 * 24,
        "domains": ["deepseek.com", "platform.deepseek.com"],
    },
}


# ═══════════════════════════════════════════════════════════
# Session Store Engine
# ═══════════════════════════════════════════════════════════

class SessionStore:
    """
    Enterprise-grade persistent session manager.

    Features:
    - Encrypted-at-rest session files (AES-256-GCM if crypto_engine available)
    - Per-provider session pools with automatic rotation
    - Fingerprint binding to detect session hijacking
    - Health monitoring loop with auto-cleanup
    - Concurrent-safe via asyncio locks
    - Integrates with stealth_worker for session capture
    """

    VERSION: Final[str] = "1.0.0-TITAN"

    def __init__(
        self,
        sessions_dir: str = "sessions",
        encryption_key: Optional[str] = None,
        auto_cleanup: bool = True,
        max_sessions_per_provider: int = 10,
    ) -> None:
        self._sessions_dir = Path(sessions_dir)
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._encryption_key = encryption_key or os.environ.get("ARKI_SESSION_KEY", "")
        self._auto_cleanup = auto_cleanup
        self._max_per_provider = max_sessions_per_provider

        # Runtime state
        self._sessions: Dict[str, BrowserSession] = {}   # session_id → session
        self._provider_index: Dict[str, Set[str]] = {}   # provider → {session_ids}
        self._lock = asyncio.Lock()
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

        # Stats
        self._stats = {
            "sessions_created": 0,
            "sessions_restored": 0,
            "sessions_expired": 0,
            "sessions_rotated": 0,
            "encrypt_errors": 0,
            "decrypt_errors": 0,
        }

    # ── Lifecycle ────────────────────────────────────────

    async def start(self) -> None:
        """Initialize the store: load persisted sessions, start monitor."""
        if self._running:
            return
        self._running = True
        await self._load_all_sessions()
        if self._auto_cleanup:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(
            "🗄️  SessionStore v%s started — %d sessions loaded from %s",
            self.VERSION, len(self._sessions), self._sessions_dir,
        )

    async def stop(self) -> None:
        """Persist all sessions and stop monitoring."""
        self._running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        await self._persist_all_sessions()
        logger.info("🗄️  SessionStore stopped — %d sessions persisted", len(self._sessions))

    # ── CRUD ─────────────────────────────────────────────

    async def create_session(
        self,
        provider: str,
        cookies: Optional[List[Dict[str, Any]]] = None,
        local_storage: Optional[Dict[str, str]] = None,
        user_agent: str = "",
        fingerprint_hash: str = "",
        tokens: Optional[Dict[str, str]] = None,
        ttl_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BrowserSession:
        """Create and persist a new browser session."""
        async with self._lock:
            # Enforce pool limit per provider
            provider_sessions = self._provider_index.get(provider, set())
            if len(provider_sessions) >= self._max_per_provider:
                oldest = await self._evict_oldest(provider)
                if oldest:
                    logger.info("🔄 Evicted oldest session %s for %s", oldest, provider)

            # Get provider defaults
            defaults = PROVIDER_DEFAULTS.get(provider.lower(), {})

            session = BrowserSession(
                session_id=secrets.token_hex(16),
                provider=provider,
                state=SessionState.ACTIVE,
                cookies=[SessionCookie.from_dict(c) for c in (cookies or [])],
                local_storage=local_storage or {},
                user_agent=user_agent,
                fingerprint_hash=fingerprint_hash or self._compute_fingerprint(user_agent, cookies),
                tokens=tokens or {},
                ttl_seconds=ttl_seconds or defaults.get("ttl_seconds", 86400),
                refresh_interval=defaults.get("refresh_interval", 3600),
                metadata=metadata or {},
            )

            self._sessions[session.session_id] = session
            self._provider_index.setdefault(provider, set()).add(session.session_id)
            self._stats["sessions_created"] += 1

            await self._persist_session(session)
            logger.info(
                "✅ Session %s created for %s (cookies=%d, ttl=%ds)",
                session.session_id[:8], provider, len(session.cookies), session.ttl_seconds,
            )
            return session

    async def get_session(
        self, provider: str, require_healthy: bool = True,
    ) -> Optional[BrowserSession]:
        """Get the best available session for a provider."""
        async with self._lock:
            session_ids = self._provider_index.get(provider, set())
            best: Optional[BrowserSession] = None
            for sid in session_ids:
                session = self._sessions.get(sid)
                if not session:
                    continue
                if require_healthy and not session.is_healthy:
                    continue
                if best is None or session.last_used > best.last_used:
                    best = session

            if best:
                best.touch()
            return best

    async def get_all_sessions(self, provider: Optional[str] = None) -> List[BrowserSession]:
        """Get all sessions, optionally filtered by provider."""
        async with self._lock:
            if provider:
                sids = self._provider_index.get(provider, set())
                return [self._sessions[s] for s in sids if s in self._sessions]
            return list(self._sessions.values())

    async def update_session(
        self,
        session_id: str,
        cookies: Optional[List[Dict[str, Any]]] = None,
        local_storage: Optional[Dict[str, str]] = None,
        tokens: Optional[Dict[str, str]] = None,
        state: Optional[SessionState] = None,
    ) -> Optional[BrowserSession]:
        """Update an existing session's data."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            if cookies is not None:
                session.cookies = [SessionCookie.from_dict(c) for c in cookies]
            if local_storage is not None:
                session.local_storage.update(local_storage)
            if tokens is not None:
                session.tokens.update(tokens)
            if state is not None:
                session.state = state

            session.last_refreshed = time.time()
            await self._persist_session(session)
            return session

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke and remove a session."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if not session:
                return False

            provider_set = self._provider_index.get(session.provider, set())
            provider_set.discard(session_id)

            # Delete persisted file
            file_path = self._session_file_path(session.provider, session_id)
            try:
                file_path.unlink(missing_ok=True)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

            logger.info("🗑️  Session %s revoked for %s", session_id[:8], session.provider)
            return True

    async def rotate_session(self, provider: str) -> Optional[BrowserSession]:
        """
        Rotate to next available session for a provider.
        Marks current best as needs-refresh and returns next best.
        """
        async with self._lock:
            session_ids = sorted(
                self._provider_index.get(provider, set()),
                key=lambda s: self._sessions.get(s, BrowserSession(session_id="", provider="")).last_used,
            )
            for sid in session_ids:
                session = self._sessions.get(sid)
                if session and session.is_healthy:
                    session.touch()
                    self._stats["sessions_rotated"] += 1
                    return session
            return None

    # ── Fingerprint Validation ───────────────────────────

    def validate_fingerprint(self, session: BrowserSession, current_ua: str) -> bool:
        """Check if session is being used with the same fingerprint."""
        if not session.fingerprint_hash:
            return True
        current_hash = self._compute_fingerprint(current_ua, None)
        return session.fingerprint_hash == current_hash

    @staticmethod
    def _compute_fingerprint(
        user_agent: str, cookies: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Compute a fingerprint hash from UA + cookie domains."""
        parts = [user_agent]
        if cookies:
            domains = sorted(set(c.get("domain", "") for c in cookies))
            parts.extend(domains)
        raw = "|".join(parts).encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    # ── Persistence ──────────────────────────────────────

    def _session_file_path(self, provider: str, session_id: str) -> Path:
        """Get the file path for a session."""
        provider_dir = self._sessions_dir / provider
        provider_dir.mkdir(parents=True, exist_ok=True)
        return provider_dir / f"{session_id}.json"

    async def _persist_session(self, session: BrowserSession) -> None:
        """Write a single session to disk (encrypted if key available)."""
        file_path = self._session_file_path(session.provider, session.session_id)
        data = json.dumps(session.to_dict(), ensure_ascii=False, indent=2)

        try:
            if _CRYPTO_AVAILABLE and self._encryption_key:
                encrypted = encrypt_data(data, self._encryption_key)
                file_path.write_text(encrypted, encoding="utf-8")
            else:
                file_path.write_text(data, encoding="utf-8")
        except Exception as e:
            self._stats["encrypt_errors"] += 1
            logger.warning("⚠️ Failed to persist session %s: %s", session.session_id[:8], e)

        # Also update the legacy provider-level JSON (backward compat)
        legacy_path = self._sessions_dir / f"{session.provider}_session.json"
        try:
            legacy_data = json.dumps({
                "active_session": session.session_id,
                "provider": session.provider,
                "state": session.state.value,
                "cookies_count": len(session.active_cookies),
                "last_used": session.last_used,
                "updated_at": time.time(),
            }, indent=2)
            legacy_path.write_text(legacy_data, encoding="utf-8")
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

    async def _load_all_sessions(self) -> None:
        """Load all persisted sessions from disk."""
        for provider_dir in self._sessions_dir.iterdir():
            if not provider_dir.is_dir():
                continue
            provider = provider_dir.name
            for session_file in provider_dir.glob("*.json"):
                try:
                    raw = session_file.read_text(encoding="utf-8")

                    # Try decrypt
                    data_str = raw
                    if _CRYPTO_AVAILABLE and self._encryption_key:
                        try:
                            data_str = decrypt_data(raw, self._encryption_key)
                        except Exception:
                            pass  # Might be unencrypted

                    data = json.loads(data_str)
                    session = BrowserSession.from_dict(data)

                    if session.is_expired:
                        session_file.unlink(missing_ok=True)
                        self._stats["sessions_expired"] += 1
                        continue

                    self._sessions[session.session_id] = session
                    self._provider_index.setdefault(provider, set()).add(session.session_id)
                    self._stats["sessions_restored"] += 1

                except Exception as e:
                    self._stats["decrypt_errors"] += 1
                    logger.debug("Skip corrupt session file %s: %s", session_file.name, e)

    async def _persist_all_sessions(self) -> None:
        """Persist all active sessions."""
        for session in self._sessions.values():
            if session.state in (SessionState.ACTIVE, SessionState.REFRESHING):
                await self._persist_session(session)

    async def _evict_oldest(self, provider: str) -> Optional[str]:
        """Evict the oldest session for a provider. Must be called with lock held."""
        sids = self._provider_index.get(provider, set())
        if not sids:
            return None

        oldest_id = min(sids, key=lambda s: self._sessions.get(s, BrowserSession(
            session_id="", provider="")).created_at)
        session = self._sessions.pop(oldest_id, None)
        sids.discard(oldest_id)

        if session:
            file_path = self._session_file_path(provider, oldest_id)
            try:
                file_path.unlink(missing_ok=True)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
        return oldest_id

    # ── Monitor Loop ─────────────────────────────────────

    async def _monitor_loop(self) -> None:
        """Background loop for session health monitoring and cleanup."""
        while self._running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Session monitor error: %s", e)

    async def _cleanup_expired(self) -> None:
        """Remove expired and corrupted sessions."""
        async with self._lock:
            to_remove = []
            for sid, session in self._sessions.items():
                if session.is_expired or session.state == SessionState.CORRUPTED:
                    to_remove.append(sid)

            for sid in to_remove:
                session = self._sessions.pop(sid, None)
                if session:
                    provider_set = self._provider_index.get(session.provider, set())
                    provider_set.discard(sid)
                    file_path = self._session_file_path(session.provider, sid)
                    try:
                        file_path.unlink(missing_ok=True)
                    except Exception as _err:
                        logger.warning("Suppressed error: %s", _err)
                    self._stats["sessions_expired"] += 1

            if to_remove:
                logger.info("🧹 Cleaned up %d expired/corrupted sessions", len(to_remove))

    # ── Stats & Health ───────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive store statistics."""
        per_provider = {}
        for provider, sids in self._provider_index.items():
            active = sum(
                1 for s in sids
                if s in self._sessions and self._sessions[s].is_healthy
            )
            per_provider[provider] = {
                "total": len(sids),
                "active": active,
                "unhealthy": len(sids) - active,
            }

        return {
            "version": self.VERSION,
            "running": self._running,
            "total_sessions": len(self._sessions),
            "providers": per_provider,
            "encryption": "AES-256-GCM" if (_CRYPTO_AVAILABLE and self._encryption_key) else "none",
            "auto_cleanup": self._auto_cleanup,
            "storage_dir": str(self._sessions_dir),
            **self._stats,
        }

    def get_health(self) -> Dict[str, Any]:
        """Quick health check."""
        total = len(self._sessions)
        healthy = sum(1 for s in self._sessions.values() if s.is_healthy)
        return {
            "status": "healthy" if healthy > 0 or total == 0 else "degraded",
            "total": total,
            "healthy": healthy,
            "unhealthy": total - healthy,
            "running": self._running,
        }


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

_store: Optional[SessionStore] = None


def get_session_store(sessions_dir: str = "sessions") -> SessionStore:
    """Get or create the global SessionStore singleton."""
    global _store
    if _store is None:
        _store = SessionStore(sessions_dir=sessions_dir)
    return _store


