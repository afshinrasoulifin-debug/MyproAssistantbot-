
"""
tests/test_stealth_worker_v3.py — Tests for stealth_worker.py v3.0-TITAN
═══════════════════════════════════════════════════════════════════════════
Tests: WAF detection, stack validation, evasion integration, circuit breaker,
proxy config, and backward compatibility.
"""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from orchestration.workers.stealth_worker import (
    StealthWorker, StealthConfig, CaptchaType, CaptchaDetector, WAFType, WAFDetector, StackValidator,
    stealth_worker,
)


# ═══════════════════════════════════════════════
# WAF Detection Tests
# ═══════════════════════════════════════════════

class TestWAFDetector:
    """Test WAF detection engine."""

    @pytest.mark.asyncio
    async def test_detect_cloudflare_headers(self):
        page = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[])
        page.content = AsyncMock(return_value="<html>normal page</html>")

        response = MagicMock()
        response.headers = {"cf-ray": "abc123", "content-type": "text/html"}

        waf_types = await WAFDetector.detect(page, response)
        assert WAFType.CLOUDFLARE in waf_types

    @pytest.mark.asyncio
    async def test_detect_cloudflare_cookies(self):
        page = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[
            {"name": "__cf_bm", "value": "abc"},
            {"name": "session_id", "value": "xyz"},
        ])
        page.content = AsyncMock(return_value="<html>normal</html>")

        waf_types = await WAFDetector.detect(page, None)
        assert WAFType.CLOUDFLARE in waf_types

    @pytest.mark.asyncio
    async def test_detect_datadome_cookies(self):
        page = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[
            {"name": "datadome", "value": "abc"},
        ])
        page.content = AsyncMock(return_value="<html>normal</html>")

        waf_types = await WAFDetector.detect(page, None)
        assert WAFType.DATADOME in waf_types

    @pytest.mark.asyncio
    async def test_detect_perimeterx_content(self):
        page = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[])
        page.content = AsyncMock(return_value='<html><script src="perimeterx.com/px.js"></script></html>')

        waf_types = await WAFDetector.detect(page, None)
        assert WAFType.PERIMETERX in waf_types

    @pytest.mark.asyncio
    async def test_detect_akamai_cookies(self):
        page = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[
            {"name": "_abck", "value": "xyz"},
        ])
        page.content = AsyncMock(return_value="<html></html>")

        waf_types = await WAFDetector.detect(page, None)
        assert WAFType.AKAMAI in waf_types

    @pytest.mark.asyncio
    async def test_detect_kasada_cookies(self):
        page = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[
            {"name": "__kpsdk_ct", "value": "abc"},
        ])
        page.content = AsyncMock(return_value="<html></html>")

        waf_types = await WAFDetector.detect(page, None)
        assert WAFType.KASADA in waf_types

    @pytest.mark.asyncio
    async def test_detect_no_waf(self):
        page = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[])
        page.content = AsyncMock(return_value="<html>normal page</html>")

        waf_types = await WAFDetector.detect(page, None)
        assert len(waf_types) == 0

    @pytest.mark.asyncio
    async def test_detect_multiple_wafs(self):
        page = AsyncMock()
        page.context.cookies = AsyncMock(return_value=[
            {"name": "__cf_bm", "value": "abc"},
            {"name": "_abck", "value": "xyz"},
        ])
        page.content = AsyncMock(return_value="<html></html>")

        response = MagicMock()
        response.headers = {"cf-ray": "abc"}

        waf_types = await WAFDetector.detect(page, response)
        assert WAFType.CLOUDFLARE in waf_types
        assert WAFType.AKAMAI in waf_types

    @pytest.mark.asyncio
    async def test_detect_handles_errors(self):
        page = AsyncMock()
        page.context.cookies = AsyncMock(side_effect=Exception("fail"))
        page.content = AsyncMock(side_effect=Exception("fail"))

        waf_types = await WAFDetector.detect(page, None)
        assert isinstance(waf_types, list)


class TestWAFStrategy:
    """Test WAF-adaptive strategy recommendations."""

    def test_cloudflare_strategy(self):
        strategy = WAFDetector.recommend_strategy([WAFType.CLOUDFLARE])
        assert strategy["extra_wait_seconds"] >= 10
        assert strategy["simulate_behavior_duration"] >= 8.0

    def test_datadome_strategy(self):
        strategy = WAFDetector.recommend_strategy([WAFType.DATADOME])
        assert strategy["use_residential_proxy"] is True
        assert strategy["simulate_behavior_duration"] >= 12.0

    def test_kasada_strategy(self):
        strategy = WAFDetector.recommend_strategy([WAFType.KASADA])
        assert strategy["use_residential_proxy"] is True
        assert strategy["retry_with_different_engine"] is True

    def test_no_waf_strategy(self):
        strategy = WAFDetector.recommend_strategy([])
        assert strategy["extra_wait_seconds"] == 0

    def test_combined_waf_strategy(self):
        strategy = WAFDetector.recommend_strategy([WAFType.CLOUDFLARE, WAFType.DATADOME])
        assert strategy["extra_wait_seconds"] >= 10
        assert strategy["use_residential_proxy"] is True
        assert strategy["simulate_behavior_duration"] >= 12.0


