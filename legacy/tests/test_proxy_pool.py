
"""Tests for utils/proxy_pool.py — Residential Proxy Pool Manager."""

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.proxy_pool import (
    ProxyType, ProxyProtocol, ProxyHealth, RotationStrategy,
    ProxyEntry, ProviderConfig, ProxyPool, PROVIDER_TEMPLATES,
    proxy_pool,
)


# ═══════════════════════════════════════════════════════════
# ProxyEntry Tests
# ═══════════════════════════════════════════════════════════

class TestProxyEntry:
    def test_create_basic(self):
        p = ProxyEntry(host="1.2.3.4", port=8080)
        assert p.host == "1.2.3.4"
        assert p.port == 8080
        assert p.health == ProxyHealth.UNKNOWN

    def test_proxy_url_no_auth(self):
        p = ProxyEntry(host="1.2.3.4", port=8080, protocol=ProxyProtocol.HTTP)
        assert p.url == "http://1.2.3.4:8080"

    def test_proxy_url_with_auth(self):
        p = ProxyEntry(host="1.2.3.4", port=8080, username="user", password="pass")
        assert "user:pass@" in p.url

    def test_proxy_id_deterministic(self):
        p = ProxyEntry(host="1.2.3.4", port=8080, username="u")
        assert len(p.proxy_id) == 12
        assert p.proxy_id == p.proxy_id  # Same every time

    def test_success_rate_zero_requests(self):
        p = ProxyEntry(host="x", port=1)
        assert p.success_rate == 1.0  # Default to 1.0

    def test_record_success(self):
        p = ProxyEntry(host="x", port=1)
        p.record_success(100.0, 1024)
        assert p.total_requests == 1
        assert p.successful_requests == 1
        assert p.avg_latency_ms == 100.0
        assert p.bytes_received == 1024

    def test_record_success_ema(self):
        p = ProxyEntry(host="x", port=1)
        p.record_success(100.0)
        p.record_success(200.0)
        # EMA: 0.8 * 100 + 0.2 * 200 = 120
        assert abs(p.avg_latency_ms - 120.0) < 0.1

    def test_record_failure_health_degradation(self):
        p = ProxyEntry(host="x", port=1, health=ProxyHealth.HEALTHY)
        for _ in range(3):
            p.record_failure("timeout")
        assert p.health == ProxyHealth.DEGRADED

    def test_record_failure_banned(self):
        p = ProxyEntry(host="x", port=1, health=ProxyHealth.HEALTHY)
        for _ in range(10):
            p.record_failure()
        assert p.health == ProxyHealth.BANNED

    def test_is_available_healthy(self):
        p = ProxyEntry(host="x", port=1, health=ProxyHealth.HEALTHY)
        assert p.is_available

    def test_is_available_banned(self):
        p = ProxyEntry(host="x", port=1, health=ProxyHealth.BANNED)
        assert not p.is_available

    def test_cooldown(self):
        p = ProxyEntry(host="x", port=1, health=ProxyHealth.HEALTHY)
        p.set_cooldown(60)
        assert not p.is_available
        assert p.health == ProxyHealth.COOLDOWN

    def test_quality_score_high_for_residential(self):
        p = ProxyEntry(host="x", port=1, proxy_type=ProxyType.RESIDENTIAL)
        p.record_success(200.0)
        assert p.quality_score > 70

    def test_quality_score_low_for_datacenter_failures(self):
        p = ProxyEntry(host="x", port=1, proxy_type=ProxyType.DATACENTER)
        for _ in range(5):
            p.record_failure()
        assert p.quality_score < 30

    def test_to_dict(self):
        p = ProxyEntry(host="1.2.3.4", port=8080, country="FI", provider="test")
        d = p.to_dict()
        assert d["country"] == "FI"
        assert d["provider"] == "test"
        assert "quality_score" in d
        assert "success_rate" in d


# ═══════════════════════════════════════════════════════════
# ProviderConfig Tests
# ═══════════════════════════════════════════════════════════

