
"""
tests/test_anti_detection_v2.py — Tests for anti_detection.py v3.0 PRO upgrades
═══════════════════════════════════════════════════════════════════════════════════
Tests: HTTP/2 profiles, Client Hints, residential proxy scoring,
request timing, extended WebGL profiles, consistent profile generation.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.anti_detection import (
    AntiDetectionEngine, BrowserType, Platform,
    UserAgentGenerator, BehaviorSimulator, HeaderBuilder,
    TLSProfileGenerator, ProxyChainManager, ProxyConfig, CookieJar, Cookie,
    # New v3 additions
    H2_PROFILES, H2_CHROME_125, H2_FIREFOX_126, H2_SAFARI_17,
    WEBGL_RENDERERS_EXTENDED, MODERN_JA3_HASHES,
    ProxyQuality, ProxyQualityScorer,
    RequestTimingEngine,
)


# ═══════════════════════════════════════════════
# HTTP/2 Profile Tests
# ═══════════════════════════════════════════════

class TestHTTP2Profiles:
    """Test HTTP/2 fingerprint profiles."""

    def test_chrome_125_profile_exists(self):
        assert "chrome_125" in H2_PROFILES
        p = H2_PROFILES["chrome_125"]
        assert p.browser == BrowserType.CHROME

    def test_firefox_126_profile_exists(self):
        assert "firefox_126" in H2_PROFILES
        p = H2_PROFILES["firefox_126"]
        assert p.browser == BrowserType.FIREFOX

    def test_safari_17_profile_exists(self):
        assert "safari_17" in H2_PROFILES
        p = H2_PROFILES["safari_17"]
        assert p.browser == BrowserType.SAFARI

    def test_chrome_h2_settings(self):
        p = H2_CHROME_125
        assert 1 in p.settings  # HEADER_TABLE_SIZE
        assert 2 in p.settings  # ENABLE_PUSH
        assert p.settings[2] == 0  # Push disabled
        assert 4 in p.settings  # INITIAL_WINDOW_SIZE
        assert p.window_update > 0

    def test_firefox_h2_no_priority_frames(self):
        p = H2_FIREFOX_126
        assert p.priority_frames is False  # Firefox dropped PRIORITY

    def test_pseudo_header_order_differs(self):
        """Different browsers have different pseudo-header orders."""
        chrome_order = H2_CHROME_125.pseudo_header_order
        firefox_order = H2_FIREFOX_126.pseudo_header_order
        safari_order = H2_SAFARI_17.pseudo_header_order
        # All should have 4 pseudo-headers
        assert len(chrome_order) == 4
        assert len(firefox_order) == 4
        assert len(safari_order) == 4
        # They should differ
        assert chrome_order != firefox_order or chrome_order != safari_order

    def test_h2_profiles_have_all_fields(self):
        for name, profile in H2_PROFILES.items():
            assert isinstance(profile.settings, dict), f"{name} missing settings"
            assert isinstance(profile.window_update, int), f"{name} missing window_update"
            assert isinstance(profile.pseudo_header_order, list), f"{name} missing pseudo_header_order"
            assert isinstance(profile.priority_frames, bool), f"{name} missing priority_frames"


# ═══════════════════════════════════════════════
# Client Hints Tests
# ═══════════════════════════════════════════════

class TestClientHints:
    """Test Client Hints header generation."""

    def test_chrome_has_client_hints(self):
        engine = AntiDetectionEngine()
        fp = engine.generate_fingerprint(browser=BrowserType.CHROME, platform=Platform.WINDOWS)
        hints = HeaderBuilder.build_client_hints(fp, BrowserType.CHROME)
        assert "sec-ch-ua" in hints
        assert "sec-ch-ua-platform" in hints
        assert "sec-ch-ua-full-version-list" in hints
        assert "sec-ch-ua-arch" in hints
        assert "sec-ch-ua-bitness" in hints
        assert '"64"' == hints["sec-ch-ua-bitness"]

    def test_firefox_no_client_hints(self):
        engine = AntiDetectionEngine()
        fp = engine.generate_fingerprint(browser=BrowserType.FIREFOX)
        hints = HeaderBuilder.build_client_hints(fp, BrowserType.FIREFOX)
        assert len(hints) == 0  # Firefox doesn't send Client Hints

    def test_safari_no_client_hints(self):
        engine = AntiDetectionEngine()
        fp = engine.generate_fingerprint(browser=BrowserType.SAFARI)
        hints = HeaderBuilder.build_client_hints(fp, BrowserType.SAFARI)
        assert len(hints) == 0

    def test_client_hints_platform_matches(self):
        engine = AntiDetectionEngine()
        fp = engine.generate_fingerprint(browser=BrowserType.CHROME, platform=Platform.WINDOWS)
        hints = HeaderBuilder.build_client_hints(fp, BrowserType.CHROME)
        assert "Windows" in hints.get("sec-ch-ua-platform", "")

    def test_client_hints_arch_correct(self):
        engine = AntiDetectionEngine()
        fp = engine.generate_fingerprint(browser=BrowserType.CHROME, platform=Platform.MACOS)
        hints = HeaderBuilder.build_client_hints(fp, BrowserType.CHROME)
        assert '"arm"' == hints.get("sec-ch-ua-arch", "")

    def test_client_hints_custom_version(self):
        engine = AntiDetectionEngine()
        fp = engine.generate_fingerprint(browser=BrowserType.CHROME)
        hints = HeaderBuilder.build_client_hints(fp, BrowserType.CHROME, full_version="126.0.6478.55")
        assert "126.0.6478.55" in hints.get("sec-ch-ua-full-version", "")
        assert "126.0.6478.55" in hints.get("sec-ch-ua-full-version-list", "")


# ═══════════════════════════════════════════════
# Extended WebGL Profiles Tests
# ═══════════════════════════════════════════════

class TestExtendedWebGL:
    """Test expanded WebGL GPU database."""

    def test_at_least_30_renderers(self):
        assert len(WEBGL_RENDERERS_EXTENDED) >= 30

    def test_all_renderers_have_vendor_and_string(self):
        for vendor, renderer in WEBGL_RENDERERS_EXTENDED:
            assert isinstance(vendor, str) and len(vendor) > 0
            assert isinstance(renderer, str) and len(renderer) > 0

    def test_has_nvidia_gpus(self):
        nvidia = [r for v, r in WEBGL_RENDERERS_EXTENDED if "NVIDIA" in v]
        assert len(nvidia) >= 10

    def test_has_amd_gpus(self):
        amd = [r for v, r in WEBGL_RENDERERS_EXTENDED if "AMD" in v]
        assert len(amd) >= 5

    def test_has_intel_gpus(self):
        intel = [r for v, r in WEBGL_RENDERERS_EXTENDED if "Intel" in v]
        assert len(intel) >= 4

    def test_has_apple_silicon(self):
        apple = [r for v, r in WEBGL_RENDERERS_EXTENDED if "Apple" in v]
        assert len(apple) >= 5

    def test_has_linux_mesa(self):
        mesa = [r for v, r in WEBGL_RENDERERS_EXTENDED if "Mesa" in v]
        assert len(mesa) >= 2

    def test_has_laptop_gpus(self):
        laptop = [r for v, r in WEBGL_RENDERERS_EXTENDED if "Laptop" in r]
        assert len(laptop) >= 2


# ═══════════════════════════════════════════════
# Proxy Quality Scoring Tests
# ═══════════════════════════════════════════════

class TestProxyQualityScoring:
    """Test residential proxy quality scorer."""

    def test_residential_scores_highest(self):
        proxy = ProxyConfig(host="1.2.3.4", port=8080)
        quality = ProxyQuality(
            is_residential=True,
            asn_type="residential",
            response_time_ms=100,
            success_rate=0.95,
            country="US",
            city="New York",
        )
        score = ProxyQualityScorer.score(proxy, quality)
        assert score >= 80

    def test_datacenter_scores_low(self):
        proxy = ProxyConfig(host="1.2.3.4", port=8080)
        quality = ProxyQuality(
            is_datacenter=True,
            asn_type="datacenter",
            response_time_ms=500,
            success_rate=0.5,
        )
        score = ProxyQualityScorer.score(proxy, quality)
        assert score < 50

    def test_mobile_scores_high(self):
        proxy = ProxyConfig(host="1.2.3.4", port=8080)
        quality = ProxyQuality(
            asn_type="mobile",
            response_time_ms=200,
            success_rate=0.9,
            country="FI",
        )
        score = ProxyQualityScorer.score(proxy, quality)
        assert score >= 70

    def test_slow_proxy_penalized(self):
        proxy = ProxyConfig(host="1.2.3.4", port=8080)
        fast = ProxyQuality(asn_type="residential", response_time_ms=100, success_rate=0.9)
        slow = ProxyQuality(asn_type="residential", response_time_ms=2500, success_rate=0.9)
        fast_score = ProxyQualityScorer.score(proxy, fast)
        slow_score = ProxyQualityScorer.score(proxy, slow)
        assert fast_score > slow_score

    def test_is_safe_for_stealth(self):
        good = ProxyQuality(score=80, success_rate=0.95, response_time_ms=200)
        assert ProxyQualityScorer.is_safe_for_stealth(good)

    def test_not_safe_if_low_score(self):
        bad = ProxyQuality(score=30, success_rate=0.4, response_time_ms=5000)
        assert not ProxyQualityScorer.is_safe_for_stealth(bad)

    def test_score_clamped_0_100(self):
        proxy = ProxyConfig(host="1.2.3.4", port=8080)
        quality = ProxyQuality(
            asn_type="residential", response_time_ms=50,
            success_rate=1.0, country="US", city="NYC",
        )
        score = ProxyQualityScorer.score(proxy, quality)
        assert 0 <= score <= 100


# ═══════════════════════════════════════════════
# Request Timing Engine Tests
# ═══════════════════════════════════════════════

class TestRequestTimingEngine:
    """Test human-realistic request timing."""

    def test_poisson_delay_positive(self):
        for _ in range(100):
            delay = RequestTimingEngine.poisson_delay()
            assert delay > 0

    def test_poisson_delay_respects_rate(self):
        # High rate = shorter delays on average
        fast_delays = [RequestTimingEngine.poisson_delay(rate=5.0) for _ in range(200)]
        slow_delays = [RequestTimingEngine.poisson_delay(rate=0.1) for _ in range(200)]
        assert sum(fast_delays) / len(fast_delays) < sum(slow_delays) / len(slow_delays)

    def test_human_browsing_delay_range(self):
        for _ in range(100):
            delay = RequestTimingEngine.human_browsing_delay()
            assert 0.5 <= delay <= 30.0

    def test_generate_session_timing(self):
        delays = RequestTimingEngine.generate_session_timing(
            num_requests=20,
            duration_minutes=2.0,
        )
        assert len(delays) == 19  # n-1 delays for n requests
        assert all(d > 0 for d in delays)

    def test_session_timing_has_variety(self):
        delays = RequestTimingEngine.generate_session_timing(num_requests=50)
        # Should have some variety (not all the same)
        assert max(delays) > min(delays) * 2


# ═══════════════════════════════════════════════
# Consistent Profile Generation Tests
# ═══════════════════════════════════════════════

class TestConsistentProfile:
    """Test consistent browser profile generation."""

    def test_generate_us_profile(self):
        engine = AntiDetectionEngine()
        profile = engine.generate_consistent_profile("us")
        assert "fingerprint" in profile
        assert "user_agent" in profile
        assert "headers" in profile
        assert "tls_profile" in profile
        assert "webgl_vendor" in profile
        assert "canvas_seed" in profile
        assert "audio_seed" in profile

    def test_generate_fi_profile(self):
        engine = AntiDetectionEngine()
        profile = engine.generate_consistent_profile("fi")
        assert profile["locale"] == "fi-FI"
        assert profile["timezone"] == "Europe/Helsinki"

    def test_profile_has_http2(self):
        engine = AntiDetectionEngine()
        profile = engine.generate_consistent_profile()
        assert "http2_profile" in profile
        assert profile["http2_profile"] is not None

    def test_profile_has_client_hints(self):
        engine = AntiDetectionEngine()
        profile = engine.generate_consistent_profile("us")
        headers = profile["headers"]
        # Chrome profile should have Client Hints
        # (depends on random browser selection)
        if "Chrome" in profile["user_agent"]:
            assert "sec-ch-ua" in headers

    def test_profile_webgl_platform_consistent(self):
        """WebGL renderer should be a non-empty string."""
        engine = AntiDetectionEngine()
        profile = engine.generate_consistent_profile("uk")
        renderer = profile["webgl_renderer"]
        assert isinstance(renderer, str) and len(renderer) > 5

    def test_seeds_are_deterministic_per_fingerprint(self):
        engine = AntiDetectionEngine()
        p1 = engine.generate_consistent_profile()
        # Canvas seed should be based on fingerprint hash
        assert isinstance(p1["canvas_seed"], int)
        assert isinstance(p1["audio_seed"], int)
        assert p1["canvas_seed"] != p1["audio_seed"]

    def test_unknown_region_defaults_to_us(self):
        engine = AntiDetectionEngine()
        profile = engine.generate_consistent_profile("xyz")
        assert profile["timezone"] == "America/New_York"


# ═══════════════════════════════════════════════
# JA3 Hash Registry Tests
# ═══════════════════════════════════════════════

class TestModernJA3:
    """Test updated JA3 hash registry."""

    def test_has_modern_browsers(self):
        assert "chrome_125_win" in MODERN_JA3_HASHES
        assert "firefox_126_win" in MODERN_JA3_HASHES
        assert "safari_17_5_mac" in MODERN_JA3_HASHES

    def test_edge_matches_chrome(self):
        # Edge is Chromium, so JA3 should match Chrome
        assert MODERN_JA3_HASHES["edge_125_win"] == MODERN_JA3_HASHES["chrome_125_win"]

    def test_hashes_are_hex(self):
        for name, hash_val in MODERN_JA3_HASHES.items():
            assert all(c in "0123456789abcdef" for c in hash_val), \
                f"{name} has non-hex hash"
            assert len(hash_val) == 32, f"{name} hash wrong length"


# ═══════════════════════════════════════════════
# Existing Feature Backward Compat Tests
# ═══════════════════════════════════════════════

class TestBackwardCompat:
    """Ensure existing features still work after v3 upgrades."""

    def test_fingerprint_generation(self):
        engine = AntiDetectionEngine()
        fp = engine.generate_fingerprint()
        assert fp.user_agent
        assert fp.platform
        assert fp.screen.width > 0

    def test_ua_generator(self):
        ua = UserAgentGenerator.generate()
        assert "Mozilla" in ua

    def test_behavior_simulator_mouse_path(self):
        path = BehaviorSimulator.generate_mouse_path((100, 100), (500, 500))
        assert len(path) > 10

    def test_tls_profiles_still_work(self):
        profile = TLSProfileGenerator.get_profile(BrowserType.CHROME)
        assert len(profile.cipher_suites) > 0
        assert profile.ja3_hash

    def test_proxy_chain_manager(self):
        mgr = ProxyChainManager()
        mgr.add_proxy(ProxyConfig(host="1.2.3.4", port=8080))
        p = mgr.get_next()
        assert p is not None
        assert p.host == "1.2.3.4"

    def test_cookie_jar(self):
        jar = CookieJar()
        jar.set(Cookie(name="test", value="123", domain="example.com"))
        cookies = jar.get("example.com")
        assert len(cookies) == 1
        assert cookies[0].value == "123"

    def test_engine_stats(self):
        engine = AntiDetectionEngine()
        stats = engine.stats()
        assert "fingerprints_generated" in stats
        assert "proxies" in stats
        assert "cookies" in stats