# ═══════════════════════════════════════════════
# Stack Validator Tests
# ═══════════════════════════════════════════════

class TestStackValidator:
    """Test browser stack consistency validation."""

    def test_windows_chrome_nvidia_consistent(self):
        issues = StackValidator.validate(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
            platform_str="Windows",
            webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11)",
            webgl_vendor="Google Inc. (NVIDIA)",
        )
        assert len(issues) == 0

    def test_windows_with_apple_gpu_inconsistent(self):
        issues = StackValidator.validate(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
            platform_str="Windows",
            webgl_renderer="Apple M2",
            webgl_vendor="Apple",
        )
        assert len(issues) > 0
        assert any("Apple" in i for i in issues)

    def test_macos_with_direct3d_inconsistent(self):
        issues = StackValidator.validate(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/125.0",
            platform_str="macOS",
            webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11)",
            webgl_vendor="Google Inc. (NVIDIA)",
        )
        assert len(issues) > 0

    def test_linux_with_mesa_consistent(self):
        issues = StackValidator.validate(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) Chrome/125.0",
            platform_str="Linux",
            webgl_renderer="Mesa Intel(R) UHD Graphics (TGL GT1)",
            webgl_vendor="Mesa",
        )
        assert len(issues) == 0

    def test_linux_with_direct3d_inconsistent(self):
        issues = StackValidator.validate(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) Chrome/125.0",
            platform_str="Linux",
            webgl_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11)",
            webgl_vendor="Google Inc. (NVIDIA)",
        )
        assert len(issues) > 0


# ═══════════════════════════════════════════════
# StealthWorker v3 Tests
# ═══════════════════════════════════════════════

class TestStealthWorkerV3:
    """Test StealthWorker v3.0 features."""

    def test_version(self):
        worker = StealthWorker()
        assert "3.0" in worker.VERSION

    def test_circuit_breaker_init(self):
        worker = StealthWorker()
        assert hasattr(worker, "_circuit_breaker")
        assert isinstance(worker._circuit_breaker, dict)

    def test_reset_circuit_breaker_all(self):
        worker = StealthWorker()
        worker._circuit_breaker["example.com"] = 10
        worker._circuit_breaker["test.com"] = 5
        worker.reset_circuit_breaker()
        assert len(worker._circuit_breaker) == 0

    def test_reset_circuit_breaker_specific(self):
        worker = StealthWorker()
        worker._circuit_breaker["example.com"] = 10
        worker._circuit_breaker["test.com"] = 5
        worker.reset_circuit_breaker("example.com")
        assert "example.com" not in worker._circuit_breaker
        assert "test.com" in worker._circuit_breaker

    def test_stats_include_new_fields(self):
        worker = StealthWorker()
        stats = worker.get_stats()
        assert "waf_detected" in stats
        assert "evasion_scripts_injected" in stats
        assert "circuit_breaker" in stats
        assert "evasion_scripts_available" in stats

    def test_health_includes_evasion(self):
        worker = StealthWorker()
        health = worker.get_health()
        assert "evasion_arsenal" in health
        assert "circuit_breakers_open" in health

    def test_health_circuit_breaker_count(self):
        worker = StealthWorker()
        worker._circuit_breaker["a.com"] = 10  # Over threshold
        worker._circuit_breaker["b.com"] = 2   # Under threshold
        health = worker.get_health()
        assert health["circuit_breakers_open"] == 1


class TestStealthConfig:
    """Test StealthConfig v3 fields."""

    def test_default_proxy_none(self):
        config = StealthConfig()
        assert config.proxy_url is None
        assert config.proxy_bypass == ""

    def test_waf_adaptive_default_true(self):
        config = StealthConfig()
        assert config.waf_adaptive is True

    def test_evasion_arsenal_default_true(self):
        config = StealthConfig()
        assert config.use_evasion_arsenal is True

    def test_custom_proxy(self):
        config = StealthConfig(proxy_url="socks5://user:pass@proxy.com:1080")
        assert "socks5" in config.proxy_url

    def test_custom_bypass(self):
        config = StealthConfig(proxy_bypass="localhost,127.0.0.1")
        assert "localhost" in config.proxy_bypass


# ═══════════════════════════════════════════════
# CAPTCHA Detection Tests (backward compat)
# ═══════════════════════════════════════════════