class TestProviderConfig:
    def test_create_config(self):
        c = ProviderConfig(
            name="test", gateway_host="proxy.test.com", gateway_port=8080,
            username="user", password="pass",
        )
        assert c.name == "test"

    def test_build_proxy_url_basic(self):
        c = ProviderConfig(
            name="test", gateway_host="proxy.test.com", gateway_port=8080,
            username="user", password="pass",
        )
        url = c.build_proxy_url()
        assert "user:pass@proxy.test.com:8080" in url

    def test_build_proxy_url_with_country(self):
        c = ProviderConfig(
            name="test", gateway_host="proxy.test.com", gateway_port=8080,
            username="user", password="pass", supports_country=True,
        )
        url = c.build_proxy_url(country="FI")
        assert "country-fi" in url

    def test_build_proxy_url_with_session(self):
        c = ProviderConfig(
            name="test", gateway_host="proxy.test.com", gateway_port=8080,
            username="user", password="pass", supports_sessions=True,
        )
        url = c.build_proxy_url(session_id="abc123")
        assert "session-abc123" in url


# ═══════════════════════════════════════════════════════════
# Provider Templates Tests
# ═══════════════════════════════════════════════════════════

class TestTemplates:
    def test_brightdata_exists(self):
        assert "brightdata" in PROVIDER_TEMPLATES

    def test_smartproxy_exists(self):
        assert "smartproxy" in PROVIDER_TEMPLATES

    def test_oxylabs_exists(self):
        assert "oxylabs" in PROVIDER_TEMPLATES

    def test_all_templates_have_host(self):
        for name, tmpl in PROVIDER_TEMPLATES.items():
            assert "gateway_host" in tmpl, f"{name} missing gateway_host"
            assert "gateway_port" in tmpl, f"{name} missing gateway_port"

    def test_template_count(self):
        assert len(PROVIDER_TEMPLATES) >= 5


# ═══════════════════════════════════════════════════════════
# ProxyPool Tests
# ═══════════════════════════════════════════════════════════

class TestProxyPool:
    def test_create_pool(self):
        pool = ProxyPool()
        assert pool.get_stats()["total_proxies"] == 0

    def test_add_proxy(self):
        pool = ProxyPool()
        p = ProxyEntry(host="1.2.3.4", port=8080, country="FI")
        pool.add_proxy(p)
        assert pool.get_stats()["total_proxies"] == 1

    def test_add_multiple_proxies(self):
        pool = ProxyPool()
        proxies = [
            ProxyEntry(host=f"1.2.3.{i}", port=8080) for i in range(5)
        ]
        added = pool.add_proxies(proxies)
        assert added == 5

    def test_remove_proxy(self):
        pool = ProxyPool()
        p = ProxyEntry(host="1.2.3.4", port=8080)
        pool.add_proxy(p)
        assert pool.remove_proxy(p.proxy_id)
        assert pool.get_stats()["total_proxies"] == 0

    def test_add_provider(self):
        pool = ProxyPool()
        config = ProviderConfig(
            name="test", gateway_host="proxy.test.com", gateway_port=8080,
            username="u", password="p",
        )
        pool.add_provider(config)
        assert "test" in pool.get_stats()["providers"]

    def test_add_provider_from_template(self):
        pool = ProxyPool()
        config = pool.add_provider_from_template("brightdata", "user", "pass")
        assert config is not None
        assert config.name == "brightdata"

    def test_add_unknown_template(self):
        pool = ProxyPool()
        config = pool.add_provider_from_template("nonexistent", "u", "p")
        assert config is None

    @pytest.mark.asyncio
    async def test_get_proxy_from_pool(self):
        pool = ProxyPool()
        p1 = ProxyEntry(host="1.2.3.4", port=8080, health=ProxyHealth.HEALTHY)
        pool.add_proxy(p1)
        result = await pool.get_proxy()
        assert result is not None
        assert result.host == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_get_proxy_with_country_filter(self):
        pool = ProxyPool()
        p1 = ProxyEntry(host="1.1.1.1", port=80, country="US", health=ProxyHealth.HEALTHY)
        p2 = ProxyEntry(host="2.2.2.2", port=80, country="FI", health=ProxyHealth.HEALTHY)
        pool.add_proxies([p1, p2])
        result = await pool.get_proxy(country="FI")
        assert result is not None
        assert result.country == "FI"

    @pytest.mark.asyncio
    async def test_get_proxy_excludes_unavailable(self):
        pool = ProxyPool()
        p1 = ProxyEntry(host="1.1.1.1", port=80, health=ProxyHealth.BANNED)
        p2 = ProxyEntry(host="2.2.2.2", port=80, health=ProxyHealth.HEALTHY)
        pool.add_proxies([p1, p2])
        result = await pool.get_proxy()
        assert result is not None
        assert result.host == "2.2.2.2"

    @pytest.mark.asyncio
    async def test_get_proxy_sticky_session(self):
        pool = ProxyPool()
        p1 = ProxyEntry(host="1.1.1.1", port=80, health=ProxyHealth.HEALTHY)
        p2 = ProxyEntry(host="2.2.2.2", port=80, health=ProxyHealth.HEALTHY)
        pool.add_proxies([p1, p2])
        r1 = await pool.get_proxy(strategy=RotationStrategy.SESSION_STICKY, session_key="s1")
        r2 = await pool.get_proxy(strategy=RotationStrategy.SESSION_STICKY, session_key="s1")
        assert r1.proxy_id == r2.proxy_id

    @pytest.mark.asyncio
    async def test_get_proxy_empty_pool_none(self):
        pool = ProxyPool()
        result = await pool.get_proxy()
        assert result is None

    def test_record_result_success(self):
        pool = ProxyPool()
        p = ProxyEntry(host="x", port=1, health=ProxyHealth.HEALTHY)
        pool.add_proxy(p)
        pool.record_result(p, success=True, latency_ms=100)
        assert p.successful_requests == 1

    def test_record_result_failure_with_cooldown(self):
        pool = ProxyPool()
        p = ProxyEntry(host="x", port=1, health=ProxyHealth.HEALTHY)
        pool.add_proxy(p)
        for _ in range(3):
            pool.record_result(p, success=False, target_domain="example.com")
        # Should have domain cooldown applied
        assert p.consecutive_failures == 3

    def test_pool_max_size_eviction(self):
        pool = ProxyPool(max_pool_size=3)
        for i in range(5):
            p = ProxyEntry(host=f"1.1.1.{i}", port=80)
            pool.add_proxy(p)
        assert pool.get_stats()["total_proxies"] <= 3

    def test_build_chain(self):
        pool = ProxyPool()
        p1 = ProxyEntry(host="1.1.1.1", port=80, country="US", health=ProxyHealth.HEALTHY, quality_score=90)
        p2 = ProxyEntry(host="2.2.2.2", port=80, country="DE", health=ProxyHealth.HEALTHY, quality_score=85)
        p3 = ProxyEntry(host="3.3.3.3", port=80, country="JP", health=ProxyHealth.HEALTHY, quality_score=80)
        pool.add_proxies([p1, p2, p3])
        chain = pool.build_chain(hops=2)
        assert len(chain) == 2
        # Different countries
        assert chain[0].country != chain[1].country

    def test_stats_structure(self):
        pool = ProxyPool()
        stats = pool.get_stats()
        assert "total_proxies" in stats
        assert "available_proxies" in stats
        assert "providers" in stats
        assert "by_type" in stats
        assert "strategy" in stats
        assert stats["strategy"] == "weighted"

    @pytest.mark.asyncio
    async def test_start_stop(self):
        pool = ProxyPool(health_check_interval=1)
        await pool.start()
        assert pool._running
        await pool.stop()
        assert not pool._running

    def test_singleton_exists(self):
        assert proxy_pool is not None


