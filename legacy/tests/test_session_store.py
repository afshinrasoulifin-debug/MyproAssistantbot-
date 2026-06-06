
"""
Tests for sessions/session_store.py — Enterprise Session Persistence Engine
"""
import os
import sys
import tempfile
import time
import pytest

# Path setup
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sessions.session_store import (
    SessionStore, BrowserSession, SessionCookie, SessionState,
    ProviderType, PROVIDER_DEFAULTS, get_session_store,
)


# ═══════════════════════════════════════════════════════════
# SessionCookie Tests
# ═══════════════════════════════════════════════════════════

class TestSessionCookie:
    def test_create_cookie(self):
        c = SessionCookie(name="sid", value="abc123", domain=".google.com")
        assert c.name == "sid"
        assert c.value == "abc123"
        assert c.domain == ".google.com"
        assert c.secure is True
        assert c.path == "/"

    def test_cookie_not_expired(self):
        c = SessionCookie(name="t", value="v", domain="x.com", expires=0)
        assert c.is_expired is False

    def test_cookie_expired(self):
        c = SessionCookie(name="t", value="v", domain="x.com", expires=1.0)
        assert c.is_expired is True

    def test_cookie_future(self):
        c = SessionCookie(name="t", value="v", domain="x.com", expires=time.time() + 9999)
        assert c.is_expired is False

    def test_cookie_roundtrip(self):
        c = SessionCookie(name="a", value="b", domain="c.com", secure=False, http_only=True)
        d = c.to_dict()
        c2 = SessionCookie.from_dict(d)
        assert c2.name == "a"
        assert c2.value == "b"
        assert c2.secure is False
        assert c2.http_only is True

    def test_cookie_to_dict_keys(self):
        c = SessionCookie(name="k", value="v", domain="d.com")
        d = c.to_dict()
        assert "name" in d
        assert "value" in d
        assert "domain" in d
        assert "httpOnly" in d
        assert "sameSite" in d


# ═══════════════════════════════════════════════════════════
# BrowserSession Tests
# ═══════════════════════════════════════════════════════════

class TestBrowserSession:
    def test_create_session(self):
        s = BrowserSession(session_id="test1", provider="google")
        assert s.session_id == "test1"
        assert s.provider == "google"
        assert s.state == SessionState.CREATED
        assert s.use_count == 0

    def test_session_not_expired(self):
        s = BrowserSession(session_id="t", provider="p", ttl_seconds=3600)
        assert s.is_expired is False

    def test_session_expired(self):
        s = BrowserSession(
            session_id="t", provider="p",
            created_at=time.time() - 100000, ttl_seconds=3600,
        )
        assert s.is_expired is True

    def test_session_health(self):
        s = BrowserSession(session_id="t", provider="p", state=SessionState.ACTIVE)
        assert s.is_healthy is True
        s.state = SessionState.CORRUPTED
        assert s.is_healthy is False

    def test_session_touch(self):
        s = BrowserSession(session_id="t", provider="p")
        before = s.use_count
        s.touch()
        assert s.use_count == before + 1

    def test_session_record_error(self):
        s = BrowserSession(session_id="t", provider="p", state=SessionState.ACTIVE, max_errors=3)
        s.record_error()
        assert s.error_count == 1
        assert s.state == SessionState.ACTIVE
        s.record_error()
        s.record_error()
        assert s.state == SessionState.CORRUPTED

    def test_session_needs_refresh(self):
        s = BrowserSession(
            session_id="t", provider="p",
            refresh_interval=10,
            created_at=time.time() - 20,
        )
        assert s.needs_refresh is True

    def test_session_active_cookies(self):
        cookies = [
            SessionCookie(name="a", value="1", domain="x.com", expires=0),
            SessionCookie(name="b", value="2", domain="x.com", expires=1.0),  # expired
        ]
        s = BrowserSession(session_id="t", provider="p", cookies=cookies)
        assert len(s.active_cookies) == 1
        assert s.active_cookies[0].name == "a"

    def test_session_roundtrip(self):
        s = BrowserSession(
            session_id="abc", provider="google",
            state=SessionState.ACTIVE,
            user_agent="Mozilla/5.0",
            tokens={"key": "val"},
        )
        d = s.to_dict()
        s2 = BrowserSession.from_dict(d)
        assert s2.session_id == "abc"
        assert s2.provider == "google"
        assert s2.state == SessionState.ACTIVE
        assert s2.tokens == {"key": "val"}


# ═══════════════════════════════════════════════════════════
# SessionStore Tests
# ═══════════════════════════════════════════════════════════

