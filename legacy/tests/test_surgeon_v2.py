
"""
Tests for orchestration/surgeon.py — AI Global Surgeon v2.0-TITAN
"""
import os
import sys
import pytest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from orchestration.surgeon import (
    SurgeonAgent, TokenPoolManager, APIToken, TokenState,
    ProviderState, ProviderHealth, surgeon as singleton_surgeon,
)


# ═══════════════════════════════════════════════════════════
# APIToken Tests
# ═══════════════════════════════════════════════════════════

class TestAPIToken:
    def test_create_token(self):
        t = APIToken(token_id="t1", provider="google", key="sk-abcdefghijklmn1234")
        assert t.token_id == "t1"
        assert t.provider == "google"
        assert t.state == TokenState.ACTIVE
        assert t.is_usable is True

    def test_masked_key(self):
        t = APIToken(token_id="t1", provider="g", key="sk-abcdefghijklmn1234")
        masked = t.masked_key
        assert masked.startswith("sk-a")
        assert masked.endswith("1234")
        assert "..." in masked

    def test_masked_short_key(self):
        t = APIToken(token_id="t1", provider="g", key="short")
        assert t.masked_key == "***"

    def test_key_hash_auto(self):
        t = APIToken(token_id="t1", provider="g", key="test_key")
        assert len(t.key_hash) == 12

    def test_record_success(self):
        t = APIToken(token_id="t1", provider="g", key="k")
        t.record_success(tokens_used=100, cost=0.01)
        assert t.total_requests == 1
        assert t.daily_requests == 1
        assert t.total_tokens_used == 100
        assert t.cost_usd == 0.01

    def test_record_error(self):
        t = APIToken(token_id="t1", provider="g", key="k")
        t.record_error(is_rate_limit=False)
        assert t.total_errors == 1
        assert t.state == TokenState.ACTIVE

    def test_rate_limit(self):
        t = APIToken(token_id="t1", provider="g", key="k")
        t.record_error(is_rate_limit=True, retry_after=120)
        assert t.state == TokenState.RATE_LIMITED
        assert t.is_usable is False

    def test_error_rate(self):
        t = APIToken(token_id="t1", provider="g", key="k")
        t.record_success()
        t.record_success()
        t.record_error()
        assert t.error_rate == pytest.approx(1 / 3, rel=0.01)

    def test_quota_utilization(self):
        t = APIToken(
            token_id="t1", provider="g", key="k",
            quota_total=1000, quota_remaining=200,
        )
        assert t.quota_utilization == pytest.approx(0.8, rel=0.01)

    def test_quota_none(self):
        t = APIToken(token_id="t1", provider="g", key="k")
        assert t.quota_utilization is None

    def test_reset_daily(self):
        t = APIToken(token_id="t1", provider="g", key="k")
        t.daily_requests = 500
        t.state = TokenState.RATE_LIMITED
        t.reset_daily()
        assert t.daily_requests == 0
        assert t.state == TokenState.ACTIVE

    def test_to_dict(self):
        t = APIToken(token_id="t1", provider="g", key="test_key_12345678")
        d = t.to_dict()
        assert "token_id" in d
        assert "provider" in d
        assert "masked_key" in d
        assert "is_usable" in d
        assert "key" not in d  # Should not expose raw key


# ═══════════════════════════════════════════════════════════
# ProviderState Tests
# ═══════════════════════════════════════════════════════════

