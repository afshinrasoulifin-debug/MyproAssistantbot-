
"""Tests for utils/request_pipeline.py — Intelligent Request Orchestration Engine."""

import time
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.request_pipeline import (
    AssetLoadSimulator,
    AssetRequest,
    CookieAccumulator,
    CookieProfile,
    DomainRateLimiter,
    DomainState,
    NavigationEntry,
    NavigationHistory,
    ReferrerChainBuilder,
    ReferrerSource,
    RequestPipeline,
    RequestPriority,
    ResourceType,
    RetryConfig,
    RetryEngine,
    request_pipeline,
)


# ═══════════════════════════════════════════════════════════
# DomainState Tests
# ═══════════════════════════════════════════════════════════

class TestDomainState:
    def test_initial_state(self):
        state = DomainState(domain="example.com")
        assert state.request_count == 0
        assert state.is_cooled_down

    def test_record_request(self):
        state = DomainState(domain="example.com")
        state.record_request(latency_ms=150, bytes_received=5000)
        assert state.request_count == 1
        assert state.total_bytes == 5000
        assert state.avg_latency_ms == 150

    def test_ema_latency(self):
        state = DomainState(domain="example.com")
        state.record_request(latency_ms=100)
        state.record_request(latency_ms=200)
        assert abs(state.avg_latency_ms - 120) < 0.01

    def test_fast_request_detection(self):
        state = DomainState(domain="example.com")
        state.record_request()
        state.last_request_time = time.time()
        state.record_request()
        assert state.consecutive_fast_requests >= 1

    def test_to_dict(self):
        state = DomainState(domain="example.com")
        state.record_request(latency_ms=100, bytes_received=1000)
        d = state.to_dict()
        assert d["domain"] == "example.com"
        assert d["request_count"] == 1


# ═══════════════════════════════════════════════════════════
# DomainRateLimiter Tests
# ═══════════════════════════════════════════════════════════

class TestDomainRateLimiter:
    def test_calculate_delay(self):
        limiter = DomainRateLimiter()
        delay = limiter.calculate_delay("example.com", ResourceType.DOCUMENT)
        assert delay > 0

    def test_css_faster_than_document(self):
        limiter = DomainRateLimiter()
        doc_delay = limiter.calculate_delay("example.com", ResourceType.DOCUMENT)
        css_delay = limiter.calculate_delay("cdn.example.com", ResourceType.STYLESHEET)
        assert doc_delay > 0 and css_delay > 0

    def test_record_429_triggers_rate_limit(self):
        limiter = DomainRateLimiter()
        limiter.record_request("example.com", status_code=429)
        state = limiter.get_domain_state("example.com")
        assert state.is_rate_limited

    def test_cookies(self):
        limiter = DomainRateLimiter()
        limiter.set_cookies("example.com", {"session": "abc123"})
        cookies = limiter.get_cookies("example.com")
        assert cookies["session"] == "abc123"

    def test_get_stats(self):
        limiter = DomainRateLimiter()
        limiter.record_request("example.com")
        stats = limiter.get_stats()
        assert stats["tracked_domains"] == 1
        assert "example.com" in stats["domains"]


# ═══════════════════════════════════════════════════════════
# ReferrerChainBuilder Tests
# ═══════════════════════════════════════════════════════════

class TestReferrerChainBuilder:
    def test_search_chain(self):
        chain = ReferrerChainBuilder.build_search_chain(
            "https://example.com/page",
            search_query="example page",
        )
        assert len(chain) == 2
        assert chain[0].source == ReferrerSource.DIRECT
        assert chain[1].source == ReferrerSource.SEARCH_ENGINE

    def test_search_chain_auto_query(self):
        chain = ReferrerChainBuilder.build_search_chain(
            "https://example.com/page"
        )
        assert len(chain) == 2

    def test_social_chain(self):
        chain = ReferrerChainBuilder.build_social_chain(
            "https://example.com/page", platform="facebook"
        )
        assert len(chain) == 1
        assert chain[0].source == ReferrerSource.SOCIAL_MEDIA
        assert "facebook" in chain[0].referrer

    def test_direct_chain(self):
        chain = ReferrerChainBuilder.build_direct_chain("https://example.com")
        assert len(chain) == 1
        assert chain[0].referrer == ""

    def test_internal_chain(self):
        pages = [
            "https://example.com/",
            "https://example.com/products",
            "https://example.com/products/1",
        ]
        chain = ReferrerChainBuilder.build_internal_chain(pages)
        assert len(chain) == 3
        assert chain[0].source == ReferrerSource.DIRECT
        assert chain[1].source == ReferrerSource.INTERNAL
        assert chain[1].referrer == pages[0]

    def test_select_entry_method(self):
        methods = set()
        for _ in range(200):
            methods.add(ReferrerChainBuilder.select_entry_method())
        assert len(methods) >= 3

    def test_navigation_entry_to_dict(self):
        entry = NavigationEntry(
            url="https://example.com",
            referrer="https://google.com",
            source=ReferrerSource.SEARCH_ENGINE,
        )
        d = entry.to_dict()
        assert d["url"] == "https://example.com"
        assert d["source"] == "search"