class TestCaptchaDetection:
    """Backward compatibility for CAPTCHA detection."""

    @pytest.mark.asyncio
    async def test_detect_cloudflare_challenge(self):
        page = AsyncMock()
        page.content = AsyncMock(return_value='<div class="cf-challenge-running">challenge</div>')
        page.url = "https://example.com"

        import orchestration.workers.stealth_worker as sw
        orig = sw.PLAYWRIGHT_AVAILABLE
        sw.PLAYWRIGHT_AVAILABLE = True
        try:
            result = await CaptchaDetector.detect(page)
            assert result == CaptchaType.CLOUDFLARE_CHALLENGE
        finally:
            sw.PLAYWRIGHT_AVAILABLE = orig

    @pytest.mark.asyncio
    async def test_detect_turnstile(self):
        page = AsyncMock()
        page.content = AsyncMock(
            return_value='<div class="cf-turnstile" data-sitekey="abc">turnstile</div>'
        )
        page.url = "https://example.com"

        import orchestration.workers.stealth_worker as sw
        orig = sw.PLAYWRIGHT_AVAILABLE
        sw.PLAYWRIGHT_AVAILABLE = True
        try:
            result = await CaptchaDetector.detect(page)
            assert result == CaptchaType.CLOUDFLARE_TURNSTILE
        finally:
            sw.PLAYWRIGHT_AVAILABLE = orig

    @pytest.mark.asyncio
    async def test_detect_recaptcha_v2(self):
        page = AsyncMock()
        page.content = AsyncMock(
            return_value='<div class="g-recaptcha" data-sitekey="abc"></div>'
        )
        page.url = "https://example.com"

        import orchestration.workers.stealth_worker as sw
        orig = sw.PLAYWRIGHT_AVAILABLE
        sw.PLAYWRIGHT_AVAILABLE = True
        try:
            result = await CaptchaDetector.detect(page)
            assert result == CaptchaType.RECAPTCHA_V2
        finally:
            sw.PLAYWRIGHT_AVAILABLE = orig

    @pytest.mark.asyncio
    async def test_detect_recaptcha_v3(self):
        page = AsyncMock()
        page.content = AsyncMock(
            return_value='<script src="recaptcha/api.js?render=abc"></script>'
        )
        page.url = "https://example.com"

        import orchestration.workers.stealth_worker as sw
        orig = sw.PLAYWRIGHT_AVAILABLE
        sw.PLAYWRIGHT_AVAILABLE = True
        try:
            result = await CaptchaDetector.detect(page)
            assert result == CaptchaType.RECAPTCHA_V3
        finally:
            sw.PLAYWRIGHT_AVAILABLE = orig

    @pytest.mark.asyncio
    async def test_detect_hcaptcha(self):
        page = AsyncMock()
        page.content = AsyncMock(
            return_value='<div class="h-captcha" data-sitekey="abc"></div>'
        )
        page.url = "https://example.com"

        import orchestration.workers.stealth_worker as sw
        orig = sw.PLAYWRIGHT_AVAILABLE
        sw.PLAYWRIGHT_AVAILABLE = True
        try:
            result = await CaptchaDetector.detect(page)
            assert result == CaptchaType.HCAPTCHA
        finally:
            sw.PLAYWRIGHT_AVAILABLE = orig

    @pytest.mark.asyncio
    async def test_detect_no_captcha(self):
        page = AsyncMock()
        page.content = AsyncMock(return_value="<html>normal page</html>")
        page.url = "https://example.com"

        import orchestration.workers.stealth_worker as sw
        orig = sw.PLAYWRIGHT_AVAILABLE
        sw.PLAYWRIGHT_AVAILABLE = True
        try:
            result = await CaptchaDetector.detect(page)
            assert result is None
        finally:
            sw.PLAYWRIGHT_AVAILABLE = orig


# ═══════════════════════════════════════════════
# Stealth Session (circuit breaker) Tests
# ═══════════════════════════════════════════════

class TestCircuitBreaker:
    """Test circuit breaker in run_stealth_session."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_after_threshold(self):
        worker = StealthWorker()
        worker._running = True
        worker._circuit_breaker["example.com"] = 10

        import orchestration.workers.stealth_worker as sw
        orig = sw.PLAYWRIGHT_AVAILABLE
        sw.PLAYWRIGHT_AVAILABLE = True
        try:
            result = await worker.run_stealth_session(
                url="https://example.com/page",
                provider_id="test",
            )
            assert result["success"] is False
            assert "Circuit breaker" in result["error"]
        finally:
            sw.PLAYWRIGHT_AVAILABLE = orig

    @pytest.mark.asyncio
    async def test_circuit_breaker_allows_different_domain(self):
        worker = StealthWorker()
        worker._running = True
        worker._circuit_breaker["blocked.com"] = 10

        # other.com should not be circuit-breaker blocked
        # It will still fail (no playwright) but error message differs
        result = await worker.run_stealth_session(
            url="https://other.com/page",
            provider_id="test",
        )
        assert "Circuit breaker" not in result.get("error", "")


# ═══════════════════════════════════════════════
# Singleton backward compat
# ═══════════════════════════════════════════════

class TestSingleton:
    """Test module-level singleton."""

    def test_stealth_worker_singleton_exists(self):
        assert stealth_worker is not None
        assert isinstance(stealth_worker, StealthWorker)

    def test_singleton_version(self):
        assert "3.0" in stealth_worker.VERSION