class TestProviderState:
    def test_create_provider(self):
        p = ProviderState(name="google")
        assert p.name == "google"
        assert p.health == ProviderHealth.UNKNOWN
        assert len(p.tokens) == 0

    def test_usable_tokens(self):
        t1 = APIToken(token_id="1", provider="g", key="k1", state=TokenState.ACTIVE)
        t2 = APIToken(token_id="2", provider="g", key="k2", state=TokenState.EXHAUSTED)
        p = ProviderState(name="g", tokens=[t1, t2])
        assert len(p.usable_tokens) == 1

    def test_get_best_token(self):
        t1 = APIToken(token_id="1", provider="g", key="k1")
        t1.daily_requests = 100
        t2 = APIToken(token_id="2", provider="g", key="k2")
        t2.daily_requests = 10
        p = ProviderState(name="g", tokens=[t1, t2])
        best = p.get_best_token()
        assert best.token_id == "2"  # Least daily usage

    def test_get_best_token_empty(self):
        p = ProviderState(name="g")
        assert p.get_best_token() is None

    def test_get_weighted_token(self):
        t1 = APIToken(token_id="1", provider="g", key="k1", weight=1.0)
        p = ProviderState(name="g", tokens=[t1])
        assert p.get_weighted_token() is not None

    def test_total_daily_requests(self):
        t1 = APIToken(token_id="1", provider="g", key="k1")
        t1.daily_requests = 50
        t2 = APIToken(token_id="2", provider="g", key="k2")
        t2.daily_requests = 30
        p = ProviderState(name="g", tokens=[t1, t2])
        assert p.total_daily_requests == 80


# ═══════════════════════════════════════════════════════════
# TokenPoolManager Tests
# ═══════════════════════════════════════════════════════════

class TestTokenPoolManager:
    @pytest.fixture
    def pool(self, tmp_path):
        return TokenPoolManager(persist_path=str(tmp_path / "pool.json"))

    @pytest.mark.asyncio
    async def test_add_token(self, pool):
        token = await pool.add_token("google", "sk-test-key-123456")
        assert token.provider == "google"
        assert token.state == TokenState.ACTIVE

    @pytest.mark.asyncio
    async def test_add_duplicate(self, pool):
        t1 = await pool.add_token("google", "sk-test-key-123456")
        t2 = await pool.add_token("google", "sk-test-key-123456")
        assert t1.key_hash == t2.key_hash  # Same token returned

    @pytest.mark.asyncio
    async def test_get_token(self, pool):
        await pool.add_token("google", "key1")
        token = await pool.get_token("google")
        assert token is not None
        assert token.provider == "google"

    @pytest.mark.asyncio
    async def test_get_token_nonexistent(self, pool):
        token = await pool.get_token("nonexistent")
        assert token is None

    @pytest.mark.asyncio
    async def test_remove_token(self, pool):
        t = await pool.add_token("google", "key-to-remove")
        result = await pool.remove_token("google", t.key_hash)
        assert result is True
        assert await pool.get_token("google") is None

    @pytest.mark.asyncio
    async def test_record_success(self, pool):
        t = await pool.add_token("google", "key1")
        await pool.record_success("google", t.key_hash, tokens_used=50, cost=0.005)
        assert t.total_requests == 1
        assert t.total_tokens_used == 50

    @pytest.mark.asyncio
    async def test_record_error_rate_limit(self, pool):
        t = await pool.add_token("google", "key1")
        await pool.record_error("google", t.key_hash, is_rate_limit=True, retry_after=60)
        assert t.state == TokenState.RATE_LIMITED

    @pytest.mark.asyncio
    async def test_rotate_provider(self, pool):
        await pool.add_token("google", "key1")
        await pool.add_token("google", "key2")
        rotated = await pool.rotate_provider("google")
        assert rotated is not None

    @pytest.mark.asyncio
    async def test_rotate_empty(self, pool):
        result = await pool.rotate_provider("empty")
        assert result is None

    @pytest.mark.asyncio
    async def test_reset_daily(self, pool):
        t = await pool.add_token("google", "key1")
        t.daily_requests = 999
        await pool.reset_daily_counters()
        assert t.daily_requests == 0

    @pytest.mark.asyncio
    async def test_stats(self, pool):
        await pool.add_token("google", "k1")
        await pool.add_token("groq", "k2")
        stats = pool.get_stats()
        assert stats["total_tokens"] == 2
        assert "google" in stats["providers"]
        assert "groq" in stats["providers"]

    @pytest.mark.asyncio
    async def test_preemptive_rotation_quota(self, pool):
        t1 = await pool.add_token("google", "key1")
        t1.quota_total = 100
        t1.quota_remaining = 10  # 90% used → should trigger
        t2 = await pool.add_token("google", "key2")
        # Direct method call (not via surgeon which might start loops)
        result = await pool.check_preemptive_rotation("google")
        # Should rotate since > 80% used and alternative exists
        assert result is not None