class TestSessionStore:
    @pytest.fixture
    def tmp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    @pytest.fixture
    def store(self, tmp_dir):
        return SessionStore(sessions_dir=os.path.join(tmp_dir, "sessions"), auto_cleanup=False)

    @pytest.mark.asyncio
    async def test_start_stop(self, store):
        await store.start()
        assert store._running is True
        await store.stop()
        assert store._running is False

    @pytest.mark.asyncio
    async def test_create_session(self, store):
        await store.start()
        s = await store.create_session(
            provider="google",
            cookies=[{"name": "sid", "value": "123", "domain": ".google.com"}],
            user_agent="Test/1.0",
        )
        assert s.provider == "google"
        assert len(s.cookies) == 1
        assert s.state == SessionState.ACTIVE
        await store.stop()

    @pytest.mark.asyncio
    async def test_get_session(self, store):
        await store.start()
        await store.create_session(provider="groq")
        s = await store.get_session("groq")
        assert s is not None
        assert s.provider == "groq"
        await store.stop()

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, store):
        await store.start()
        s = await store.get_session("nonexistent")
        assert s is None
        await store.stop()

    @pytest.mark.asyncio
    async def test_update_session(self, store):
        await store.start()
        s = await store.create_session(provider="google")
        updated = await store.update_session(s.session_id, tokens={"key": "new_key"})
        assert updated is not None
        assert updated.tokens["key"] == "new_key"
        await store.stop()

    @pytest.mark.asyncio
    async def test_revoke_session(self, store):
        await store.start()
        s = await store.create_session(provider="google")
        assert await store.revoke_session(s.session_id) is True
        assert await store.get_session("google") is None
        await store.stop()

    @pytest.mark.asyncio
    async def test_revoke_nonexistent(self, store):
        await store.start()
        assert await store.revoke_session("fake_id") is False
        await store.stop()

    @pytest.mark.asyncio
    async def test_multiple_sessions_per_provider(self, store):
        await store.start()
        s1 = await store.create_session(provider="google")
        s2 = await store.create_session(provider="google")
        all_s = await store.get_all_sessions("google")
        assert len(all_s) == 2
        await store.stop()

    @pytest.mark.asyncio
    async def test_pool_limit_eviction(self, tmp_dir):
        store = SessionStore(
            sessions_dir=os.path.join(tmp_dir, "sessions"),
            max_sessions_per_provider=2,
            auto_cleanup=False,
        )
        await store.start()
        s1 = await store.create_session(provider="test")
        s2 = await store.create_session(provider="test")
        s3 = await store.create_session(provider="test")  # Should evict s1
        all_s = await store.get_all_sessions("test")
        assert len(all_s) == 2
        ids = {s.session_id for s in all_s}
        assert s1.session_id not in ids  # s1 was evicted
        await store.stop()

    @pytest.mark.asyncio
    async def test_persistence_roundtrip(self, tmp_dir):
        dir_path = os.path.join(tmp_dir, "sessions")

        # Create and persist
        store1 = SessionStore(sessions_dir=dir_path, auto_cleanup=False)
        await store1.start()
        await store1.create_session(
            provider="google",
            cookies=[{"name": "x", "value": "y", "domain": "g.com"}],
            user_agent="UA/1.0",
        )
        await store1.stop()

        # Reload from disk
        store2 = SessionStore(sessions_dir=dir_path, auto_cleanup=False)
        await store2.start()
        s = await store2.get_session("google")
        assert s is not None
        assert s.provider == "google"
        assert len(s.cookies) == 1
        assert s.cookies[0].name == "x"
        await store2.stop()

    @pytest.mark.asyncio
    async def test_stats(self, store):
        await store.start()
        stats = store.get_stats()
        assert "version" in stats
        assert "total_sessions" in stats
        assert "providers" in stats
        assert stats["running"] is True
        await store.stop()

    @pytest.mark.asyncio
    async def test_health(self, store):
        await store.start()
        health = store.get_health()
        assert health["status"] in ("healthy", "degraded")
        assert "total" in health
        await store.stop()

    @pytest.mark.asyncio
    async def test_rotate_session(self, store):
        await store.start()
        await store.create_session(provider="test")
        await store.create_session(provider="test")
        rotated = await store.rotate_session("test")
        assert rotated is not None
        await store.stop()

    @pytest.mark.asyncio
    async def test_fingerprint_validation(self, store):
        await store.start()
        s = await store.create_session(
            provider="test",
            user_agent="UA/1.0",
            fingerprint_hash="abc123",
        )
        assert store.validate_fingerprint(s, "UA/1.0") is False  # hash mismatch (different algo)
        s2 = BrowserSession(session_id="t", provider="p", fingerprint_hash="")
        assert store.validate_fingerprint(s2, "any") is True  # no fingerprint = always valid
        await store.stop()


# ═══════════════════════════════════════════════════════════
# Provider Defaults Tests
# ═══════════════════════════════════════════════════════════

class TestProviderDefaults:
    def test_all_providers_have_defaults(self):
        for provider in ["google", "groq", "openrouter", "openai", "anthropic", "deepseek"]:
            assert provider in PROVIDER_DEFAULTS

    def test_defaults_have_required_keys(self):
        for name, defaults in PROVIDER_DEFAULTS.items():
            assert "console_url" in defaults, f"{name} missing console_url"
            assert "ttl_seconds" in defaults, f"{name} missing ttl_seconds"
            assert "refresh_interval" in defaults, f"{name} missing refresh_interval"
            assert defaults["ttl_seconds"] > 0

    def test_google_defaults(self):
        g = PROVIDER_DEFAULTS["google"]
        assert "aistudio.google.com" in g["console_url"]
        assert g["ttl_seconds"] == 86400 * 7


# ═══════════════════════════════════════════════════════════
# Singleton Tests
# ═══════════════════════════════════════════════════════════

class TestSingleton:
    def test_get_session_store_returns_same(self):
        import sessions.session_store as mod
        mod._store = None  # Reset
        s1 = get_session_store()
        s2 = get_session_store()
        assert s1 is s2
        mod._store = None  # Cleanup

    def test_session_state_enum(self):
        assert SessionState.ACTIVE.value == "active"
        assert SessionState.EXPIRED.value == "expired"

    def test_provider_type_enum(self):
        assert ProviderType.GOOGLE.value == "google"
        assert ProviderType.CUSTOM.value == "custom"