# ═══════════════════════════════════════════════════════════
# Rotation Strategy Tests
# ═══════════════════════════════════════════════════════════

class TestRotationStrategies:
    @pytest.mark.asyncio
    async def test_round_robin(self):
        pool = ProxyPool()
        p1 = ProxyEntry(host="1.1.1.1", port=80, health=ProxyHealth.HEALTHY)
        p2 = ProxyEntry(host="2.2.2.2", port=80, health=ProxyHealth.HEALTHY)
        p1.last_used = 100
        p2.last_used = 200
        pool.add_proxies([p1, p2])
        result = await pool.get_proxy(strategy=RotationStrategy.ROUND_ROBIN)
        assert result.host == "1.1.1.1"  # Least recently used

    @pytest.mark.asyncio
    async def test_random(self):
        pool = ProxyPool()
        proxies = [
            ProxyEntry(host=f"1.1.1.{i}", port=80, health=ProxyHealth.HEALTHY)
            for i in range(10)
        ]
        pool.add_proxies(proxies)
        result = await pool.get_proxy(strategy=RotationStrategy.RANDOM)
        assert result is not None

    @pytest.mark.asyncio
    async def test_least_used(self):
        pool = ProxyPool()
        p1 = ProxyEntry(host="1.1.1.1", port=80, health=ProxyHealth.HEALTHY)
        p2 = ProxyEntry(host="2.2.2.2", port=80, health=ProxyHealth.HEALTHY)
        p1.total_requests = 100
        p2.total_requests = 5
        pool.add_proxies([p1, p2])
        result = await pool.get_proxy(strategy=RotationStrategy.LEAST_USED)
        assert result.host == "2.2.2.2"