# ═══════════════════════════════════════════════════════════
# SurgeonAgent Tests (no background loops)
# ═══════════════════════════════════════════════════════════

class TestSurgeonAgent:
    def test_create_surgeon(self):
        s = SurgeonAgent()
        assert s.VERSION == "2.0.0-TITAN"
        assert s.is_running is False
        assert len(s.capabilities) >= 16

    def test_capabilities_list(self):
        s = SurgeonAgent()
        required = [
            "captcha_bypass", "cloudflare_bypass", "token_pooling",
            "browser_automation", "session_reuse", "multi_engine_browser",
            "fingerprint_injection", "human_simulation", "quota_prediction",
            "provider_failover", "encrypted_sessions",
        ]
        for cap in required:
            assert cap in s.capabilities, f"Missing capability: {cap}"

    @pytest.mark.asyncio
    async def test_get_best_model(self):
        s = SurgeonAgent()
        model = await s.get_best_model("marketing")
        assert "gemini" in model.lower() or "pro" in model.lower()

    @pytest.mark.asyncio
    async def test_get_best_model_code(self):
        s = SurgeonAgent()
        model = await s.get_best_model("code")
        assert "llama" in model.lower()

    @pytest.mark.asyncio
    async def test_get_best_model_unknown(self):
        s = SurgeonAgent()
        model = await s.get_best_model("unknown_task")
        assert model == "gemini-2.5-pro"  # Default

    @pytest.mark.asyncio
    async def test_get_provider_for_model(self):
        s = SurgeonAgent()
        assert await s.get_provider_for_model("gemini-2.5-pro") == "google"
        assert await s.get_provider_for_model("llama-3.3-70b") == "groq"
        assert await s.get_provider_for_model("gpt-4o") == "openai"
        assert await s.get_provider_for_model("claude-3.5") == "anthropic"
        assert await s.get_provider_for_model("unknown-model") == "openrouter"

    def test_stats_initial(self):
        s = SurgeonAgent()
        stats = s.get_stats()
        assert "version" in stats
        assert "token_pool" in stats
        assert stats["running"] is False

    def test_health_initial(self):
        s = SurgeonAgent()
        health = s.get_health()
        assert health["status"] == "stopped"
        assert "version" in health

    @pytest.mark.asyncio
    async def test_start_stop(self):
        s = SurgeonAgent()
        await s.start()
        assert s.is_running is True
        # Stop immediately — cancels background tasks
        await s.stop()
        assert s.is_running is False

    @pytest.mark.asyncio
    async def test_double_start(self):
        s = SurgeonAgent()
        await s.start()
        await s.start()  # Should be idempotent
        assert s.is_running is True
        await s.stop()

    @pytest.mark.asyncio
    async def test_failover_no_tokens(self):
        s = SurgeonAgent()
        # Don't start (avoids background loops) — test pool directly
        result = await s.failover("google", "chat")
        assert result is None  # No tokens loaded


# ═══════════════════════════════════════════════════════════
# Singleton Test
# ═══════════════════════════════════════════════════════════

class TestSingleton:
    def test_singleton_exists(self):
        assert singleton_surgeon is not None
        assert isinstance(singleton_surgeon, SurgeonAgent)

    def test_singleton_version(self):
        assert singleton_surgeon.VERSION == "2.0.0-TITAN"

    def test_token_state_enum(self):
        assert TokenState.ACTIVE.value == "active"
        assert TokenState.EXHAUSTED.value == "exhausted"

    def test_provider_health_enum(self):
        assert ProviderHealth.HEALTHY.value == "healthy"
        assert ProviderHealth.DOWN.value == "down"