# ═══════════════════════════════════════════════════════════
# AssetLoadSimulator Tests
# ═══════════════════════════════════════════════════════════

class TestAssetLoadSimulator:
    def test_generate_loading_sequence(self):
        assets = AssetLoadSimulator.generate_loading_sequence(
            "https://example.com", "landing_page"
        )
        assert len(assets) > 10
        assert assets[0].resource_type == ResourceType.DOCUMENT
        assert assets[0].priority == RequestPriority.HIGHEST

    def test_ecommerce_more_images(self):
        ecom = AssetLoadSimulator.generate_loading_sequence(
            "https://shop.com", "e_commerce"
        )
        article = AssetLoadSimulator.generate_loading_sequence(
            "https://blog.com", "article"
        )
        ecom_imgs = [a for a in ecom if a.resource_type == ResourceType.IMAGE]
        article_imgs = [a for a in article if a.resource_type == ResourceType.IMAGE]
        assert len(ecom_imgs) >= len(article_imgs)

    def test_assets_have_delays(self):
        assets = AssetLoadSimulator.generate_loading_sequence(
            "https://example.com", "spa"
        )
        for a in assets[1:]:
            assert a.delay_ms > 0

    def test_xhr_sequence(self):
        requests = AssetLoadSimulator.generate_xhr_sequence(
            "https://example.com", count=3
        )
        assert len(requests) == 3
        assert all(r.resource_type == ResourceType.XHR for r in requests)

    def test_asset_to_dict(self):
        asset = AssetRequest(
            url="https://example.com/style.css",
            resource_type=ResourceType.STYLESHEET,
            priority=RequestPriority.HIGH,
        )
        d = asset.to_dict()
        assert d["type"] == "stylesheet"
        assert d["priority"] == "high"


# ═══════════════════════════════════════════════════════════
# CookieAccumulator Tests
# ═══════════════════════════════════════════════════════════

class TestCookieAccumulator:
    def test_new_user_cookies(self):
        profile = CookieAccumulator.generate_new_user_cookies()
        assert profile.total_cookies <= 2

    def test_returning_user_cookies(self):
        profile = CookieAccumulator.generate_returning_user_cookies(10)
        assert profile.total_domains > 0
        assert profile.total_cookies > 0

    def test_cookie_profile_operations(self):
        profile = CookieProfile()
        profile.add_cookies(".example.com", {"session": "abc"})
        assert profile.has_visited(".example.com")
        assert profile.get_cookies(".example.com")["session"] == "abc"
        assert profile.total_domains == 1
        assert profile.total_cookies == 1

    def test_cookie_profile_to_dict(self):
        profile = CookieProfile()
        profile.add_cookies(".example.com", {"a": "1", "b": "2"})
        d = profile.to_dict()
        assert d["total_domains"] == 1
        assert d["total_cookies"] == 2


# ═══════════════════════════════════════════════════════════
# NavigationHistory Tests
# ═══════════════════════════════════════════════════════════

