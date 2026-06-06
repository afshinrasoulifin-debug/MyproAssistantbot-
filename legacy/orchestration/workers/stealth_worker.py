
"""
orchestration/workers/stealth_worker.py — Enterprise Stealth Browser Engine v3.0-TITAN
══════════════════════════════════════════════════════════════════════════════════════════
Military-grade undetectable browser automation engine.

 1. Multi-engine support (Chromium, Firefox, WebKit) with auto-fallback
 2. 18-vector evasion script arsenal (via utils/evasion_scripts.py)
 3. Consistent fingerprint stack validation (UA↔Platform↔GPU↔Headers)
 4. Human behavior simulation (Bézier mouse, variable typing, scroll patterns)
 5. Persistent session integration (sessions/session_store, AES-256 encrypted)
 6. Cloudflare Turnstile/JS Challenge/Managed Challenge bypass pipeline
 7. CAPTCHA detection + multi-solver routing (2captcha, hcaptcha, reCAPTCHA, Turnstile)
 8. WAF detection (Cloudflare, Akamai, PerimeterX, DataDome, Kasada) + adaptive response
 9. Per-context proxy support (residential scoring, rotation)
10. Request interception + header rewriting + Client Hints injection
11. Screenshot + DOM evidence capture
12. Worker pool for parallel stealth operations
13. Health monitoring + exponential backoff retry + circuit breaker

Author: Arki Engine TITAN
License: Proprietary
"""

# NOTE: Consider using arki_project.utils.feature_registry for optional imports
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Final, List, Optional, Tuple

logger = logging.getLogger("arki.worker.stealth")

# ── Optional dependency imports ──
try:
    from playwright.async_api import (
        async_playwright, Browser, BrowserContext, BrowserType as PWBrowserType,
        Page, Playwright, Route, Request as PWRequest, Response as PWResponse,
    )
    PLAYWRIGHT_AVAILABLE: Final[bool] = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from playwright_stealth import stealth_async
    STEALTH_PLUGIN_AVAILABLE: Final[bool] = True
except ImportError:
    STEALTH_PLUGIN_AVAILABLE = False

# Anti-detection integration
try:
    from arki_project.utils.anti_detection import (
        AntiDetectionEngine, BrowserFingerprint,
        UserAgentGenerator, BehaviorSimulator, HeaderBuilder,
        BrowserType as ADBrowserType, Platform,
        ProxyQualityScorer, ProxyQuality, RequestTimingEngine,
        WEBGL_RENDERERS_EXTENDED, H2_PROFILES, MODERN_JA3_HASHES,
    )
    _ANTI_DETECT_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.anti_detection import (
            AntiDetectionEngine, BrowserFingerprint,
            UserAgentGenerator, BehaviorSimulator, HeaderBuilder,
            BrowserType as ADBrowserType, Platform,
            ProxyQualityScorer, ProxyQuality, RequestTimingEngine,
            WEBGL_RENDERERS_EXTENDED, H2_PROFILES, MODERN_JA3_HASHES,
        )
        _ANTI_DETECT_AVAILABLE = True
    except ImportError:
        _ANTI_DETECT_AVAILABLE = False

# Evasion scripts arsenal
try:
    from arki_project.utils.evasion_scripts import EvasionScriptBuilder
    _EVASION_SCRIPTS_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.evasion_scripts import EvasionScriptBuilder
        _EVASION_SCRIPTS_AVAILABLE = True
    except ImportError:
        _EVASION_SCRIPTS_AVAILABLE = False

# Session persistence integration
try:
    from arki_project.sessions.session_store import (
        get_session_store, SessionStore, BrowserSession, SessionState,
    )
    _SESSION_STORE_AVAILABLE: bool = True
except ImportError:
    try:
        from sessions.session_store import (
            get_session_store, SessionStore, BrowserSession, SessionState,
        )
        _SESSION_STORE_AVAILABLE = True
    except ImportError:
        _SESSION_STORE_AVAILABLE = False

# ── v3.0 TITAN Phase 2: Advanced bypass infrastructure ──

# TLS Fingerprint Engine
try:
    from arki_project.utils.tls_fingerprint import (
        TLSFingerprintEngine, tls_engine as _tls_engine,
    )
    _TLS_FINGERPRINT_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.tls_fingerprint import (
            TLSFingerprintEngine, tls_engine as _tls_engine,
        )
        _TLS_FINGERPRINT_AVAILABLE = True
    except ImportError:
        _TLS_FINGERPRINT_AVAILABLE = False
        _tls_engine = None

# HTTP/2 Transport Fingerprint
try:
    from arki_project.utils.h2_transport import (
        H2ProfileSelector, H2SettingsBuilder, h2_profile_selector as _h2_selector,
    )
    _H2_TRANSPORT_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.h2_transport import (
            H2ProfileSelector, H2SettingsBuilder, h2_profile_selector as _h2_selector,
        )
        _H2_TRANSPORT_AVAILABLE = True
    except ImportError:
        _H2_TRANSPORT_AVAILABLE = False
        _h2_selector = None

# Browser Validator
try:
    from arki_project.utils.browser_validator import (
        BrowserValidator, browser_validator as _browser_validator,
        ValidationReport, CheckStatus,
    )
    _BROWSER_VALIDATOR_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.browser_validator import (
            BrowserValidator, browser_validator as _browser_validator,
            ValidationReport, CheckStatus,
        )
        _BROWSER_VALIDATOR_AVAILABLE = True
    except ImportError:
        _BROWSER_VALIDATOR_AVAILABLE = False
        _browser_validator = None

# Proxy Pool Manager
try:
    from arki_project.utils.proxy_pool import (
        ProxyPool, ProxyEntry as PoolProxyEntry, RotationStrategy, proxy_pool as _proxy_pool,
    )
    _PROXY_POOL_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.proxy_pool import (
            ProxyPool, ProxyEntry as PoolProxyEntry, RotationStrategy, proxy_pool as _proxy_pool,
        )
        _PROXY_POOL_AVAILABLE = True
    except ImportError:
        _PROXY_POOL_AVAILABLE = False
        _proxy_pool = None

# Browser Profile Persistence
try:
    from arki_project.sessions.browser_profile import (
        ProfileManager, ProfileCapturer, ProfileRestorer,
        BrowserProfile, profile_manager as _profile_manager,
    )
    _BROWSER_PROFILE_AVAILABLE: bool = True
except ImportError:
    try:
        from sessions.browser_profile import (
            ProfileManager, ProfileCapturer, ProfileRestorer,
            BrowserProfile, profile_manager as _profile_manager,
        )
        _BROWSER_PROFILE_AVAILABLE = True
    except ImportError:
        _BROWSER_PROFILE_AVAILABLE = False
        _profile_manager = None

# ── v3.0 TITAN Phase 3: Operational Intelligence Layer ──

# Geographic Consistency Engine
try:
    from arki_project.utils.geo_consistency import (
        GeoConsistencyEngine, geo_engine as _geo_engine,
        GEO_DATABASE, Region,
    )
    _GEO_CONSISTENCY_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.geo_consistency import (
            GeoConsistencyEngine, geo_engine as _geo_engine,
            GEO_DATABASE, Region,
        )
        _GEO_CONSISTENCY_AVAILABLE = True
    except ImportError:
        _GEO_CONSISTENCY_AVAILABLE = False
        _geo_engine = None

# Behavioral Intelligence Engine
try:
    from arki_project.utils.behavior_engine import (
        BehaviorEngine as BehaviorIntelEngine,
        behavior_engine as _behavior_engine,
        BrowsingIntent, ScrollPattern,
    )
    _BEHAVIOR_ENGINE_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.behavior_engine import (
            BehaviorEngine as BehaviorIntelEngine,
            behavior_engine as _behavior_engine,
            BrowsingIntent, ScrollPattern,
        )
        _BEHAVIOR_ENGINE_AVAILABLE = True
    except ImportError:
        _BEHAVIOR_ENGINE_AVAILABLE = False
        _behavior_engine = None

# Request Pipeline Engine
try:
    from arki_project.utils.request_pipeline import (
        RequestPipeline as ReqPipeline,
        request_pipeline as _request_pipeline,
        ResourceType, ReferrerSource,
    )
    _REQUEST_PIPELINE_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.request_pipeline import (
            RequestPipeline as ReqPipeline,
            request_pipeline as _request_pipeline,
            ResourceType, ReferrerSource,
        )
        _REQUEST_PIPELINE_AVAILABLE = True
    except ImportError:
        _REQUEST_PIPELINE_AVAILABLE = False
        _request_pipeline = None

# Unified Fingerprint Engine
try:
    from arki_project.utils.fingerprint_engine import (
        FingerprintEngine as FPEngine,
        fingerprint_engine as _fingerprint_engine,
        OSType, BrowserFamily,
    )
    _FINGERPRINT_ENGINE_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.fingerprint_engine import (
            FingerprintEngine as FPEngine,
            fingerprint_engine as _fingerprint_engine,
            OSType, BrowserFamily,
        )
        _FINGERPRINT_ENGINE_AVAILABLE = True
    except ImportError:
        _FINGERPRINT_ENGINE_AVAILABLE = False
        _fingerprint_engine = None

# Advanced Captcha Intelligence Engine
try:
    from arki_project.utils.captcha_engine import (
        CaptchaEngine as CaptchaIntelEngine,
        captcha_engine as _captcha_intel_engine,
        CaptchaFamily, SolverProvider, SolverConfig, SolveRequest,
    )
    _CAPTCHA_INTEL_AVAILABLE: bool = True
