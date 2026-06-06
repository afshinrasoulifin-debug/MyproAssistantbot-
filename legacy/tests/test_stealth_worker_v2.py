
"""
Tests for orchestration/workers/stealth_worker.py — Stealth Browser Engine v2.0-TITAN
"""
import os
import sys
import pytest

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from orchestration.workers.stealth_worker import (
    StealthWorker, StealthConfig, BrowserEngine, CaptchaType,
    BypassResult, CaptchaDetector, CaptchaBypass,
    USER_AGENTS, VIEWPORT_PROFILES, TIMEZONES, LOCALES,
    TRACKER_PATTERNS, CANVAS_NOISE_SCRIPT, WEBGL_NOISE_SCRIPT,
    AUDIO_NOISE_SCRIPT, WEBDRIVER_HIDE_SCRIPT,
    stealth_worker as singleton_worker,
)


# ═══════════════════════════════════════════════════════════
# Config Tests
# ═══════════════════════════════════════════════════════════

class TestStealthConfig:
    def test_default_config(self):
        c = StealthConfig()
        assert c.engine == BrowserEngine.CHROMIUM
        assert c.headless is True
        assert c.inject_canvas_noise is True
        assert c.simulate_human_behavior is True
        assert c.max_retries == 3

    def test_custom_config(self):
        c = StealthConfig(
            engine=BrowserEngine.FIREFOX,
            headless=False,
            max_retries=5,
            block_images=True,
        )
        assert c.engine == BrowserEngine.FIREFOX
        assert c.headless is False
        assert c.max_retries == 5
        assert c.block_images is True


# ═══════════════════════════════════════════════════════════
# Enum Tests
# ═══════════════════════════════════════════════════════════

class TestEnums:
    def test_browser_engine_values(self):
        assert BrowserEngine.CHROMIUM.value == "chromium"
        assert BrowserEngine.FIREFOX.value == "firefox"
        assert BrowserEngine.WEBKIT.value == "webkit"

    def test_captcha_type_values(self):
        assert CaptchaType.RECAPTCHA_V2.value == "recaptcha_v2"
        assert CaptchaType.CLOUDFLARE_TURNSTILE.value == "turnstile"
        assert CaptchaType.HCAPTCHA.value == "hcaptcha"

    def test_bypass_result_values(self):
        assert BypassResult.SUCCESS.value == "success"
        assert BypassResult.CLOUDFLARE_BLOCKED.value == "cloudflare_blocked"
        assert BypassResult.RETRY_NEEDED.value == "retry_needed"


# ═══════════════════════════════════════════════════════════
# Constants Tests
# ═══════════════════════════════════════════════════════════

class TestConstants:
    def test_user_agents_populated(self):
        assert len(USER_AGENTS) >= 5
        for ua in USER_AGENTS:
            assert "Mozilla" in ua

    def test_viewport_profiles(self):
        assert len(VIEWPORT_PROFILES) >= 4
        for vp in VIEWPORT_PROFILES:
            assert "width" in vp
            assert "height" in vp
            assert vp["width"] > 0
            assert vp["height"] > 0

    def test_timezones(self):
        assert "Europe/Helsinki" in TIMEZONES
        assert len(TIMEZONES) >= 3

    def test_locales(self):
        assert "en-US" in LOCALES
        assert "fi-FI" in LOCALES

    def test_tracker_patterns(self):
        assert len(TRACKER_PATTERNS) >= 5

    def test_fingerprint_scripts_non_empty(self):
        assert len(CANVAS_NOISE_SCRIPT) > 50
        assert len(WEBGL_NOISE_SCRIPT) > 50
        assert len(AUDIO_NOISE_SCRIPT) > 50
        assert len(WEBDRIVER_HIDE_SCRIPT) > 50
        assert "webdriver" in WEBDRIVER_HIDE_SCRIPT


# ═══════════════════════════════════════════════════════════
# StealthWorker Tests (without Playwright)
# ═══════════════════════════════════════════════════════════

class TestStealthWorkerInit:
    def test_create_worker(self):
        w = StealthWorker(sessions_dir="/tmp/test_sessions_sw")
        assert w.VERSION == "3.0.0-TITAN"
        assert w._running is False
        assert w._max_concurrent == 3

    def test_custom_config(self):
        cfg = StealthConfig(engine=BrowserEngine.FIREFOX, max_retries=5)
        w = StealthWorker(config=cfg, max_concurrent=5)
        assert w._config.engine == BrowserEngine.FIREFOX
        assert w._max_concurrent == 5

    def test_stats_initial(self):
        w = StealthWorker(sessions_dir="/tmp/test_sessions_sw2")
        stats = w.get_stats()
        assert stats["version"] == "3.0.0-TITAN"
        assert stats["running"] is False
        assert stats["total_sessions"] == 0
        assert stats["successful_bypasses"] == 0

    def test_health_initial(self):
        w = StealthWorker(sessions_dir="/tmp/test_sessions_sw3")
        health = w.get_health()
        assert health["status"] == "stopped"
        assert "success_rate" in health

    @pytest.mark.asyncio
    async def test_run_without_playwright(self):
        w = StealthWorker(sessions_dir="/tmp/test_sessions_sw4")
        # Without starting, should return error
        result = await w.run_stealth_session(url="https://example.com", provider_id="test")
        assert result["success"] is False
        assert "not started" in result.get("error", "").lower() or "not installed" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_run_bypass_session_compat(self):
        w = StealthWorker(sessions_dir="/tmp/test_sessions_sw5")
        result = await w.run_bypass_session(url="https://example.com", provider_id="test")
        assert result["success"] is False
        assert result["provider"] == "test"


# ═══════════════════════════════════════════════════════════
# CaptchaDetector Tests
# ═══════════════════════════════════════════════════════════

class TestCaptchaDetector:
    def test_cf_markers(self):
        assert len(CaptchaDetector.CF_CHALLENGE_MARKERS) >= 3
        assert "cf-challenge-running" in CaptchaDetector.CF_CHALLENGE_MARKERS

    def test_recaptcha_markers(self):
        assert len(CaptchaDetector.RECAPTCHA_MARKERS) >= 2
        assert "g-recaptcha" in CaptchaDetector.RECAPTCHA_MARKERS

    def test_hcaptcha_markers(self):
        assert "h-captcha" in CaptchaDetector.HCAPTCHA_MARKERS

    def test_turnstile_markers(self):
        assert "cf-turnstile" in CaptchaDetector.TURNSTILE_MARKERS


# ═══════════════════════════════════════════════════════════
# CaptchaBypass Tests
# ═══════════════════════════════════════════════════════════

class TestCaptchaBypass:
    def test_solver_config(self):
        # Should read from env (empty in test)
        assert isinstance(CaptchaBypass.SOLVER_API_KEY, str)
        assert isinstance(CaptchaBypass.SOLVER_SERVICE, str)


# ═══════════════════════════════════════════════════════════
# Singleton Tests
# ═══════════════════════════════════════════════════════════

class TestSingleton:
    def test_singleton_exists(self):
        assert singleton_worker is not None
        assert isinstance(singleton_worker, StealthWorker)

    def test_singleton_version(self):
        assert singleton_worker.VERSION == "3.0.0-TITAN"