class TestNavigationHistory:
    def test_navigate(self):
        history = NavigationHistory()
        history.navigate(NavigationEntry(url="https://a.com"))
        assert history.length == 1
        assert history.current.url == "https://a.com"

    def test_back_forward(self):
        history = NavigationHistory()
        history.navigate(NavigationEntry(url="https://a.com"))
        history.navigate(NavigationEntry(url="https://b.com"))
        assert history.can_go_back()
        entry = history.go_back()
        assert entry.url == "https://a.com"
        assert history.can_go_forward()
        entry = history.go_forward()
        assert entry.url == "https://b.com"

    def test_navigate_clears_forward(self):
        history = NavigationHistory()
        history.navigate(NavigationEntry(url="https://a.com"))
        history.navigate(NavigationEntry(url="https://b.com"))
        history.go_back()
        history.navigate(NavigationEntry(url="https://c.com"))
        assert not history.can_go_forward()

    def test_max_entries(self):
        history = NavigationHistory(max_entries=5)
        for i in range(10):
            history.navigate(NavigationEntry(url=f"https://site{i}.com"))
        assert history.length == 5

    def test_to_dict(self):
        history = NavigationHistory()
        history.navigate(NavigationEntry(url="https://a.com"))
        d = history.to_dict()
        assert d["length"] == 1
        assert d["current_url"] == "https://a.com"


# ═══════════════════════════════════════════════════════════
# RetryEngine Tests
# ═══════════════════════════════════════════════════════════

class TestRetryEngine:
    def test_should_retry_429(self):
        engine = RetryEngine()
        assert engine.should_retry("https://a.com", 429)

    def test_should_not_retry_200(self):
        engine = RetryEngine()
        assert not engine.should_retry("https://a.com", 200)

    def test_max_retries_respected(self):
        engine = RetryEngine(RetryConfig(max_retries=2))
        engine.record_retry("https://a.com")
        engine.record_retry("https://a.com")
        assert not engine.should_retry("https://a.com", 429)

    def test_exponential_backoff(self):
        engine = RetryEngine(RetryConfig(base_delay_seconds=1.0, jitter=0.0))
        d1 = engine.get_retry_delay("https://a.com")
        engine.record_retry("https://a.com")
        d2 = engine.get_retry_delay("https://a.com")
        assert d2 > d1

    def test_retry_strategy(self):
        engine = RetryEngine()
        strategy = engine.get_retry_strategy("https://a.com")
        assert strategy["attempt"] == 1
        assert strategy["remaining_retries"] == 3

    def test_reset(self):
        engine = RetryEngine()
        engine.record_retry("https://a.com")
        engine.reset("https://a.com")
        assert engine.should_retry("https://a.com", 429)

    def test_get_stats(self):
        engine = RetryEngine()
        engine.record_retry("https://a.com")
        stats = engine.get_stats()
        assert stats["total_retries"] == 1


# ═══════════════════════════════════════════════════════════
# RequestPipeline (Main) Tests
# ═══════════════════════════════════════════════════════════

class TestRequestPipeline:
    def test_singleton(self):
        assert request_pipeline is not None

    def test_version(self):
        assert "TITAN" in RequestPipeline.VERSION

    def test_build_referrer_chain_search(self):
        pipeline = RequestPipeline()
        chain = pipeline.build_referrer_chain(
            "https://example.com", source="search"
        )
        assert len(chain) >= 1

    def test_build_referrer_chain_direct(self):
        pipeline = RequestPipeline()
        chain = pipeline.build_referrer_chain(
            "https://example.com", source="direct"
        )
        assert len(chain) == 1
        assert chain[0].referrer == ""

    def test_generate_page_load(self):
        pipeline = RequestPipeline()
        assets = pipeline.generate_page_load("https://example.com", "landing_page")
        assert len(assets) > 5

    def test_get_delay(self):
        pipeline = RequestPipeline()
        delay = pipeline.get_delay("example.com")
        assert delay > 0

    def test_record_request_with_cookies(self):
        pipeline = RequestPipeline()
        pipeline.record_request(
            "example.com", latency_ms=100,
            cookies={"session": "abc"}
        )
        assert pipeline.cookies.has_visited(".example.com")

    def test_should_retry(self):
        pipeline = RequestPipeline()
        assert pipeline.should_retry("https://a.com", 429)
        assert not pipeline.should_retry("https://a.com", 200)

    def test_history(self):
        pipeline = RequestPipeline()
        pipeline.build_referrer_chain("https://example.com", source="direct")
        assert pipeline.history.length >= 1

    def test_get_stats(self):
        pipeline = RequestPipeline()
        pipeline.record_request("example.com")
        stats = pipeline.get_stats()
        assert stats["total_requests"] == 1
        assert "rate_limiter" in stats
        assert "retry" in stats
        assert "cookies" in stats