except ImportError:
    try:
        from utils.captcha_engine import (
            CaptchaEngine as CaptchaIntelEngine,
            captcha_engine as _captcha_intel_engine,
            CaptchaFamily, SolverProvider, SolverConfig, SolveRequest,
        )
        _CAPTCHA_INTEL_AVAILABLE = True
    except ImportError:
        _CAPTCHA_INTEL_AVAILABLE = False
        _captcha_intel_engine = None


# ═══════════════════════════════════════════════════════════
# Constants & Configuration
# ═══════════════════════════════════════════════════════════

class BrowserEngine(Enum):
    """Supported browser engines for stealth operations."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class CaptchaType(Enum):
    """Detected CAPTCHA types."""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE_TURNSTILE = "turnstile"
    CLOUDFLARE_CHALLENGE = "cf_challenge"
    FUNCAPTCHA = "funcaptcha"
    UNKNOWN = "unknown"


class BypassResult(Enum):
    """Outcome of a bypass attempt."""
    SUCCESS = "success"
    CAPTCHA_DETECTED = "captcha_detected"
    CLOUDFLARE_BLOCKED = "cloudflare_blocked"
    TIMEOUT = "timeout"
    BROWSER_ERROR = "browser_error"
    NETWORK_ERROR = "network_error"
    RETRY_NEEDED = "retry_needed"


@dataclass
class StealthConfig:
    """Configuration for a stealth session."""
    engine: BrowserEngine = BrowserEngine.CHROMIUM
    headless: bool = True
    timeout_ms: int = 60000
    navigation_timeout_ms: int = 30000
    # Fingerprint
    inject_canvas_noise: bool = True
    inject_webgl_noise: bool = True
    inject_audio_noise: bool = True
    randomize_viewport: bool = True
    randomize_locale: bool = True
    randomize_timezone: bool = True
    # Behavior
    simulate_human_behavior: bool = True
    min_page_dwell_ms: int = 3000
    max_page_dwell_ms: int = 8000
    # Network
    block_trackers: bool = True
    block_images: bool = False   # Keep images for CAPTCHA detection
    intercept_requests: bool = True
    # Retry
    max_retries: int = 3
    retry_delay_base: float = 5.0
    # Capture
    capture_screenshots: bool = True
    capture_dom: bool = False
    screenshots_dir: str = "sessions/screenshots"
    # Proxy (per-context)
    proxy_url: Optional[str] = None   # e.g. "socks5://user:pass@host:port"
    proxy_bypass: str = ""            # Bypass list (comma-separated domains)
    # WAF-aware behavior
    waf_adaptive: bool = True         # Auto-adapt to detected WAF
    use_evasion_arsenal: bool = True   # Use full 18-script evasion (vs legacy 4)


# ═══════════════════════════════════════════════════════════
# Legacy fallback scripts (used when evasion_scripts module unavailable)
# ═══════════════════════════════════════════════════════════

WEBDRIVER_HIDE_SCRIPT: Final[str] = """
(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    delete navigator.__proto__.webdriver;
    const props = ['__playwright','_selenium','__webdriver_evaluate','ChromeDriverw'];
    props.forEach(p => { try { delete window[p]; } catch(e) {} });
    window.chrome = { runtime: {}, loadTimes: () => ({}), csi: () => ({}) };
})();
"""

CANVAS_NOISE_SCRIPT: Final[str] = """
(() => {
    const orig = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const ctx = this.getContext('2d');
        if (ctx) {
            try {
                const d = ctx.getImageData(0,0,this.width,this.height);
                for(let i=0;i<d.data.length;i+=4) d.data[i]+=(Math.random()*2-1);
                ctx.putImageData(d,0,0);
            } catch(e) {}
        }
        return orig.apply(this, arguments);
    };
})();
"""

WEBGL_NOISE_SCRIPT: Final[str] = """
(() => {
    const g = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(p) {
        if(p===37445) return 'Intel Inc.';
        if(p===37446) return 'Intel Iris OpenGL Engine';
        return g.apply(this,arguments);
    };
})();
"""

AUDIO_NOISE_SCRIPT: Final[str] = """
(() => {
    const o = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function() {
        const osc = o.apply(this,arguments);
        const c = osc.connect;
        osc.connect = function(d) {
            if(d instanceof AnalyserNode) {
                const g = this.context.createGain();
                g.gain.value = 1+(Math.random()*0.0001-0.00005);
                c.call(this,g); g.connect(d); return d;
            }
            return c.apply(this,arguments);
        };
        return osc;
    };
})();
"""

# ── Tracker block patterns ──
TRACKER_PATTERNS: Final[List[str]] = [
    "*google-analytics.com*", "*googletagmanager.com*",
    "*facebook.net/tr*", "*analytics*", "*hotjar.com*",
    "*sentry.io*", "*mixpanel.com*", "*segment.io*",
    "*doubleclick.net*", "*adservice.google*",
    "*tiktokapi.com*", "*ads-twitter.com*",
]

# ── User agent pool ──
USER_AGENTS: Final[List[str]] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.76 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.76 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.76 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.76 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

# ── Viewport profiles ──
VIEWPORT_PROFILES: Final[List[Dict[str, int]]] = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 2560, "height": 1440},
    {"width": 1680, "height": 1050},
]

TIMEZONES: Final[List[str]] = [
    "Europe/Helsinki", "Europe/London", "America/New_York",
    "America/Los_Angeles", "Europe/Berlin", "Asia/Tokyo",
]

LOCALES: Final[List[str]] = [
    "en-US", "en-GB", "fi-FI", "de-DE", "fr-FR", "ja-JP",
]


# ═══════════════════════════════════════════════════════════
# WAF Detection Engine
# ═══════════════════════════════════════════════════════════

class WAFType(Enum):
    """Known WAF providers."""
    CLOUDFLARE = "cloudflare"
    AKAMAI = "akamai"
    PERIMETERX = "perimeterx"
    DATADOME = "datadome"
    KASADA = "kasada"
    IMPERVA = "imperva"
    SUCURI = "sucuri"
    AWS_WAF = "aws_waf"
    UNKNOWN = "unknown"


class WAFDetector:
    """
    Detect which WAF/bot-protection is active on a page.

    Detection is performed via response headers, cookies, and page content
    markers. Knowing the WAF allows the bypass pipeline to use the right
    strategy (e.g., Cloudflare needs JS challenge wait, DataDome needs
    behavioral simulation, PerimeterX needs canvas/WebGL consistency).
    """

    # Header signatures
    HEADER_SIGNATURES: Final[Dict[WAFType, List[str]]] = {
        WAFType.CLOUDFLARE: ["cf-ray", "cf-cache-status", "cf-request-id"],
        WAFType.AKAMAI: ["x-akamai-transformed", "akamai-grn", "x-akamai-session-info"],
        WAFType.DATADOME: ["x-datadome", "x-dd-b", "x-dd-type"],
        WAFType.IMPERVA: ["x-iinfo", "x-cdn"],
        WAFType.SUCURI: ["x-sucuri-id", "x-sucuri-cache"],
        WAFType.AWS_WAF: ["x-amzn-requestid", "x-amz-cf-id"],
    }

    # Cookie signatures
    COOKIE_SIGNATURES: Final[Dict[WAFType, List[str]]] = {
        WAFType.CLOUDFLARE: ["__cf_bm", "cf_clearance", "_cfuvid"],
        WAFType.DATADOME: ["datadome"],
        WAFType.PERIMETERX: ["_px3", "_pxvid", "_px"],
        WAFType.KASADA: ["__kpsdk_ct", "kpsdk-im", "kpsdk-cd"],
        WAFType.AKAMAI: ["_abck", "ak_bmsc", "bm_sz"],
        WAFType.IMPERVA: ["visid_incap_", "incap_ses_"],
    }

    # HTML content markers
    CONTENT_SIGNATURES: Final[Dict[WAFType, List[str]]] = {
        WAFType.CLOUDFLARE: ["cf-challenge-running", "cf-turnstile", "challenges.cloudflare.com"],
        WAFType.PERIMETERX: ["_pxAppId", "perimeterx.com", "px-captcha"],
        WAFType.DATADOME: ["datadome.co", "dd.js"],
        WAFType.KASADA: ["ips.js", "ips-d.kasada.io"],
        WAFType.AKAMAI: ["_abck", "akamaized.net"],
    }

    @classmethod
    async def detect(cls, page: int, response: Optional[Any]=None) -> List[WAFType]:
        """Detect all active WAFs on the current page."""
        detected: List[WAFType] = []

        try:
            # Check response headers
            if response:
                headers = response.headers
                for waf_type, sigs in cls.HEADER_SIGNATURES.items():
                    if any(sig in headers for sig in sigs):
                        if waf_type not in detected:
                            detected.append(waf_type)

            # Check cookies
            try:
                cookies = await page.context.cookies()
                cookie_names = {c["name"] for c in cookies}
                for waf_type, sigs in cls.COOKIE_SIGNATURES.items():
                    if any(sig in name for sig in sigs for name in cookie_names):
                        if waf_type not in detected:
                            detected.append(waf_type)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

            # Check HTML content
            try:
                html = await page.content()
                for waf_type, sigs in cls.CONTENT_SIGNATURES.items():
                    if any(sig in html for sig in sigs):
                        if waf_type not in detected:
                            detected.append(waf_type)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        except Exception as e:
            logger.debug("WAF detection error: %s", e)

        if detected:
            logger.info("🛡️ WAF detected: %s", [w.value for w in detected])
        return detected

    @classmethod
    def recommend_strategy(cls, waf_types: List[WAFType]) -> Dict[str, Any]:
        """Recommend bypass strategy based on detected WAFs."""
        strategy: Dict[str, Any] = {
            "use_full_evasion": True,
            "extra_wait_seconds": 0,
            "simulate_behavior_duration": 5.0,
            "use_residential_proxy": False,
            "retry_with_different_engine": False,
        }

        for waf in waf_types:
            if waf == WAFType.CLOUDFLARE:
                strategy["extra_wait_seconds"] = max(strategy["extra_wait_seconds"], 10)
                strategy["simulate_behavior_duration"] = max(strategy["simulate_behavior_duration"], 8.0)
            elif waf == WAFType.DATADOME:
                strategy["simulate_behavior_duration"] = max(strategy["simulate_behavior_duration"], 12.0)
                strategy["use_residential_proxy"] = True
            elif waf == WAFType.PERIMETERX:
                strategy["use_full_evasion"] = True
                strategy["simulate_behavior_duration"] = max(strategy["simulate_behavior_duration"], 10.0)
            elif waf == WAFType.KASADA:
                strategy["use_residential_proxy"] = True
                strategy["retry_with_different_engine"] = True
            elif waf == WAFType.AKAMAI:
                strategy["extra_wait_seconds"] = max(strategy["extra_wait_seconds"], 5)
                strategy["simulate_behavior_duration"] = max(strategy["simulate_behavior_duration"], 7.0)

        return strategy


# ═══════════════════════════════════════════════════════════
# Browser Stack Consistency Validator
# ═══════════════════════════════════════════════════════════

class StackValidator:
    """
    Validate that UA, platform, GPU, headers, and fingerprint are
    internally consistent. Inconsistency is the #1 detection vector.

    Example: UA says Chrome/Windows but WebGL says "Apple M2" → instant block.
    """

    @staticmethod
    def validate(
        user_agent: str,
        platform_str: str,
        webgl_renderer: str,
        webgl_vendor: str,
    ) -> List[str]:
        """Return list of inconsistencies (empty = good)."""
        issues = []

        ua_lower = user_agent.lower()

        # Platform checks
        if "windows" in ua_lower:
            if "apple" in webgl_renderer.lower() and "ANGLE" not in webgl_renderer:
                issues.append("UA=Windows but WebGL says Apple GPU")
            if "mesa" in webgl_renderer.lower():
                issues.append("UA=Windows but WebGL says Mesa (Linux)")
            if platform_str not in ("Windows", "Win32"):
                issues.append(f"UA=Windows but platform={platform_str}")

        elif "macintosh" in ua_lower or "mac os" in ua_lower:
            if "direct3d" in webgl_renderer.lower():
                issues.append("UA=macOS but WebGL says Direct3D (Windows)")
            if platform_str not in ("macOS", "MacIntel"):
                issues.append(f"UA=macOS but platform={platform_str}")

        elif "linux" in ua_lower:
            if "direct3d" in webgl_renderer.lower():
                issues.append("UA=Linux but WebGL says Direct3D (Windows)")
            if "apple" in webgl_renderer.lower():
                issues.append("UA=Linux but WebGL says Apple GPU")
            if platform_str not in ("Linux", "Linux x86_64"):
                issues.append(f"UA=Linux but platform={platform_str}")

        # Vendor consistency
        if "chrome" in ua_lower and "Google" not in webgl_vendor and "Mesa" not in webgl_vendor:
            issues.append(f"UA=Chrome but WebGL vendor={webgl_vendor}")

        return issues


# ═══════════════════════════════════════════════════════════
# CAPTCHA Detection & Bypass
# ═══════════════════════════════════════════════════════════

class CaptchaDetector:
    """Detects CAPTCHA/challenge type from page content."""

    # Patterns for detection
    CF_CHALLENGE_MARKERS: Final[List[str]] = [
        "cf-challenge-running", "cf-turnstile", "challenge-platform",
        "cf-chl-widget", "cf_chl_opt", "jschl_vc", "jschl_answer",
    ]
    RECAPTCHA_MARKERS: Final[List[str]] = [
        "g-recaptcha", "recaptcha/api", "grecaptcha",
    ]
    HCAPTCHA_MARKERS: Final[List[str]] = [
        "h-captcha", "hcaptcha.com",
    ]
    TURNSTILE_MARKERS: Final[List[str]] = [
        "cf-turnstile", "challenges.cloudflare.com/turnstile",
    ]

    @classmethod
    async def detect(cls, page: int) -> Optional[CaptchaType]:
        """Detect CAPTCHA type on the current page."""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        try:
            html = await page.content()
            url = page.url

            # Cloudflare challenge page
            if any(m in html for m in cls.CF_CHALLENGE_MARKERS):
                if any(m in html for m in cls.TURNSTILE_MARKERS):
                    return CaptchaType.CLOUDFLARE_TURNSTILE
                return CaptchaType.CLOUDFLARE_CHALLENGE

            # reCAPTCHA
            if any(m in html for m in cls.RECAPTCHA_MARKERS):
                if "recaptcha/api.js?render=" in html:
                    return CaptchaType.RECAPTCHA_V3
                return CaptchaType.RECAPTCHA_V2

            # hCaptcha
            if any(m in html for m in cls.HCAPTCHA_MARKERS):
                return CaptchaType.HCAPTCHA

            return None
        except Exception:
            return None


class CloudflareBypass:
    """
    Specialized Cloudflare challenge bypass.

    Strategy pipeline:
    1. Wait for JS challenge auto-solve (5-15 seconds)
    2. Detect Turnstile widget and trigger click
    3. Cookie extraction after challenge pass
    4. Session persistence for future requests
    """

    MAX_WAIT_SECONDS: Final[int] = 30
    CHECK_INTERVAL: Final[float] = 1.0

    @classmethod
    async def attempt_bypass(cls, page: int, config: StealthConfig) -> BypassResult:
        """Attempt to bypass Cloudflare protection."""
        logger.info("☁️  Cloudflare challenge detected — initiating bypass pipeline")

        start = time.time()
        while (time.time() - start) < cls.MAX_WAIT_SECONDS:
            # Check if challenge is resolved
            try:
                html = await page.content()

                # JS challenge auto-completes
                if "cf-challenge-running" not in html and "jschl_vc" not in html:
                    if "cf-turnstile" not in html:
                        logger.info("✅ Cloudflare JS challenge auto-resolved in %.1fs",
                                    time.time() - start)
                        return BypassResult.SUCCESS

                # Try clicking Turnstile checkbox if present
                turnstile = await page.query_selector('input[type="checkbox"][name="cf-turnstile-response"]')
                if turnstile:
                    await cls._simulate_human_click(page, turnstile)
                    await asyncio.sleep(random.uniform(2.0, 4.0))

                # Check for iframe-based challenge
                frames = page.frames
                for frame in frames:
                    if "challenges.cloudflare.com" in (frame.url or ""):
                        checkbox = await frame.query_selector('input[type="checkbox"]')
                        if checkbox:
                            await cls._simulate_human_click_frame(frame, checkbox)
                            await asyncio.sleep(random.uniform(2.0, 4.0))

            except Exception as e:
                logger.debug("CF bypass check error: %s", e)

            await asyncio.sleep(cls.CHECK_INTERVAL)

        logger.warning("⏰ Cloudflare bypass timed out after %ds", cls.MAX_WAIT_SECONDS)
        return BypassResult.CLOUDFLARE_BLOCKED

    @classmethod
    async def _simulate_human_click(cls, page: int, element: Any) -> None:
        """Click with human-like behavior."""
        try:
            box = await element.bounding_box()
            if box:
                x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
                y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
                await page.mouse.move(x, y, steps=random.randint(5, 15))
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await page.mouse.click(x, y)
        except Exception as e:
            logger.debug("Human click failed: %s", e)
            try:
                await element.click()
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

    @classmethod
    async def _simulate_human_click_frame(cls, frame: Any, element: Any) -> None:
        """Click within an iframe."""
        try:
            await element.click()
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)


class CaptchaBypass:
    """
    Multi-solver CAPTCHA bypass router.

    Supports:
    - Cloudflare Turnstile (wait + click)
    - reCAPTCHA v2 (audio challenge or external solver API)
    - reCAPTCHA v3 (score manipulation via behavioral simulation)
    - hCaptcha (external solver API)

    External solver integration points:
    - 2captcha API
    - Anti-Captcha API
    - CapMonster Cloud
    """

    # External solver config (set via environment)
    SOLVER_API_KEY: Final[str] = os.environ.get("CAPTCHA_SOLVER_API_KEY", "")
    SOLVER_SERVICE: Final[str] = os.environ.get("CAPTCHA_SOLVER_SERVICE", "2captcha")

    @classmethod
    async def solve(cls, page: int, captcha_type: CaptchaType) -> BypassResult:
        """Route to the appropriate solver."""
        solvers = {
            CaptchaType.CLOUDFLARE_TURNSTILE: cls._solve_turnstile,
            CaptchaType.CLOUDFLARE_CHALLENGE: cls._solve_cf_challenge,
            CaptchaType.RECAPTCHA_V2: cls._solve_recaptcha_v2,
            CaptchaType.RECAPTCHA_V3: cls._solve_recaptcha_v3,
            CaptchaType.HCAPTCHA: cls._solve_hcaptcha,
        }

        solver = solvers.get(captcha_type, cls._solve_generic)
        return await solver(page)

    @classmethod
    async def _solve_turnstile(cls, page: int) -> BypassResult:
        """Solve Cloudflare Turnstile — mostly behavioral."""
        return await CloudflareBypass.attempt_bypass(page, StealthConfig())

    @classmethod
    async def _solve_cf_challenge(cls, page: int) -> BypassResult:
        """Solve generic Cloudflare challenge — JS wait."""
        return await CloudflareBypass.attempt_bypass(page, StealthConfig())

    @classmethod
    async def _solve_recaptcha_v2(cls, page: int) -> BypassResult:
        """Attempt reCAPTCHA v2 solve via external service or audio."""
        if cls.SOLVER_API_KEY:
            return await cls._external_solve(page, "recaptcha_v2")
        # Fallback: try audio challenge
        logger.info("🔊 Attempting reCAPTCHA v2 audio challenge...")
        try:
            # Find recaptcha iframe
            frames = page.frames
            for frame in frames:
                if "recaptcha" in (frame.url or ""):
                    audio_btn = await frame.query_selector("#recaptcha-audio-button")
                    if audio_btn:
                        await audio_btn.click()
                        await asyncio.sleep(random.uniform(2, 4))
                        # Audio solving would need speech-to-text
                        logger.info("Audio challenge opened — needs external solver")
                        return BypassResult.CAPTCHA_DETECTED
        except Exception as e:
            logger.debug("reCAPTCHA v2 audio fallback: %s", e)
        return BypassResult.CAPTCHA_DETECTED

    @classmethod
    async def _solve_recaptcha_v3(cls, page: int) -> BypassResult:
        """reCAPTCHA v3 — high score via behavior simulation."""
        logger.info("🤖 reCAPTCHA v3 — simulating human behavior for high score")
        try:
            # v3 is score-based — simulate natural browsing
            await _simulate_browsing_behavior(page, duration_seconds=5)
            return BypassResult.SUCCESS
        except Exception:
            return BypassResult.CAPTCHA_DETECTED

    @classmethod
    async def _solve_hcaptcha(cls, page: int) -> BypassResult:
        """hCaptcha — needs external solver."""
        if cls.SOLVER_API_KEY:
            return await cls._external_solve(page, "hcaptcha")
        return BypassResult.CAPTCHA_DETECTED

    @classmethod
    async def _solve_generic(cls, page: int) -> BypassResult:
        """Generic unknown captcha — wait and hope."""
        await asyncio.sleep(random.uniform(5, 10))
        return BypassResult.RETRY_NEEDED

    @classmethod
    async def _external_solve(cls, page: int, captcha_kind: str) -> BypassResult:
        """Route to external solver API (2captcha, Anti-Captcha, CapMonster)."""
        logger.info("📡 Routing %s to external solver: %s", captcha_kind, cls.SOLVER_SERVICE)
        # Integration point — implement based on selected service
        # This requires the page's sitekey + page URL → API call → token → inject
        try:
            html = await page.content()

            # Extract sitekey
            sitekey_match = re.search(
                r'(?:data-sitekey|sitekey)["\s=:]+["\']?([a-zA-Z0-9_-]{20,})',
                html,
            )
            if not sitekey_match:
                logger.warning("Could not extract sitekey for %s", captcha_kind)
                return BypassResult.CAPTCHA_DETECTED

            sitekey = sitekey_match.group(1)
            page_url = page.url

            logger.info(
                "🔑 Extracted sitekey=%s... for %s at %s",
                sitekey[:12], captcha_kind, page_url,
            )

            # API call would go here:
            # result = await call_solver_api(service, sitekey, page_url)
            # await inject_token(page, result.token)

            return BypassResult.CAPTCHA_DETECTED  # Until solver configured

        except Exception as e:
            logger.error("External solver error: %s", e)
            return BypassResult.CAPTCHA_DETECTED


# ═══════════════════════════════════════════════════════════
# Human Behavior Simulation
# ═══════════════════════════════════════════════════════════

async def _simulate_browsing_behavior(page: int, duration_seconds: float = 5.0) -> None:
    """Simulate human-like browsing behavior on a page."""
    if not PLAYWRIGHT_AVAILABLE:
        return

    start = time.time()
    while (time.time() - start) < duration_seconds:
        action = random.choice(["scroll", "move", "idle"])
        try:
            if action == "scroll":
                delta = random.randint(-300, 300)
                await page.mouse.wheel(0, delta)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            elif action == "move":
                vp = page.viewport_size or {"width": 1920, "height": 1080}
                x = random.randint(100, vp["width"] - 100)
                y = random.randint(100, vp["height"] - 100)
                steps = random.randint(5, 20)
                await page.mouse.move(x, y, steps=steps)
                await asyncio.sleep(random.uniform(0.2, 0.5))

            else:  # idle
                await asyncio.sleep(random.uniform(0.5, 1.5))

        except Exception:
            await asyncio.sleep(0.5)


# ═══════════════════════════════════════════════════════════
# Stealth Worker Engine
# ═══════════════════════════════════════════════════════════

class StealthWorker:
    """
    Enterprise stealth browser automation engine.

    Capabilities:
    - Multi-engine: Chromium, Firefox, WebKit (auto-fallback)
    - Deep fingerprint injection (Canvas, WebGL, AudioContext noise)
    - Human behavior simulation (mouse, scroll, typing, idle)
    - Session persistence (cookies, localStorage, tokens → SessionStore)
    - Cloudflare Turnstile/Challenge bypass pipeline
    - CAPTCHA detection + multi-solver routing
    - Request interception (tracker blocking, header rewriting)
    - Evidence capture (screenshots, DOM)
    - Worker pool for parallel operations
    - Health monitoring + exponential backoff retry
    """

    VERSION: Final[str] = "3.0.0-TITAN"

    def __init__(
        self,
        sessions_dir: str = "sessions",
        config: Optional[StealthConfig] = None,
        max_concurrent: int = 3,
    ) -> None:
        self._sessions_dir = sessions_dir
        self._config = config or StealthConfig()
        self._max_concurrent = max_concurrent

        # Runtime
        self._playwright: Optional[Any] = None
        self._browser_pool: Dict[BrowserEngine, Any] = {}
        self._active_contexts: List[Any] = []
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False

        # Anti-detection engine
        self._anti_detect: Optional[Any] = None
        if _ANTI_DETECT_AVAILABLE:
            self._anti_detect = AntiDetectionEngine()

        # Session store
        self._session_store: Optional[Any] = None
        if _SESSION_STORE_AVAILABLE:
            self._session_store = get_session_store(sessions_dir)

        # Circuit breaker: track consecutive failures per domain
        self._circuit_breaker: Dict[str, int] = {}
        self._circuit_breaker_threshold = 5

        # Stats
        self._stats = {
            "total_sessions": 0,
            "successful_bypasses": 0,
            "failed_bypasses": 0,
            "captchas_detected": 0,
            "cloudflare_bypassed": 0,
            "waf_detected": 0,
            "evasion_scripts_injected": 0,
            "screenshots_captured": 0,
            "errors": 0,
        }

        # Ensure directories
        Path(sessions_dir).mkdir(parents=True, exist_ok=True)
        Path(self._config.screenshots_dir).mkdir(parents=True, exist_ok=True)

    # ── Lifecycle ────────────────────────────────────────

    async def start(self) -> bool:
        """Start the stealth worker engine."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("⚠️ Playwright not installed — StealthWorker disabled")
            return False

        try:
            pw_manager = async_playwright()
            self._playwright = await pw_manager.start()
            self._running = True

            if self._session_store and hasattr(self._session_store, "start"):
                await self._session_store.start()

            # Start proxy pool
            if _PROXY_POOL_AVAILABLE and _proxy_pool:
                await _proxy_pool.start()

            # Load browser profiles
            if _BROWSER_PROFILE_AVAILABLE and _profile_manager:
                await _profile_manager.load_all()

            logger.info(
                "🕵️ StealthWorker v%s started (engines: chromium/firefox/webkit, "
                "max_concurrent: %d, anti_detect: %s, sessions: %s, "
                "evasion_arsenal: %s, waf_adaptive: %s, "
                "tls_fp: %s, h2_fp: %s, proxy_pool: %s, browser_profiles: %s, validator: %s)",
                self.VERSION, self._max_concurrent,
                "✅" if _ANTI_DETECT_AVAILABLE else "❌",
                "✅" if _SESSION_STORE_AVAILABLE else "❌",
                "✅ (18 scripts)" if _EVASION_SCRIPTS_AVAILABLE else "❌",
                "✅" if self._config.waf_adaptive else "❌",
                "✅" if _TLS_FINGERPRINT_AVAILABLE else "❌",
                "✅" if _H2_TRANSPORT_AVAILABLE else "❌",
                "✅" if _PROXY_POOL_AVAILABLE else "❌",
                "✅" if _BROWSER_PROFILE_AVAILABLE else "❌",
                "✅" if _BROWSER_VALIDATOR_AVAILABLE else "❌",
            )
            return True

        except Exception as e:
            logger.error("StealthWorker start failed: %s", e)
            return False

    async def stop(self) -> None:
        """Gracefully shutdown: close all browsers, persist sessions."""
        self._running = False

        # Close all browser contexts
        for ctx in self._active_contexts:
            try:
                await ctx.close()
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
        self._active_contexts.clear()

        # Close browsers
        for engine, browser in self._browser_pool.items():
            try:
                await browser.close()
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
        self._browser_pool.clear()

        # Stop playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
            self._playwright = None

        # Persist sessions
        if self._session_store and hasattr(self._session_store, "stop"):
            await self._session_store.stop()

        # Stop proxy pool
        if _PROXY_POOL_AVAILABLE and _proxy_pool:
            try:
                await _proxy_pool.stop()
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        logger.info("🕵️ StealthWorker stopped — stats: %s", self._stats)

    # ── Browser Management ───────────────────────────────

    async def _get_browser(
        self, engine: BrowserEngine = BrowserEngine.CHROMIUM,
    ) -> Optional[Any]:
        """Get or launch a browser instance."""
        if not self._playwright:
            return None

        if engine in self._browser_pool:
            browser = self._browser_pool[engine]
            if browser.is_connected():
                return browser

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--ignore-certificate-errors",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-first-run",
        ]

        try:
            pw = self._playwright
            if engine == BrowserEngine.FIREFOX:
                browser = await pw.firefox.launch(
                    headless=self._config.headless,
                    firefox_user_prefs={
                        "dom.webdriver.enabled": False,
                        "media.navigator.enabled": False,
                        "privacy.resistFingerprinting": False,
                    },
                )
            elif engine == BrowserEngine.WEBKIT:
                browser = await pw.webkit.launch(headless=self._config.headless)
            else:
                browser = await pw.chromium.launch(
                    headless=self._config.headless,
                    args=launch_args,
                )

            self._browser_pool[engine] = browser
            return browser

        except Exception as e:
            logger.error("Failed to launch %s: %s", engine.value, e)
            return None

    async def _create_stealth_context(
        self,
        browser: Any,
        user_agent: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        stored_session: Optional[Any] = None,
        proxy_url: Optional[str] = None,
        fingerprint_profile: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """Create a browser context with full stealth configuration.

        v3: Supports per-context proxy, consistent fingerprint profiles,
        and returns the fingerprint_profile used for later injection.
        """
        config = self._config
        fp_profile = fingerprint_profile or {}

        # Select user agent — prefer consistent profile
        ua = user_agent
        if not ua and fp_profile.get("user_agent"):
            ua = fp_profile["user_agent"]
        elif not ua:
            if _ANTI_DETECT_AVAILABLE and self._anti_detect:
                fp = self._anti_detect.generate_fingerprint()
                ua = fp.user_agent
                fp_profile["fingerprint"] = fp
            else:
                ua = random.choice(USER_AGENTS)

        # Select viewport
        vp = viewport
        if not vp and config.randomize_viewport:
            base = random.choice(VIEWPORT_PROFILES)
            vp = {
                "width": base["width"] + random.randint(-20, 20),
                "height": base["height"] + random.randint(-20, 20),
            }
        elif not vp:
            vp = {"width": 1920, "height": 1080}

        # Select locale/timezone — prefer consistent profile
        locale = fp_profile.get("locale") or (
            random.choice(LOCALES) if config.randomize_locale else "en-US"
        )
        tz = fp_profile.get("timezone") or (
            random.choice(TIMEZONES) if config.randomize_timezone else "UTC"
        )

        color_scheme = random.choice(["light", "dark", "no-preference"])

        try:
            context_kwargs: Dict[str, Any] = {
                "user_agent": ua,
                "viewport": vp,
                "locale": locale,
                "timezone_id": tz,
                "color_scheme": color_scheme,
                "has_touch": random.choice([True, False]),
                "java_script_enabled": True,
                "ignore_https_errors": True,
            }

            # Per-context proxy
            effective_proxy = proxy_url or config.proxy_url
            if effective_proxy:
                context_kwargs["proxy"] = {"server": effective_proxy}
                if config.proxy_bypass:
                    context_kwargs["proxy"]["bypass"] = config.proxy_bypass
                logger.info("🔗 Using proxy: %s", effective_proxy.split("@")[-1] if "@" in effective_proxy else effective_proxy)

            # Restore cookies from stored session
            if stored_session and hasattr(stored_session, "cookies"):
                storage_state_cookies = [c.to_dict() for c in stored_session.active_cookies]
                if storage_state_cookies:
                    context_kwargs["storage_state"] = {"cookies": storage_state_cookies}

            context = await browser.new_context(**context_kwargs)
            self._active_contexts.append(context)

            # Validate browser stack consistency
            webgl_vendor = fp_profile.get("webgl_vendor", "Google Inc. (NVIDIA)")
            webgl_renderer = fp_profile.get("webgl_renderer",
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)")
            issues = StackValidator.validate(
                ua,
                locale.split("-")[1] if "-" in locale else "US",
                webgl_renderer,
                webgl_vendor,
            )
            if issues:
                logger.warning("⚠️ Stack inconsistencies detected: %s", issues)

            return context

        except Exception as e:
            logger.error("Failed to create stealth context: %s", e)
            return None

    async def _apply_stealth_patches(
        self,
        page: int,
        fingerprint_profile: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Inject all anti-detection scripts into a page.

        v3 upgrade: Uses the full 18-script EvasionScriptBuilder arsenal
        with fingerprint-consistent configuration when available.
        Falls back to legacy scripts if evasion module is unavailable.
        """
        config = self._config

        # ── Phase 1: Base stealth plugin ──
        if STEALTH_PLUGIN_AVAILABLE:
            try:
                await stealth_async(page)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        # ── Phase 2: Full evasion arsenal (18 scripts) ──
        if _EVASION_SCRIPTS_AVAILABLE and config.inject_canvas_noise:
            try:
                # Build evasion config from fingerprint profile
                fp = fingerprint_profile or {}
                webgl_vendor = fp.get("webgl_vendor", "Google Inc. (NVIDIA)")
                webgl_renderer = fp.get("webgl_renderer",
                    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)")
                canvas_seed = fp.get("canvas_seed", random.randint(1, 2**31))
                audio_seed = fp.get("audio_seed", random.randint(1, 2**31))

                # Build screen config from viewport
                vp = page.viewport_size or {"width": 1920, "height": 1080}
                screen_config = {
                    "width": vp["width"],
                    "height": vp["height"],
                    "availWidth": vp["width"],
                    "availHeight": vp["height"] - 40,
                    "colorDepth": 24,
                    "pixelRatio": fp.get("pixel_ratio", 1),
                }

                # Build navigator config
                fingerprint = fp.get("fingerprint")
                nav_config = {
                    "hardwareConcurrency": getattr(fingerprint, "hardware_concurrency", 8) if fingerprint else 8,
                    "deviceMemory": getattr(fingerprint, "device_memory", 8) if fingerprint else 8,
                    "maxTouchPoints": getattr(fingerprint, "max_touch_points", 0) if fingerprint else 0,
                    "platform": getattr(fingerprint, "platform", "Win32") if fingerprint else "Win32",
                    "vendor": "Google Inc.",
                    "doNotTrack": None,
                    "language": getattr(fingerprint, "language", "en-US") if fingerprint else "en-US",
                    "languages": getattr(fingerprint, "languages", ["en-US", "en"]) if fingerprint else ["en-US", "en"],
                    "connectionType": "4g",
                    "downlink": random.choice([1.5, 2.5, 5.0, 10.0, 15.0]),
                    "rtt": random.choice([50, 100, 150, 200]),
                    "plugins": [
                        {"name": "PDF Viewer", "description": "Portable Document Format",
                         "filename": "internal-pdf-viewer", "mimeTypes": [{"type": "application/pdf"}]},
                        {"name": "Chrome PDF Viewer", "description": "Portable Document Format",
                         "filename": "internal-pdf-viewer", "mimeTypes": [{"type": "application/pdf"}]},
                        {"name": "Chromium PDF Viewer", "description": "Portable Document Format",
                         "filename": "internal-pdf-viewer", "mimeTypes": [{"type": "application/pdf"}]},
                    ],
                }

                # Battery simulation
                charging = random.choice([True, False])
                level = round(random.uniform(0.2, 0.95), 2)

                # Build and inject all 18 scripts
                scripts = EvasionScriptBuilder.build_all(
                    canvas_seed=canvas_seed,
                    audio_seed=audio_seed,
                    webgl_vendor=webgl_vendor,
                    webgl_renderer=webgl_renderer,
                    webgl_unmasked_vendor=webgl_vendor,
                    webgl_unmasked_renderer=webgl_renderer,
                    nav_config=nav_config,
                    screen_config=screen_config,
                    battery_charging=charging,
                    battery_level=level,
                    battery_charging_time=random.randint(1800, 7200) if charging else 0,
                    battery_discharging_time=0 if charging else random.randint(3600, 18000),
                    color_scheme=random.choice(["light", "dark"]),
                )

                # Inject in randomized order to avoid ordered-injection detection
                indices = list(range(len(scripts)))
                random.shuffle(indices)
                for idx in indices:
                    await page.add_init_script(scripts[idx])

                logger.info("🛡️ Injected %d evasion scripts (full arsenal)", len(scripts))
                return  # Done — skip legacy scripts

            except Exception as e:
                logger.warning("Evasion script injection failed, falling back to legacy: %s", e)

        # ── Phase 3: Legacy fallback ──
        # Always hide webdriver
        await page.add_init_script(WEBDRIVER_HIDE_SCRIPT)

        # Fingerprint noise
        if config.inject_canvas_noise:
            await page.add_init_script(CANVAS_NOISE_SCRIPT)
        if config.inject_webgl_noise:
            await page.add_init_script(WEBGL_NOISE_SCRIPT)
        if config.inject_audio_noise:
            await page.add_init_script(AUDIO_NOISE_SCRIPT)

    async def _setup_request_interception(self, page: int) -> None:
        """Set up request interception for tracker blocking and header rewriting."""
        config = self._config

        if not config.intercept_requests:
            return

        async def route_handler(route: Any) -> None:
            request = route.request
            url = request.url

            # Block trackers
            if config.block_trackers:
                for pattern in TRACKER_PATTERNS:
                    clean = pattern.replace("*", "")
                    if clean in url:
                        await route.abort()
                        return

            # Block images if configured
            if config.block_images and request.resource_type == "image":
                await route.abort()
                return

            # Rewrite headers for stealth
            headers = {**request.headers}
            headers.pop("sec-ch-ua-platform", None)  # Remove revealing headers

            try:
                await route.continue_(headers=headers)
            except Exception:
                try:
                    await route.continue_()
                except Exception as _err:
                    logger.warning("Suppressed error: %s", _err)

        try:
            await page.route("**/*", route_handler)
        except Exception as e:
            logger.debug("Request interception setup: %s", e)

    # ── Core Operations ──────────────────────────────────

    async def run_stealth_session(
        self,
        url: str,
        provider_id: str,
        engine: Optional[BrowserEngine] = None,
        config: Optional[StealthConfig] = None,
        on_page_ready: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Execute a full stealth browser session with bypass pipeline.

        Flow:
        1. Acquire semaphore (concurrency limit)
        2. Get/launch browser engine
        3. Restore session from store (if available)
        4. Create stealth context with fingerprint injection
        5. Navigate to URL
        6. Detect & bypass CAPTCHA/Cloudflare
        7. Simulate human behavior
        8. Execute custom callback (if provided)
        9. Capture session state (cookies, localStorage)
        10. Persist to SessionStore
        11. Capture evidence (screenshot)

        Returns dict with success, session_data, screenshot, etc.
        """
        # Circuit breaker check (before anything else)
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if self._circuit_breaker.get(domain, 0) >= self._circuit_breaker_threshold:
            return {
                "success": False,
                "error": f"Circuit breaker open for {domain} ({self._circuit_breaker[domain]} consecutive failures)",
                "provider": provider_id,
                "url": url,
            }

        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "error": "Playwright not installed", "provider": provider_id}

        if not self._running:
            return {"success": False, "error": "StealthWorker not started", "provider": provider_id}

        cfg = config or self._config
        selected_engine = engine or cfg.engine

        async with self._semaphore:
            self._stats["total_sessions"] += 1
            browser = None
            context = None
            fingerprint_profile: Dict[str, Any] = {}
            result: Dict[str, Any] = {
                "success": False,
                "provider": provider_id,
                "url": url,
                "engine": selected_engine.value,
                "timestamp": time.time(),
            }

            # Generate consistent fingerprint profile
            if _ANTI_DETECT_AVAILABLE and self._anti_detect:
                try:
                    fingerprint_profile = self._anti_detect.generate_consistent_profile()
                except Exception as e:
                    logger.debug("Consistent profile generation failed: %s", e)

            for attempt in range(cfg.max_retries):
                try:
                    # Get browser
                    browser = await self._get_browser(selected_engine)
                    if not browser:
                        # Fallback to another engine
                        for fallback in BrowserEngine:
                            if fallback != selected_engine:
                                browser = await self._get_browser(fallback)
                                if browser:
                                    selected_engine = fallback
                                    break
                    if not browser:
                        result["error"] = "No browser engine available"
                        return result

                    # Try to restore existing session
                    stored_session = None
                    if self._session_store:
                        stored_session = await self._session_store.get_session(provider_id)
                        if stored_session:
                            logger.info("♻️  Restoring session %s for %s",
                                        stored_session.session_id[:8], provider_id)

                    # Create context (with optional per-context proxy)
                    context = await self._create_stealth_context(
                        browser,
                        stored_session=stored_session,
                        fingerprint_profile=fingerprint_profile,
                    )
                    if not context:
                        result["error"] = "Failed to create browser context"
                        return result

                    page = await context.new_page()

                    # Apply full evasion arsenal
                    await self._apply_stealth_patches(page, fingerprint_profile)
                    self._stats["evasion_scripts_injected"] += 1

                    # Setup request interception
                    await self._setup_request_interception(page)

                    # Navigate
                    logger.info("🌐 Navigating to %s (engine: %s, attempt: %d/%d)",
                                url, selected_engine.value, attempt + 1, cfg.max_retries)

                    response = await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=cfg.navigation_timeout_ms,
                    )

                    # ── WAF Detection (v3) ──
                    waf_types: List[WAFType] = []
                    if cfg.waf_adaptive:
                        waf_types = await WAFDetector.detect(page, response)
                        if waf_types:
                            self._stats["waf_detected"] += 1
                            result["waf_detected"] = [w.value for w in waf_types]
                            strategy = WAFDetector.recommend_strategy(waf_types)

                            # Apply WAF-specific behavior
                            if strategy.get("extra_wait_seconds"):
                                logger.info("⏳ WAF wait: %ds", strategy["extra_wait_seconds"])
                                await asyncio.sleep(strategy["extra_wait_seconds"])

                    # Check for CAPTCHA/challenge
                    captcha_type = await CaptchaDetector.detect(page)
                    if captcha_type:
                        self._stats["captchas_detected"] += 1
                        logger.info("🔍 Detected: %s", captcha_type.value)

                        bypass_result = await CaptchaBypass.solve(page, captcha_type)
                        if bypass_result == BypassResult.SUCCESS:
                            self._stats["cloudflare_bypassed"] += 1
                            logger.info("✅ Challenge bypassed!")
                        elif bypass_result in (BypassResult.RETRY_NEEDED, BypassResult.TIMEOUT):
                            if attempt < cfg.max_retries - 1:
                                delay = cfg.retry_delay_base * (2 ** attempt)
                                logger.info("🔄 Retrying in %.1fs...", delay)
                                await context.close()
                                self._active_contexts.remove(context)
                                context = None
                                await asyncio.sleep(delay)
                                continue
                        else:
                            result["captcha_type"] = captcha_type.value
                            result["bypass_result"] = bypass_result.value

                    # Human behavior simulation (WAF-aware duration)
                    if cfg.simulate_human_behavior:
                        if waf_types:
                            strategy = WAFDetector.recommend_strategy(waf_types)
                            dwell = strategy.get("simulate_behavior_duration", 5.0)
                        else:
                            dwell = random.uniform(
                                cfg.min_page_dwell_ms / 1000,
                                cfg.max_page_dwell_ms / 1000,
                            )
                        await _simulate_browsing_behavior(page, dwell)

                    # Execute custom callback
                    if on_page_ready:
                        try:
                            callback_result = await on_page_ready(page, context)
                            result["callback_result"] = callback_result
                        except Exception as e:
                            logger.warning("Page callback error: %s", e)
                            result["callback_error"] = str(e)

                    # Extract session data
                    cookies = await context.cookies()
                    local_storage = await page.evaluate(
                        "() => { try { return JSON.stringify(localStorage); } catch(e) { return '{}'; } }"
                    )
                    session_storage = await page.evaluate(
                        "() => { try { return JSON.stringify(sessionStorage); } catch(e) { return '{}'; } }"
                    )

                    # Persist session
                    if self._session_store:
                        ua = await page.evaluate("() => navigator.userAgent")
                        new_session = await self._session_store.create_session(
                            provider=provider_id,
                            cookies=cookies,
                            local_storage=json.loads(local_storage) if isinstance(local_storage, str) else {},
                            user_agent=ua or "",
                            metadata={
                                "url": url,
                                "engine": selected_engine.value,
                                "response_status": response.status_code if response else None,
                                "captured_at": time.time(),
                            },
                        )
                        result["session_id"] = new_session.session_id

                    # Take screenshot
                    if cfg.capture_screenshots:
                        try:
                            ts = int(time.time())
                            screenshot_path = os.path.join(
                                cfg.screenshots_dir,
                                f"{provider_id}_{ts}.png",
                            )
                            await page.screenshot(path=screenshot_path, full_page=False)
                            result["screenshot"] = screenshot_path
                            self._stats["screenshots_captured"] += 1
                        except Exception as e:
                            logger.debug("Screenshot failed: %s", e)

                    # Build result
                    result.update({
                        "success": True,
                        "cookies_count": len(cookies),
                        "response_status": response.status_code if response else None,
                        "final_url": page.url,
                        "engine": selected_engine.value,
                        "attempt": attempt + 1,
                    })

                    self._stats["successful_bypasses"] += 1
                    logger.info(
                        "✅ Stealth session completed for %s (cookies=%d, status=%s)",
                        provider_id, len(cookies),
                        response.status_code if response else "N/A",
                    )
                    break

                except Exception as e:
                    self._stats["errors"] += 1
                    logger.error(
                        "Stealth session error (attempt %d/%d): %s",
                        attempt + 1, cfg.max_retries, e,
                    )
                    result["error"] = str(e)

                    if attempt < cfg.max_retries - 1:
                        delay = cfg.retry_delay_base * (2 ** attempt)
                        await asyncio.sleep(delay)

                finally:
                    # Cleanup context (but not browser — reuse)
                    if context:
                        try:
                            if context in self._active_contexts:
                                self._active_contexts.remove(context)
                            await context.close()
                        except Exception as _err:
                            logger.warning("Suppressed error: %s", _err)
                        context = None

            if not result["success"]:
                self._stats["failed_bypasses"] += 1
                # Circuit breaker: track failures
                self._circuit_breaker[domain] = self._circuit_breaker.get(domain, 0) + 1
            else:
                # Reset circuit breaker on success
                self._circuit_breaker[domain] = 0

            return result

    # ── Convenience Methods ──────────────────────────────

    async def run_bypass_session(
        self, url: str, provider_id: str,
    ) -> Dict[str, Any]:
        """
        Backward-compatible wrapper for simple bypass operations.
        (Replaces the original Diamond edition method)
        """
        return await self.run_stealth_session(url=url, provider_id=provider_id)

    async def extract_api_key_page(
        self,
        provider_id: str,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Navigate to a provider's API key console and capture session state.
        Designed for surgeon.bypass_and_regenerate() integration.
        """
        from sessions.session_store import PROVIDER_DEFAULTS
        defaults = PROVIDER_DEFAULTS.get(provider_id.lower(), {})
        target_url = url or defaults.get("console_url", "https://google.com")

        async def capture_key_page(page: int, context: dict) -> Any:
            """Callback to capture specific API key page data."""
            # Wait for page to fully load
            await asyncio.sleep(random.uniform(2.0, 4.0))

            # Try to extract visible API keys or key creation forms
            result = await page.evaluate("""
                () => {
                    const keys = [];
                    // Look for common key display patterns
                    const codeElements = document.querySelectorAll(
                        'code, .api-key, [data-testid*="key"], pre'
                    );
                    codeElements.forEach(el => {
                        const text = el.textContent.trim();
                        if (text.length > 20 && text.length < 200) {
                            keys.push(text);
                        }
                    });
                    return { found_keys: keys, page_title: document.title };
                }
            """)
            return result

        return await self.run_stealth_session(
            url=target_url,
            provider_id=provider_id,
            on_page_ready=capture_key_page,
        )

    async def multi_engine_bypass(
        self, url: str, provider_id: str,
    ) -> Dict[str, Any]:
        """
        Try all browser engines in sequence until one succeeds.
        Last resort for heavily protected targets.
        """
        engines = [BrowserEngine.CHROMIUM, BrowserEngine.FIREFOX, BrowserEngine.WEBKIT]
        random.shuffle(engines)

        for engine in engines:
            logger.info("🔄 Trying %s engine for %s", engine.value, url)
            result = await self.run_stealth_session(
                url=url,
                provider_id=provider_id,
                engine=engine,
            )
            if result.get("success"):
                return result
            # Small delay between engines
            await asyncio.sleep(random.uniform(2.0, 5.0))

        return {
            "success": False,
            "error": "All browser engines failed",
            "provider": provider_id,
            "url": url,
            "engines_tried": [e.value for e in engines],
        }

    # ── Stats ────────────────────────────────────────────

    def reset_circuit_breaker(self, domain: Optional[str] = None) -> None:
        """Reset circuit breaker for a domain or all domains."""
        if domain:
            self._circuit_breaker.pop(domain, None)
        else:
            self._circuit_breaker.clear()

    # ── Phase 2: TLS / H2 / ProxyPool / BrowserProfile / Validator ──

    def get_tls_engine(self) -> Optional[Any]:
        """Get the TLS fingerprint engine for configuring TLS-level stealth."""
        if _TLS_FINGERPRINT_AVAILABLE:
            return _tls_engine
        return None

    def get_h2_profile_selector(self) -> Optional[Any]:
        """Get the HTTP/2 transport profile selector."""
        if _H2_TRANSPORT_AVAILABLE:
            return _h2_selector
        return None

    def get_proxy_pool(self) -> Optional[Any]:
        """Get the proxy pool manager."""
        if _PROXY_POOL_AVAILABLE:
            return _proxy_pool
        return None

    def get_profile_manager(self) -> Optional[Any]:
        """Get the browser profile manager."""
        if _BROWSER_PROFILE_AVAILABLE:
            return _profile_manager
        return None

    async def select_proxy(
        self,
        country: Optional[str] = None,
        target_domain: Optional[str] = None,
        session_key: Optional[str] = None,
    ) -> Optional[str]:
        """
        Select best proxy from pool for a stealth operation.

        Returns proxy URL string or None.
        """
        if not _PROXY_POOL_AVAILABLE or _proxy_pool is None:
            return None

        proxy = await _proxy_pool.get_proxy(
            country=country,
            target_domain=target_domain,
            session_key=session_key,
        )
        return proxy.url if proxy else None

    async def validate_stealth(self, page: Any) -> Optional[Dict[str, Any]]:
        """
        Run live stealth validation on a page.

        Returns validation report dict or None if validator unavailable.
        """
        if not _BROWSER_VALIDATOR_AVAILABLE or _browser_validator is None:
            return None
        try:
            report = await _browser_validator.validate_page(page)
            return report.to_dict()
        except Exception as e:
            logger.warning("Stealth validation error: %s", e)
            return None

    async def capture_browser_profile(
        self, context: Any, page: Any, profile_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Capture current browser state as a persistent profile.

        Returns profile_id or None.
        """
        if not _BROWSER_PROFILE_AVAILABLE or _profile_manager is None:
            return None
        try:
            profile = await _profile_manager.capture_from_page(
                context, page, profile_id=profile_id,
            )
            return profile.profile_id
        except Exception as e:
            logger.warning("Profile capture error: %s", e)
            return None

    async def restore_browser_profile(
        self, context: Any, page: Any, profile_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Restore a saved browser profile into the current page/context.

        Returns restoration stats dict or None.
        """
        if not _BROWSER_PROFILE_AVAILABLE or _profile_manager is None:
            return None
        try:
            return await _profile_manager.restore_to_page(
                context, page, profile_id,
            )
        except Exception as e:
            logger.warning("Profile restore error: %s", e)
            return None

    # ── Phase 3: Geo / Behavior / Request / Fingerprint / Captcha Intel ──

    def get_geo_engine(self) -> Optional[Any]:
        """Get the geographic consistency engine."""
        if _GEO_CONSISTENCY_AVAILABLE:
            return _geo_engine
        return None

    def build_geo_profile(
        self,
        country_code: str,
        timezone_variant: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a geographic consistency profile for a country.

        Returns dict with timezone, locale, currency, accept_language,
        and Intl override scripts — all cross-validated.
        """
        if _GEO_CONSISTENCY_AVAILABLE and _geo_engine:
            return _geo_engine.build_profile(
                country_code, timezone_variant=timezone_variant,
            )
        return {"country_code": country_code, "error": "geo_engine_unavailable"}

    def get_playwright_geo_args(self, country_code: str) -> Dict[str, Any]:
        """Get Playwright context args matching a country profile."""
        if _GEO_CONSISTENCY_AVAILABLE and _geo_engine:
            return _geo_engine.build_playwright_context_args(country_code)
        return {}

    def get_behavior_engine(self) -> Optional[Any]:
        """Get the behavioral intelligence engine."""
        if _BEHAVIOR_ENGINE_AVAILABLE:
            return _behavior_engine
        return None

    def generate_human_mouse_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
    ) -> List[Tuple[int, int]]:
        """Generate a human-like Bézier mouse movement path."""
        if _BEHAVIOR_ENGINE_AVAILABLE and _behavior_engine:
            return _behavior_engine.generate_mouse_path(start, end)
        # Fallback: simple linear
        steps = 20
        return [
            (
                int(start[0] + (end[0] - start[0]) * t / steps),
                int(start[1] + (end[1] - start[1]) * t / steps),
            )
            for t in range(steps + 1)
        ]

    def generate_human_typing(self, text: str) -> List[Dict[str, Any]]:
        """Generate human-like typing actions with variable delays and typos."""
        if _BEHAVIOR_ENGINE_AVAILABLE and _behavior_engine:
            actions = _behavior_engine.generate_typing(text)
            return [a.to_dict() for a in actions]
        # Fallback: simple keypress list
        return [{"action": "keypress", "value": c, "delay_ms": random.randint(50, 150)} for c in text]

    def plan_browsing_session(
        self,
        intent: str = "casual",
        pages: int = 3,
    ) -> Dict[str, Any]:
        """
        Plan a natural browsing session with timing/scroll/interaction patterns.

        Args:
            intent: "casual", "shopping", "research", "reading", "quick_check"
            pages: Number of pages to visit
        """
        if _BEHAVIOR_ENGINE_AVAILABLE and _behavior_engine:
            intent_map = {
                "casual": BrowsingIntent.CASUAL_BROWSING,
                "shopping": BrowsingIntent.SHOPPING,
                "research": BrowsingIntent.RESEARCH,
                "reading": BrowsingIntent.READING,
                "quick_check": BrowsingIntent.QUICK_CHECK,
            }
            bi = intent_map.get(intent, BrowsingIntent.CASUAL_BROWSING)
            plan = _behavior_engine.plan_session(bi, pages=pages)
            return plan.to_dict()
        return {"intent": intent, "pages": pages, "error": "behavior_engine_unavailable"}

    def get_request_pipeline(self) -> Optional[Any]:
        """Get the request pipeline engine."""
        if _REQUEST_PIPELINE_AVAILABLE:
            return _request_pipeline
        return None

    def build_referrer_chain(
        self,
        target_url: str,
        source: str = "search",
        search_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build a realistic referrer chain for natural navigation.

        Args:
            target_url: The URL to navigate to
            source: "search", "direct", "social", or "internal"
            search_query: Optional search query (for search source)
        """
        if _REQUEST_PIPELINE_AVAILABLE and _request_pipeline:
            chain = _request_pipeline.build_referrer_chain(
                target_url, source=source, search_query=search_query,
            )
            return [entry.to_dict() for entry in chain]
        return [{"url": target_url, "referrer": "", "source": source}]

    def generate_page_load_assets(
        self,
        url: str,
        page_type: str = "landing_page",
    ) -> List[Dict[str, Any]]:
        """
        Generate a realistic page-load asset sequence.

        Returns ordered list of assets (CSS, JS, images, fonts, XHR)
        with natural timing and priority.
        """
        if _REQUEST_PIPELINE_AVAILABLE and _request_pipeline:
            assets = _request_pipeline.generate_page_load(url, page_type)
            return [a.to_dict() for a in assets]
        return [{"url": url, "type": "document", "priority": "highest"}]

    def get_fingerprint_engine(self) -> Optional[Any]:
        """Get the unified fingerprint consistency engine."""
        if _FINGERPRINT_ENGINE_AVAILABLE:
            return _fingerprint_engine
        return None

    def generate_consistent_fingerprint(
        self,
        os_name: str = "windows",
        browser_name: str = "chrome",
        seed: Optional[int] = None,
        gpu_class: str = "",
    ) -> Dict[str, Any]:
        """
        Generate a complete, cross-vector consistent browser fingerprint.

        All vectors (canvas, audio, WebGL, fonts, hardware) are matched
        to OS/browser/GPU and mathematically validated.

        Returns dict with profile + override scripts.
        """
        if _FINGERPRINT_ENGINE_AVAILABLE and _fingerprint_engine:
            os_map = {
                "windows": OSType.WINDOWS, "macos": OSType.MACOS,
                "linux": OSType.LINUX,
            }
            browser_map = {
                "chrome": BrowserFamily.CHROME, "firefox": BrowserFamily.FIREFOX,
                "safari": BrowserFamily.SAFARI, "edge": BrowserFamily.EDGE,
            }
            os_type = os_map.get(os_name, OSType.WINDOWS)
            browser_type = browser_map.get(browser_name, BrowserFamily.CHROME)

            fp = _fingerprint_engine.generate(
                os=os_type, browser=browser_type,
                seed=seed, gpu_class=gpu_class,
            )

            # Validate
            issues = _fingerprint_engine.validate(fp)
            return {
                **fp.to_dict(),
                "scripts": fp.get_all_scripts(),
                "validation_issues": [i.to_dict() for i in issues],
                "is_consistent": not any(
                    i.severity == "critical" for i in issues
                ),
            }
        return {"error": "fingerprint_engine_unavailable"}

    def get_captcha_intel_engine(self) -> Optional[Any]:
        """Get the advanced captcha intelligence engine."""
        if _CAPTCHA_INTEL_AVAILABLE:
            return _captcha_intel_engine
        return None

    def detect_captcha_type(self, html: str = "", script_urls: Optional[List[str]] = None) -> List[str]:
        """
        Detect captcha types present on a page.

        Returns list of captcha family names.
        """
        if _CAPTCHA_INTEL_AVAILABLE and _captcha_intel_engine:
            detected = _captcha_intel_engine.detect_captcha(
                html=html, script_urls=script_urls,
            )
            return [d.value for d in detected]
        return []

    async def solve_captcha_intelligent(
        self,
        captcha_type: str,
        sitekey: str,
        page_url: str,
        proxy: Optional[str] = None,
        optimize_for: str = "cost",
    ) -> Dict[str, Any]:
        """
        Solve a captcha using the intelligent multi-solver router.

        Automatically selects cheapest/fastest/most reliable solver,
        uses token cache, respects budget limits.
        """
        if not _CAPTCHA_INTEL_AVAILABLE or _captcha_intel_engine is None:
            return {"success": False, "error": "captcha_intel_engine_unavailable"}

        type_map = {f.value: f for f in CaptchaFamily}
        family = type_map.get(captcha_type)
        if not family:
            return {"success": False, "error": f"Unknown captcha type: {captcha_type}"}

        result = await _captcha_intel_engine.solve(
            SolveRequest(
                captcha_type=family,
                sitekey=sitekey,
                page_url=page_url,
                proxy=proxy,
            ),
            optimize_for=optimize_for,
        )
        return result.to_dict()

    def get_tls_session_config(self, user_agent: str = "") -> Dict[str, Any]:
        """
        Get TLS+H2 configuration to match a given User-Agent.

        Returns dict with tls_profile, h2_profile, ja3_hash, ja4_hash.
        """
        config: Dict[str, Any] = {"tls_available": False, "h2_available": False}

        if _TLS_FINGERPRINT_AVAILABLE and _tls_engine:
            # Select TLS profile matching browser
            browser = "chrome"
            platform = "windows"
            if "Firefox" in user_agent:
                browser = "firefox"
            elif "Safari" in user_agent and "Chrome" not in user_agent:
                browser, platform = "safari", "macos"

            tls_profile = _tls_engine.select_profile(browser, platform)
            config["tls_available"] = True
            config["ja3_hash"] = _tls_engine.compute_ja3(tls_profile)
            config["ja4_hash"] = _tls_engine.compute_ja4(tls_profile)
            config["tls_backend"] = _tls_engine.get_best_backend()
            config["tls_profile_name"] = tls_profile.name

        if _H2_TRANSPORT_AVAILABLE and _h2_selector:
            if user_agent:
                h2_profile = _h2_selector.select_by_ua(user_agent)
            else:
                h2_profile = _h2_selector.select("chrome")
            config["h2_available"] = True
            config["h2_profile_name"] = h2_profile.name
            config["h2_settings"] = H2SettingsBuilder.get_settings_dict(h2_profile) if _H2_TRANSPORT_AVAILABLE else {}
            config["h2_pseudo_header_order"] = h2_profile.pseudo_header_order

        return config

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive worker statistics."""
        return {
            "version": self.VERSION,
            "running": self._running,
            "playwright_available": PLAYWRIGHT_AVAILABLE,
            "stealth_plugin": STEALTH_PLUGIN_AVAILABLE,
            "anti_detection_engine": _ANTI_DETECT_AVAILABLE,
            "evasion_scripts_available": _EVASION_SCRIPTS_AVAILABLE,
            "session_store": _SESSION_STORE_AVAILABLE,
            # Phase 2
            "tls_fingerprint_engine": _TLS_FINGERPRINT_AVAILABLE,
            "h2_transport_engine": _H2_TRANSPORT_AVAILABLE,
            "browser_validator": _BROWSER_VALIDATOR_AVAILABLE,
            "proxy_pool": _PROXY_POOL_AVAILABLE,
            "browser_profile_persistence": _BROWSER_PROFILE_AVAILABLE,
            # Phase 3
            "geo_consistency_engine": _GEO_CONSISTENCY_AVAILABLE,
            "behavior_intelligence_engine": _BEHAVIOR_ENGINE_AVAILABLE,
            "request_pipeline_engine": _REQUEST_PIPELINE_AVAILABLE,
            "fingerprint_engine": _FINGERPRINT_ENGINE_AVAILABLE,
            "captcha_intelligence_engine": _CAPTCHA_INTEL_AVAILABLE,
            # Runtime
            "active_browsers": len(self._browser_pool),
            "active_contexts": len(self._active_contexts),
            "max_concurrent": self._max_concurrent,
            "circuit_breaker": dict(self._circuit_breaker),
            **self._stats,
        }

    def get_health(self) -> Dict[str, Any]:
        """Quick health check."""
        return {
            "status": "healthy" if self._running else "stopped",
            "playwright": PLAYWRIGHT_AVAILABLE,
            "evasion_arsenal": _EVASION_SCRIPTS_AVAILABLE,
            "tls_fingerprint": _TLS_FINGERPRINT_AVAILABLE,
            "h2_transport": _H2_TRANSPORT_AVAILABLE,
            "proxy_pool": _PROXY_POOL_AVAILABLE,
            "browser_profiles": _BROWSER_PROFILE_AVAILABLE,
            "geo_consistency": _GEO_CONSISTENCY_AVAILABLE,
            "behavior_intelligence": _BEHAVIOR_ENGINE_AVAILABLE,
            "request_pipeline": _REQUEST_PIPELINE_AVAILABLE,
            "fingerprint_engine": _FINGERPRINT_ENGINE_AVAILABLE,
            "captcha_intelligence": _CAPTCHA_INTEL_AVAILABLE,
            "browsers": len(self._browser_pool),
            "success_rate": (
                self._stats["successful_bypasses"] /
                max(self._stats["total_sessions"], 1)
            ) * 100,
            "circuit_breakers_open": sum(
                1 for v in self._circuit_breaker.values()
                if v >= self._circuit_breaker_threshold
            ),
        }


# ═══════════════════════════════════════════════════════════
# Singleton (backward compatible)
# ═══════════════════════════════════════════════════════════

stealth_worker: StealthWorker = StealthWorker()


