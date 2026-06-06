
"""Tests for utils/captcha_engine.py — Advanced Captcha Intelligence Engine."""

import pytest
import time
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.captcha_engine import (
    BudgetConfig,
    BudgetTracker,
    CachedToken,
    CaptchaDetector,
    CaptchaEngine,
    CaptchaFamily,
    SolveRequest,
    SolveResult,
    SolverConfig,
    SolverProvider,
    SolverRouter,
    SOLVER_CAPABILITIES,
    SOLVER_PRICING,
    TokenCache,
    captcha_engine,
)


# ═══════════════════════════════════════════════════════════
# CaptchaDetector Tests
# ═══════════════════════════════════════════════════════════

class TestCaptchaDetector:
    def test_detect_recaptcha_v2(self):
        html = '<div class="g-recaptcha" data-sitekey="abc123"></div>'
        detected = CaptchaDetector.detect_from_html(html)
        assert CaptchaFamily.RECAPTCHA_V2 in detected

    def test_detect_recaptcha_v3(self):
        html = '<script src="https://www.google.com/recaptcha/api.js?render=abc"></script>'
        detected = CaptchaDetector.detect_from_html(html)
        assert CaptchaFamily.RECAPTCHA_V3 in detected

    def test_detect_hcaptcha(self):
        html = '<div class="h-captcha" data-sitekey="abc"></div>'
        detected = CaptchaDetector.detect_from_html(html)
        assert CaptchaFamily.HCAPTCHA in detected

    def test_detect_turnstile(self):
        html = '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>'
        detected = CaptchaDetector.detect_from_html(html)
        assert CaptchaFamily.CLOUDFLARE_TURNSTILE in detected

    def test_detect_funcaptcha(self):
        html = '<script src="https://cdn.arkoselabs.com/fc/api/"></script>'
        detected = CaptchaDetector.detect_from_html(html)
        assert CaptchaFamily.FUNCAPTCHA in detected

    def test_detect_geetest(self):
        html = '<script>initGeetest({gt: "abc"})</script>'
        detected = CaptchaDetector.detect_from_html(html)
        assert CaptchaFamily.GEETEST_V3 in detected

    def test_detect_none(self):
        html = '<div>No captcha here</div>'
        assert len(CaptchaDetector.detect_from_html(html)) == 0

    def test_detect_from_scripts(self):
        urls = [
            "https://www.google.com/recaptcha/api2/anchor",
            "https://hcaptcha.com/1/api.js",
        ]
        detected = CaptchaDetector.detect_from_scripts(urls)
        assert CaptchaFamily.RECAPTCHA_V2 in detected
        assert CaptchaFamily.HCAPTCHA in detected

    def test_extract_sitekey_recaptcha(self):
        html = '<div class="g-recaptcha" data-sitekey="6LeIxAcTAAAAA"></div>'
        key = CaptchaDetector.extract_sitekey(html, CaptchaFamily.RECAPTCHA_V2)
        assert key == "6LeIxAcTAAAAA"

    def test_extract_sitekey_hcaptcha(self):
        html = '<div class="h-captcha" data-sitekey="10000000-ffff"></div>'
        key = CaptchaDetector.extract_sitekey(html, CaptchaFamily.HCAPTCHA)
        assert key == "10000000-ffff"

    def test_extract_sitekey_missing(self):
        key = CaptchaDetector.extract_sitekey('<div>x</div>', CaptchaFamily.RECAPTCHA_V2)
        assert key is None


# ═══════════════════════════════════════════════════════════
# Solver Pricing & Capabilities Tests
# ═══════════════════════════════════════════════════════════

class TestSolverPricingCaps:
    def test_all_providers_have_pricing(self):
        for provider in SolverProvider:
            assert provider in SOLVER_PRICING

    def test_capabilities_match_pricing(self):
        for provider, caps in SOLVER_CAPABILITIES.items():
            prices = SOLVER_PRICING[provider]
            assert caps == set(prices.keys())

    def test_recaptcha_v2_widely_supported(self):
        for provider, caps in SOLVER_CAPABILITIES.items():
            assert CaptchaFamily.RECAPTCHA_V2 in caps


# ═══════════════════════════════════════════════════════════
# TokenCache Tests
# ═══════════════════════════════════════════════════════════

class TestTokenCache:
    def test_store_and_get(self):
        cache = TokenCache()
        cache.store(CachedToken(
            token="abc123",
            captcha_type=CaptchaFamily.RECAPTCHA_V2,
            sitekey="key1", page_url="https://example.com",
        ))
        result = cache.get(CaptchaFamily.RECAPTCHA_V2, "key1", "https://example.com")
        assert result == "abc123"

    def test_get_empty(self):
        cache = TokenCache()
        assert cache.get(CaptchaFamily.RECAPTCHA_V2, "k", "https://a.com") is None

    def test_expired_token_not_returned(self):
        cache = TokenCache()
        cache.store(CachedToken(
            token="expired",
            captcha_type=CaptchaFamily.RECAPTCHA_V2,
            sitekey="k", page_url="https://a.com",
            created_at=time.time() - 300,
        ))
        assert cache.get(CaptchaFamily.RECAPTCHA_V2, "k", "https://a.com") is None

    def test_max_size_enforced(self):
        cache = TokenCache(max_size=5)
        for i in range(10):
            cache.store(CachedToken(
                token=f"t_{i}", captcha_type=CaptchaFamily.RECAPTCHA_V2,
                sitekey=f"k_{i}", page_url=f"https://s{i}.com",
            ))
        assert cache.size <= 5

    def test_hit_rate(self):
        cache = TokenCache()
        cache.store(CachedToken(
            token="abc", captcha_type=CaptchaFamily.HCAPTCHA,
            sitekey="k", page_url="https://a.com",
        ))
        cache.get(CaptchaFamily.HCAPTCHA, "k", "https://a.com")  # Hit
        cache.get(CaptchaFamily.HCAPTCHA, "k2", "https://b.com")  # Miss
        assert cache.hit_rate == 0.5

    def test_cached_token_validity(self):
        token = CachedToken(
            token="abc", captcha_type=CaptchaFamily.RECAPTCHA_V2,
            sitekey="k", page_url="https://a.com", created_at=time.time(),
        )
        assert token.is_valid

        old = CachedToken(
            token="abc", captcha_type=CaptchaFamily.RECAPTCHA_V2,
            sitekey="k", page_url="https://a.com", created_at=time.time() - 300,
        )
        assert not old.is_valid


# ═══════════════════════════════════════════════════════════
# SolverRouter Tests
# ═══════════════════════════════════════════════════════════

class TestSolverRouter:
    def _make_solvers(self):
        return [
            SolverConfig(provider=SolverProvider.TWO_CAPTCHA, api_key="t1"),
            SolverConfig(provider=SolverProvider.CAPSOLVER, api_key="t2"),
            SolverConfig(provider=SolverProvider.CAPMONSTER, api_key="t3"),
        ]

    def test_select_solver_basic(self):
        router = SolverRouter()
        selected = router.select_solver(CaptchaFamily.RECAPTCHA_V2, self._make_solvers())
        assert selected is not None

    def test_select_solver_cost_optimization(self):
        router = SolverRouter()
        selected = router.select_solver(
            CaptchaFamily.RECAPTCHA_V2, self._make_solvers(), optimize_for="cost"
        )
        assert selected.provider == SolverProvider.CAPMONSTER

    def test_select_solver_no_capable(self):
        router = SolverRouter()
        solvers = [SolverConfig(provider=SolverProvider.CAPMONSTER, api_key="t")]
        assert router.select_solver(CaptchaFamily.AMAZON_WAF, solvers) is None

    def test_fallback_chain(self):
        router = SolverRouter()
        chain = router.get_fallback_chain(CaptchaFamily.RECAPTCHA_V2, self._make_solvers())
        assert len(chain) == 3

    def test_performance_tracking(self):
        router = SolverRouter()
        stats = router.get_stats(SolverProvider.TWO_CAPTCHA, CaptchaFamily.RECAPTCHA_V2)
        stats.record_success(15000, 0.003)
        assert stats.success_rate == 1.0

    def test_failure_reduces_priority(self):
        router = SolverRouter()
        stats = router.get_stats(SolverProvider.CAPMONSTER, CaptchaFamily.RECAPTCHA_V2)
        for _ in range(5):
            stats.record_failure()
        selected = router.select_solver(
            CaptchaFamily.RECAPTCHA_V2, self._make_solvers(), optimize_for="reliability"
        )
        assert selected.provider != SolverProvider.CAPMONSTER


# ═══════════════════════════════════════════════════════════
# BudgetTracker Tests
# ═══════════════════════════════════════════════════════════

class TestBudgetTracker:
    def test_within_budget(self):
        tracker = BudgetTracker(BudgetConfig(daily_budget_usd=10))
        tracker.record_spend(1.0)
        assert tracker.is_within_budget()

    def test_over_budget(self):
        tracker = BudgetTracker(BudgetConfig(daily_budget_usd=1.0))
        tracker.record_spend(2.0)
        assert not tracker.is_within_budget()

    def test_alert_threshold(self):
        tracker = BudgetTracker(BudgetConfig(daily_budget_usd=10, alert_threshold=0.5))
        tracker.record_spend(6.0)
        assert tracker.should_alert()

    def test_get_stats(self):
        tracker = BudgetTracker()
        tracker.record_spend(0.5)
        stats = tracker.get_stats()
        assert stats["today_usd"] == 0.5


# ═══════════════════════════════════════════════════════════
# CaptchaEngine (Main) Tests
# ═══════════════════════════════════════════════════════════

class TestCaptchaEngine:
    def test_singleton(self):
        assert captcha_engine is not None

    def test_version(self):
        assert "TITAN" in CaptchaEngine.VERSION

    def test_add_remove_solver(self):
        engine = CaptchaEngine()
        engine.add_solver(SolverConfig(provider=SolverProvider.TWO_CAPTCHA, api_key="t"))
        assert len(engine._solvers) == 1
        engine.remove_solver(SolverProvider.TWO_CAPTCHA)
        assert len(engine._solvers) == 0

    def test_detect_captcha(self):
        engine = CaptchaEngine()
        detected = engine.detect_captcha(html='<div class="g-recaptcha" data-sitekey="x"></div>')
        assert CaptchaFamily.RECAPTCHA_V2 in detected

    def test_detect_from_scripts(self):
        engine = CaptchaEngine()
        detected = engine.detect_captcha(script_urls=["https://hcaptcha.com/1/api.js"])
        assert CaptchaFamily.HCAPTCHA in detected

    def test_extract_sitekey(self):
        engine = CaptchaEngine()
        key = engine.extract_sitekey('<div data-sitekey="mykey"></div>', CaptchaFamily.RECAPTCHA_V2)
        assert key == "mykey"

    @pytest.mark.asyncio
    async def test_solve_no_solvers(self):
        engine = CaptchaEngine()
        result = await engine.solve(SolveRequest(
            captcha_type=CaptchaFamily.RECAPTCHA_V2,
            sitekey="abc", page_url="https://example.com",
        ))
        assert not result.success
        assert "No solver" in result.error

    @pytest.mark.asyncio
    async def test_solve_with_cache(self):
        engine = CaptchaEngine()
        engine._token_cache.store(CachedToken(
            token="cached_token",
            captcha_type=CaptchaFamily.HCAPTCHA,
            sitekey="k1", page_url="https://a.com",
        ))
        result = await engine.solve(SolveRequest(
            captcha_type=CaptchaFamily.HCAPTCHA,
            sitekey="k1", page_url="https://a.com",
        ))
        assert result.success
        assert result.token == "cached_token"
        assert result.from_cache

    @pytest.mark.asyncio
    async def test_solve_over_budget(self):
        engine = CaptchaEngine(budget=BudgetConfig(daily_budget_usd=0))
        engine.add_solver(SolverConfig(provider=SolverProvider.TWO_CAPTCHA, api_key="t"))
        engine._budget.record_spend(1.0)
        result = await engine.solve(
            SolveRequest(captcha_type=CaptchaFamily.RECAPTCHA_V2, sitekey="k", page_url="https://a.com"),
            use_cache=False,
        )
        assert not result.success
        assert "Budget" in result.error

    def test_get_cheapest_solver(self):
        engine = CaptchaEngine()
        cheapest = engine.get_cheapest_solver(CaptchaFamily.IMAGE_CAPTCHA)
        assert cheapest is not None
        _, cost = cheapest
        assert cost < 1.0

    def test_get_supported_types(self):
        engine = CaptchaEngine()
        engine.add_solver(SolverConfig(provider=SolverProvider.CAPSOLVER, api_key="t"))
        types = engine.get_supported_types()
        assert "capsolver" in types
        assert "recaptcha_v2" in types["capsolver"]

    def test_get_stats(self):
        engine = CaptchaEngine()
        stats = engine.get_stats()
        assert stats["version"] == CaptchaEngine.VERSION
        assert stats["total_solves"] == 0

    def test_solve_result_to_dict(self):
        result = SolveResult(
            success=True, token="abc",
            provider=SolverProvider.TWO_CAPTCHA,
            captcha_type=CaptchaFamily.RECAPTCHA_V2,
            solve_time_ms=15000, cost_usd=0.003,
        )
        d = result.to_dict()
        assert d["success"]
        assert d["provider"] == "2captcha"


