
from __future__ import annotations
"""
tg_bot/utils/anti_detection.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
ANTI-DETECTION — Browser Fingerprint & Stealth Engine

Advanced browser fingerprint generation, rotation, and stealth
techniques for web automation and research.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────────┐
   │                 ANTI-DETECTION ENGINE                       │
   ├──────────┬──────────┬──────────┬──────────┬────────────────┤
   │ Finger-  │ User     │ TLS/JA3  │ Behavior │ Session        │
   │ print    │ Agent    │ Rotation │ Simulate │ Manager        │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ Canvas   │ Chrome   │ Cipher   │ Mouse    │ Cookie Jar     │
   │ WebGL    │ Firefox  │ Curves   │ Scroll   │ Persistence    │
   │ Audio    │ Safari   │ Exts     │ Typing   │ Rotation       │
   │ Screen   │ Mobile   │ ALPN     │ Clicks   │ Isolation      │
   │ Fonts    │ Versions │ Handshk  │ Delays   │ Proxy Chain    │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ Timezone │ Locale   │ Headers  │ Cookie   │ Evasion        │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ Offset   │ Language │ Order    │ Mgmt     │ WAF Bypass     │
   │ Region   │ Accept   │ Priority │ SameSite │ Rate Adapt     │
   │ DST      │ Encoding │ Custom   │ Secure   │ Captcha Integ  │
   └──────────┴──────────┴──────────┴──────────┴────────────────┘

Features
────────
  • Browser fingerprint generation with 20+ attributes
  • Realistic User-Agent rotation (Chrome, Firefox, Safari, mobile)
  • TLS/JA3 fingerprint profiles for different browsers
  • Behavioral simulation (mouse, scroll, typing patterns)
  • Cookie and session management
  • Proxy chain management (HTTP/SOCKS)
  • Timezone and locale spoofing
  • Canvas/WebGL fingerprint variation
  • Header order matching real browsers
  • Request timing randomization
  • WAF detection and adaptive evasion

References
──────────
  Port of: apex_app/src/lib/anti-detection.ts (739 lines)
  Enhanced: JA3 fingerprints, behavioral simulation,
            proxy chains, canvas fingerprint algebra,
            header ordering, request timing
"""


import hashlib
import json
import os
import random
from collections import defaultdict
try:
    from arki_project.utils.titanium.compat import secure_random as random  # v10: CSPRNG
except ImportError:
    import random  # fallback
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# ── TITANIUM v29.0 Integration ──



# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════

class BrowserType(Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"


class Platform(Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"



# ── v3.4.1: Stealth Evasion Layer Integration ──
try:
    from arki_project.utils.traffic_orchestrator import get_traffic_orchestrator
    from arki_project.utils.waf_adaptive import get_waf_engine
    from arki_project.utils.latency_cloaking import get_kinetic_synthesizer
    from arki_project.utils.payload_encryption import get_payload_encryptor
    _STEALTH_V341 = True
except ImportError:
    _STEALTH_V341 = False


class StealthEvasionMatrix:
    """
    v3.4.1: Unified stealth evasion matrix.
    Combines TrafficOrchestrator + WAF Adaptive + Latency Cloaking + Payload Encryption.
    """

    def __init__(self) -> None:
        self._available = _STEALTH_V341
        self._traffic = get_traffic_orchestrator() if _STEALTH_V341 else None
        self._waf = get_waf_engine() if _STEALTH_V341 else None
        self._kinetic = get_kinetic_synthesizer() if _STEALTH_V341 else None
        self._encryptor = get_payload_encryptor() if _STEALTH_V341 else None

    def get_stealth_request_config(self, target_url: str = "",
                                    browser_hint: str = "") -> dict:
        """Get complete stealth config for a single request."""
        config = {
            "tls_profile": None,
            "headers": {},
            "cookies": {},
            "delay_seconds": 0.0,
            "encrypted_payload": False,
            "strategies": [],
        }
        if not self._available:
            return config

        # 1. Morph TLS profile (unique per-request)
        tls = self._traffic.morph(browser_hint)
        config["tls_profile"] = tls.to_dict()

        # 2. Get morphed headers matching the TLS profile
        config["headers"] = self._traffic.get_morphed_headers(tls)

        # 3. Apply WAF adaptive evasion
        waf_config = self._waf.prepare_request(config["headers"], target_url)
        config["headers"] = waf_config["headers"]
        config["cookies"] = waf_config["cookies"]
        config["strategies"] = waf_config["strategies_applied"]

        # 4. Human kinetic delay (no deterministic constants)
        config["delay_seconds"] = self._kinetic.api_request_delay()
        if waf_config.get("delay", 0) > 0:
            config["delay_seconds"] = max(config["delay_seconds"], waf_config["delay"])

        config["encrypted_payload"] = True
        return config

    def encrypt_payload(self, data: bytes) -> bytes:
        """Encrypt outgoing payload."""
        if self._encryptor:
            encrypted = self._encryptor.encrypt(data)
            return encrypted.to_bytes()
        return data

    def record_response(self, status_code: int, latency_ms: float,
                       headers: dict, body_snippet: str = "") -> None:
        """Feed response back into adaptive engine."""
        if self._waf:
            from arki_project.utils.waf_adaptive import WAFResponse
            self._waf.record_response(WAFResponse(
                status_code=status_code,
                latency_ms=latency_ms,
                headers=headers,
                body_snippet=body_snippet[:2000],
                blocked=status_code in (403, 429, 503),
            ))

    @property
    def stats(self) -> dict:
        if not self._available:
            return {"status": "unavailable"}
        return {
            "traffic_orchestrator": self._traffic.stats,
            "waf_adaptive": self._waf.stats,
            "payload_encryption": self._encryptor.stats,
        }


def get_stealth_matrix() -> StealthEvasionMatrix:
    return StealthEvasionMatrix()


class ProxyType(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ScreenProfile:
    """Screen resolution and display properties."""
    width: int
    height: int
    color_depth: int = 24
    pixel_ratio: float = 1.0
    available_width: int = 0
    available_height: int = 0

    def __post_init__(self) -> Any:
        if not self.available_width:
            self.available_width = self.width
        if not self.available_height:
            self.available_height = self.height - 40  # taskbar


@dataclass
class BrowserFingerprint:
    """Complete browser fingerprint."""
    user_agent: str
    platform: str
    language: str
    languages: List[str]
    screen: ScreenProfile
    timezone: str
    timezone_offset: int
    webgl_vendor: str
    webgl_renderer: str
    fonts: List[str]
    plugins: List[str]
    canvas_hash: str
    audio_context: float
    hardware_concurrency: int
    device_memory: int
    max_touch_points: int
    do_not_track: Optional[str]
    cookie_enabled: bool = True
    headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_agent": self.user_agent,
            "platform": self.platform,
            "language": self.language,
            "languages": self.languages,
            "screen": {
                "width": self.screen.width,
                "height": self.screen.height,
                "color_depth": self.screen.color_depth,
                "pixel_ratio": self.screen.pixel_ratio,
            },
            "timezone": self.timezone,
            "timezone_offset": self.timezone_offset,
            "webgl_vendor": self.webgl_vendor,
            "webgl_renderer": self.webgl_renderer,
            "fonts_count": len(self.fonts),
            "plugins_count": len(self.plugins),
            "canvas_hash": self.canvas_hash,
            "hardware_concurrency": self.hardware_concurrency,
            "device_memory": self.device_memory,
            "max_touch_points": self.max_touch_points,
        }

    def fingerprint_hash(self) -> str:
        """Generate a unique hash for this fingerprint."""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    host: str
    port: int
    proxy_type: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    response_time_ms: float = 0

    def url(self) -> str:
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"


@dataclass
class TLSProfile:
    """TLS fingerprint profile."""
    browser: BrowserType
    version: str
    cipher_suites: List[str]
    extensions: List[str]
    curves: List[str]
    alpn: List[str]
    ja3_hash: str


# ═══════════════════════════════════════════════════════════════════
# User-Agent Generator
# ═══════════════════════════════════════════════════════════════════

class UserAgentGenerator:
    """Generate realistic User-Agent strings."""

    # Chrome versions (recent)
    CHROME_VERSIONS = [
        "120.0.6099.109", "120.0.6099.71", "119.0.6045.199",
        "119.0.6045.159", "118.0.5993.117", "118.0.5993.88",
        "121.0.6167.85", "121.0.6167.139", "122.0.6261.69",
        "122.0.6261.94", "123.0.6312.58", "123.0.6312.86",
        "124.0.6367.61", "124.0.6367.91", "125.0.6422.76",
    ]

    # Firefox versions
    FIREFOX_VERSIONS = [
        "121.0", "120.0", "119.0", "118.0", "117.0",
        "122.0", "123.0", "124.0", "125.0", "126.0",
    ]

    # Safari versions
    SAFARI_VERSIONS = [
        "17.2", "17.1", "17.0", "16.6", "16.5",
    ]

    # Windows versions
    WINDOWS_VERSIONS = [
        "10.0", "10.0; Win64; x64",
    ]

    # macOS versions
    MACOS_VERSIONS = [
        "14_2_1", "14_1", "14_0", "13_6_3", "13_5",
    ]

    @classmethod
    def generate(cls, browser: Optional[BrowserType] = None,
                 platform: Optional[Platform] = None, version: Optional[str] = None) -> str:
        """Generate a realistic User-Agent string."""
        browser = browser or random.choice(list(BrowserType))
        platform = platform or random.choice([
            Platform.WINDOWS, Platform.MACOS, Platform.LINUX,
        ])

        if browser == BrowserType.CHROME:
            return cls._chrome_ua(platform, version)
        elif browser == BrowserType.FIREFOX:
            return cls._firefox_ua(platform, version)
        elif browser == BrowserType.SAFARI:
            return cls._safari_ua(version)
        elif browser == BrowserType.EDGE:
            return cls._edge_ua(platform, version)
        return cls._chrome_ua(platform, version)

    @classmethod
    def _chrome_ua(cls, platform: Platform, version: Optional[str] = None) -> str:
        ver = version or random.choice(cls.CHROME_VERSIONS)
        if platform == Platform.WINDOWS:
            win_ver = random.choice(cls.WINDOWS_VERSIONS)
            return f"Mozilla/5.0 (Windows NT {win_ver}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36"
        elif platform == Platform.MACOS:
            mac_ver = random.choice(cls.MACOS_VERSIONS)
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X {mac_ver}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36"
        else:
            return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Safari/537.36"

    @classmethod
    def _firefox_ua(cls, platform: Platform, version: Optional[str] = None) -> str:
        ver = version or random.choice(cls.FIREFOX_VERSIONS)
        if platform == Platform.WINDOWS:
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{ver}) Gecko/20100101 Firefox/{ver}"
        elif platform == Platform.MACOS:
            mac_ver = random.choice(cls.MACOS_VERSIONS)
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X {mac_ver}; rv:{ver}) Gecko/20100101 Firefox/{ver}"
        else:
            return f"Mozilla/5.0 (X11; Linux x86_64; rv:{ver}) Gecko/20100101 Firefox/{ver}"

    @classmethod
    def _safari_ua(cls, version: Optional[str] = None) -> str:
        ver = version or random.choice(cls.SAFARI_VERSIONS)
        mac_ver = random.choice(cls.MACOS_VERSIONS)
        webkit = "605.1.15"
        return f"Mozilla/5.0 (Macintosh; Intel Mac OS X {mac_ver}) AppleWebKit/{webkit} (KHTML, like Gecko) Version/{ver} Safari/{webkit}"

    @classmethod
    def _edge_ua(cls, platform: Platform, version: Optional[str] = None) -> str:
        ver = version or random.choice(cls.CHROME_VERSIONS) # Edge is Chromium-based, uses Chrome versions
        chrome_ver = random.choice(cls.CHROME_VERSIONS)
        edge_ver = chrome_ver.split(".")[0] + ".0"
        if platform == Platform.WINDOWS:
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 Edg/{edge_ver}"
        else:
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36 Edg/{edge_ver}"

    @classmethod
    def generate_mobile(cls) -> str:
        """Generate a mobile User-Agent."""
        android_versions = ["13", "14", "12", "11"]
        devices = [
            "SM-S918B", "SM-S911B", "Pixel 8 Pro", "Pixel 7",
            "SM-A546B", "OnePlus 11", "Redmi Note 12",
        ]
        ver = random.choice(cls.CHROME_VERSIONS)
        android = random.choice(android_versions)
        device = random.choice(devices)
        return f"Mozilla/5.0 (Linux; Android {android}; {device}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver} Mobile Safari/537.36"


# ═══════════════════════════════════════════════════════════════════
# TLS/JA3 Fingerprint Profiles
# ═══════════════════════════════════════════════════════════════════

class TLSProfileGenerator:
    """Generate TLS fingerprint profiles matching real browsers."""

    PROFILES: Dict[str, TLSProfile] = {
        "chrome_120": TLSProfile(
            browser=BrowserType.CHROME,
            version="120",
            cipher_suites=[
                "TLS_AES_128_GCM_SHA256",
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "ECDHE-ECDSA-AES128-GCM-SHA256",
                "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-ECDSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES256-GCM-SHA384",
            ],
            extensions=[
                "server_name", "extended_master_secret",
                "renegotiation_info", "supported_groups",
                "ec_point_formats", "session_ticket",
                "application_layer_protocol_negotiation",
                "status_request", "signature_algorithms",
                "signed_certificate_timestamp", "key_share",
                "psk_key_exchange_modes", "supported_versions",
                "compress_certificate", "application_settings",
            ],
            curves=["X25519", "P-256", "P-384"],
            alpn=["h2", "http/1.1"],
            ja3_hash="cd08e31494f9531f560d64c695473da9",
        ),
        "firefox_121": TLSProfile(
            browser=BrowserType.FIREFOX,
            version="121",
            cipher_suites=[
                "TLS_AES_128_GCM_SHA256",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_256_GCM_SHA384",
                "ECDHE-ECDSA-AES128-GCM-SHA256",
                "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-ECDSA-CHACHA20-POLY1305",
                "ECDHE-RSA-CHACHA20-POLY1305",
                "ECDHE-ECDSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES256-GCM-SHA384",
            ],
            extensions=[
                "server_name", "extended_master_secret",
                "renegotiation_info", "supported_groups",
                "ec_point_formats", "session_ticket",
                "application_layer_protocol_negotiation",
                "status_request", "delegated_credentials",
                "key_share", "supported_versions",
                "signature_algorithms", "psk_key_exchange_modes",
                "record_size_limit",
            ],
            curves=["X25519", "P-256", "P-384", "P-521"],
            alpn=["h2", "http/1.1"],
            ja3_hash="b32309a26951912be7dba376398abc3b",
        ),
        "safari_17": TLSProfile(
            browser=BrowserType.SAFARI,
            version="17",
            cipher_suites=[
                "TLS_AES_128_GCM_SHA256",
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "ECDHE-ECDSA-AES256-GCM-SHA384",
                "ECDHE-ECDSA-AES128-GCM-SHA256",
                "ECDHE-ECDSA-CHACHA20-POLY1305",
                "ECDHE-RSA-AES256-GCM-SHA384",
                "ECDHE-RSA-AES128-GCM-SHA256",
                "ECDHE-RSA-CHACHA20-POLY1305",
            ],
            extensions=[
                "server_name", "extended_master_secret",
                "renegotiation_info", "supported_groups",
                "ec_point_formats", "application_layer_protocol_negotiation",
                "status_request", "signed_certificate_timestamp",
                "key_share", "supported_versions",
                "signature_algorithms", "psk_key_exchange_modes",
            ],
            curves=["X25519", "P-256", "P-384", "P-521"],
            alpn=["h2", "http/1.1"],
            ja3_hash="773906b0efdefa24a7f2b8eb6985bf37",
        ),
    }

    @classmethod
    def get_profile(cls, browser: BrowserType) -> TLSProfile:
        """Get TLS profile for a browser."""
        mapping = {
            BrowserType.CHROME: "chrome_120",
            BrowserType.FIREFOX: "firefox_121",
            BrowserType.SAFARI: "safari_17",
            BrowserType.EDGE: "chrome_120",
        }
        key = mapping.get(browser, "chrome_120")
        return cls.PROFILES[key]


# ═══════════════════════════════════════════════════════════════════
# Screen Profiles Database
# ═══════════════════════════════════════════════════════════════════

COMMON_SCREENS: List[ScreenProfile] = [
    ScreenProfile(1920, 1080, 24, 1.0),
    ScreenProfile(2560, 1440, 24, 1.0),
    ScreenProfile(3840, 2160, 24, 2.0),
    ScreenProfile(1366, 768, 24, 1.0),
    ScreenProfile(1440, 900, 24, 2.0),
    ScreenProfile(1536, 864, 24, 1.25),
    ScreenProfile(1680, 1050, 24, 1.0),
    ScreenProfile(2560, 1600, 24, 2.0),
    ScreenProfile(1280, 720, 24, 1.0),
    ScreenProfile(1600, 900, 24, 1.0),
]

MOBILE_SCREENS: List[ScreenProfile] = [
    ScreenProfile(412, 915, 24, 2.625),
    ScreenProfile(393, 873, 24, 2.75),
    ScreenProfile(360, 800, 24, 3.0),
    ScreenProfile(390, 844, 24, 3.0),
    ScreenProfile(428, 926, 24, 3.0),
]


# ═══════════════════════════════════════════════════════════════════
# Font Lists
# ═══════════════════════════════════════════════════════════════════

COMMON_FONTS_WINDOWS = [
    "Arial", "Arial Black", "Calibri", "Cambria", "Comic Sans MS",
    "Consolas", "Courier New", "Georgia", "Impact", "Lucida Console",
    "Microsoft Sans Serif", "Palatino Linotype", "Segoe UI",
    "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
]

COMMON_FONTS_MAC = [
    "Arial", "Courier New", "Georgia", "Helvetica", "Helvetica Neue",
    "Lucida Grande", "Menlo", "Monaco", "Palatino", "SF Pro",
    "SF Mono", "Times", "Times New Roman", "Trebuchet MS", "Verdana",
]

COMMON_FONTS_LINUX = [
    "Arial", "Courier New", "DejaVu Sans", "DejaVu Serif",
    "Droid Sans", "FreeMono", "FreeSans", "Liberation Mono",
    "Liberation Sans", "Noto Sans", "Ubuntu", "Ubuntu Mono",
]


# ═══════════════════════════════════════════════════════════════════
# Timezone Database
# ═══════════════════════════════════════════════════════════════════

TIMEZONE_OFFSETS: Dict[str, int] = {
    "America/New_York": -300,
    "America/Chicago": -360,
    "America/Denver": -420,
    "America/Los_Angeles": -480,
    "America/Sao_Paulo": -180,
    "Europe/London": 0,
    "Europe/Berlin": 60,
    "Europe/Moscow": 180,
    "Asia/Dubai": 240,
    "Asia/Kolkata": 330,
    "Asia/Shanghai": 480,
    "Asia/Tokyo": 540,
    "Asia/Tehran": 210,
    "Australia/Sydney": 660,
    "Pacific/Auckland": 780,
}


# ═══════════════════════════════════════════════════════════════════
# WebGL Renderers
# ═══════════════════════════════════════════════════════════════════

WEBGL_RENDERERS: List[Tuple[str, str]] = [
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0)"),
    ("Apple", "Apple GPU"),
    ("Google Inc. (Apple)", "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)"),
    ("Google Inc. (Apple)", "ANGLE (Apple, Apple M2, OpenGL 4.1)"),
    ("Mesa", "Mesa Intel(R) UHD Graphics (TGL GT1)"),
]


# ═══════════════════════════════════════════════════════════════════
# Behavioral Simulation
# ═══════════════════════════════════════════════════════════════════

class BehaviorSimulator:
    """
    Simulate human-like browsing behavior.

    Generates realistic mouse movements, scroll patterns,
    typing speeds, and click timings.
    """

    @staticmethod
    def generate_mouse_path(
        start: Tuple[int, int],
        end: Tuple[int, int],
        steps: int = 20,
    ) -> List[Tuple[int, int]]:
        """
        Generate a human-like mouse movement path.

        Uses Bézier curves with random control points for
        natural-looking trajectories.
        """
        # Random control points for Bézier curve
        cx1 = start[0] + random.randint(-50, 50)
        cy1 = start[1] + random.randint(-100, 100)
        cx2 = end[0] + random.randint(-50, 50)
        cy2 = end[1] + random.randint(-100, 100)

        steps = max(1, steps)  # Prevent division by zero
        path = []
        for i in range(steps + 1):
            t = i / steps
            # Cubic Bézier
            x = (
                (1 - t) ** 3 * start[0]
                + 3 * (1 - t) ** 2 * t * cx1
                + 3 * (1 - t) * t ** 2 * cx2
                + t ** 3 * end[0]
            )
            y = (
                (1 - t) ** 3 * start[1]
                + 3 * (1 - t) ** 2 * t * cy1
                + 3 * (1 - t) * t ** 2 * cy2
                + t ** 3 * end[1]
            )
            # Add micro-jitter
            x += random.gauss(0, 1.5)
            y += random.gauss(0, 1.5)
            path.append((int(x), int(y)))

        return path

    @staticmethod
    def generate_typing_delays(text: str) -> List[float]:
        """
        Generate human-like typing delays (ms per character).

        Accounts for:
        - Base typing speed (varies between 50-150ms)
        - Shift key delay for capitals
        - Pause after punctuation
        - Occasional longer pauses (thinking)
        """
        delays = []
        base_speed = random.uniform(60, 130)

        for i, char in enumerate(text):
            delay = base_speed + random.gauss(0, 15)

            # Shift key delay
            if char.isupper() or char in '!@#$%^&*()_+{}|:"<>?':
                delay += random.uniform(20, 60)

            # Punctuation pause
            if char in ".!?":
                delay += random.uniform(100, 400)

            # Space is usually faster
            if char == " ":
                delay *= 0.7

            # Occasional longer pauses
            if random.random() < 0.03:
                delay += random.uniform(200, 800)

            delays.append(max(20, delay))

        return delays

    @staticmethod
    def generate_scroll_pattern(
        page_height: int,
        viewport_height: int = 900,
    ) -> List[Dict[str, Any]]:
        """Generate human-like scroll pattern."""
        events = []
        current_y = 0
        max_scroll = page_height - viewport_height

        while current_y < max_scroll:
            # Variable scroll distance
            scroll_delta = random.randint(100, 500)
            current_y = min(current_y + scroll_delta, max_scroll)

            events.append({
                "type": "scroll",
                "y": current_y,
                "delay_ms": random.uniform(500, 3000),
            })

            # Occasional pause (reading)
            if random.random() < 0.3:
                events.append({
                    "type": "pause",
                    "duration_ms": random.uniform(1000, 5000),
                })

            # Occasional scroll back up slightly
            if random.random() < 0.1:
                back = random.randint(50, 200)
                current_y = max(0, current_y - back)
                events.append({
                    "type": "scroll",
                    "y": current_y,
                    "delay_ms": random.uniform(200, 800),
                })

        return events

    @staticmethod
    def generate_click_timing() -> float:
        """Generate human-like click timing (ms)."""
        return random.gauss(200, 50)  # ~200ms average

    @staticmethod
    def generate_request_delay() -> float:
        """Generate delay between requests (seconds)."""
        # Log-normal distribution mimics human browsing
        return random.lognormvariate(1.0, 0.8)


# ═══════════════════════════════════════════════════════════════════
# Header Builder
# ═══════════════════════════════════════════════════════════════════

class HeaderBuilder:
    """Build browser-realistic HTTP headers with correct ordering."""

    # Chrome header order
    CHROME_ORDER = [
        "Host", "Connection", "sec-ch-ua", "sec-ch-ua-mobile",
        "sec-ch-ua-platform", "Upgrade-Insecure-Requests",
        "User-Agent", "Accept", "Sec-Fetch-Site", "Sec-Fetch-Mode",
        "Sec-Fetch-User", "Sec-Fetch-Dest", "Accept-Encoding",
        "Accept-Language", "Cookie",
    ]

    # Firefox header order
    FIREFOX_ORDER = [
        "Host", "User-Agent", "Accept", "Accept-Language",
        "Accept-Encoding", "Connection", "Upgrade-Insecure-Requests",
        "Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site",
        "Sec-Fetch-User", "Cookie",
    ]

    @classmethod
    def build(cls, fingerprint: BrowserFingerprint,
              browser: BrowserType) -> Dict[str, str]:
        """Build headers matching a specific browser."""
        headers: Dict[str, str] = {}

        headers["User-Agent"] = fingerprint.user_agent
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        headers["Accept-Language"] = ",".join(
            f"{lang};q={1.0 - i * 0.1:.1f}" if i > 0 else lang
            for i, lang in enumerate(fingerprint.languages[:4])
        )
        headers["Accept-Encoding"] = "gzip, deflate, br"
        headers["Connection"] = "keep-alive"
        headers["Upgrade-Insecure-Requests"] = "1"

        if browser in (BrowserType.CHROME, BrowserType.EDGE):
            # Chrome-specific headers
            ver = re.search(r"Chrome/(\d+)", fingerprint.user_agent)
            chrome_ver = ver.group(1) if ver else "120"
            headers["sec-ch-ua"] = f'"Chromium";v="{chrome_ver}", "Not_A Brand";v="8"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = f'"{fingerprint.platform}"'
            headers["Sec-Fetch-Site"] = "none"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-User"] = "?1"
            headers["Sec-Fetch-Dest"] = "document"

        elif browser == BrowserType.FIREFOX:
            headers["Sec-Fetch-Dest"] = "document"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-Site"] = "none"
            headers["Sec-Fetch-User"] = "?1"

        return headers

    @classmethod
    def build_client_hints(
        cls,
        fingerprint: "BrowserFingerprint",
        browser: BrowserType,
        full_version: str = "125.0.6422.76",
    ) -> Dict[str, str]:
        """
        Build Sec-CH-UA Client Hints headers (Chrome 125+).

        These headers are increasingly checked by Cloudflare, Akamai, and PerimeterX.
        """
        hints: Dict[str, str] = {}

        if browser not in (BrowserType.CHROME, BrowserType.EDGE):
            return hints  # Only Chromium sends Client Hints

        major = full_version.split(".")[0]
        hints["sec-ch-ua"] = f'"Chromium";v="{major}", "Google Chrome";v="{major}", "Not-A.Brand";v="24"'
        hints["sec-ch-ua-mobile"] = "?0"
        hints["sec-ch-ua-platform"] = f'"{fingerprint.platform}"'
        hints["sec-ch-ua-full-version"] = f'"{full_version}"'
        hints["sec-ch-ua-full-version-list"] = (
            f'"Chromium";v="{full_version}", '
            f'"Google Chrome";v="{full_version}", '
            f'"Not-A.Brand";v="24.0.0.0"'
        )

        # Architecture
        arch = "x86" if fingerprint.platform == "Windows" else "arm" if fingerprint.platform == "macOS" else "x86"
        hints["sec-ch-ua-arch"] = f'"{arch}"'
        hints["sec-ch-ua-bitness"] = '"64"'

        # Platform version
        pv_map = {
            "Windows": '"15.0.0"',
            "macOS": '"14.5.0"',
            "Linux": '"6.5.0"',
        }
        hints["sec-ch-ua-platform-version"] = pv_map.get(fingerprint.platform, '"15.0.0"')

        # Model (only for mobile — empty for desktop)
        hints["sec-ch-ua-model"] = '""'

        # Window on Which (WoW)
        hints["sec-ch-ua-wow64"] = "?0"

        return hints


# ═══════════════════════════════════════════════════════════════════
# HTTP/2 Fingerprint Profiles
# ═══════════════════════════════════════════════════════════════════

@dataclass
class HTTP2Profile:
    """
    HTTP/2 connection fingerprint.

    Modern WAFs (Akamai, Cloudflare) fingerprint HTTP/2 SETTINGS frames,
    WINDOW_UPDATE sizes, PRIORITY frames, and pseudo-header order.
    Inconsistency between TLS JA3 (saying Chrome) and HTTP/2 (not Chrome)
    is a top detection vector.
    """
    browser: BrowserType
    settings: Dict[int, int]        # SETTINGS frame parameters
    window_update: int              # Initial WINDOW_UPDATE increment
    pseudo_header_order: List[str]  # :method, :authority, :scheme, :path order
    priority_frames: bool           # Whether PRIORITY frames are sent
    header_table_size: int          # HPACK dynamic table size


# Chrome 125 HTTP/2 fingerprint
H2_CHROME_125 = HTTP2Profile(
    browser=BrowserType.CHROME,
    settings={
        1: 65536,     # HEADER_TABLE_SIZE
        2: 0,         # ENABLE_PUSH (disabled)
        3: 1000,      # MAX_CONCURRENT_STREAMS
        4: 6291456,   # INITIAL_WINDOW_SIZE
        6: 262144,    # MAX_HEADER_LIST_SIZE
    },
    window_update=15663105,
    pseudo_header_order=[":method", ":authority", ":scheme", ":path"],
    priority_frames=True,
    header_table_size=65536,
)

# Firefox 126 HTTP/2 fingerprint
H2_FIREFOX_126 = HTTP2Profile(
    browser=BrowserType.FIREFOX,
    settings={
        1: 65536,     # HEADER_TABLE_SIZE
        2: 0,         # ENABLE_PUSH
        3: 100,       # MAX_CONCURRENT_STREAMS
        4: 131072,    # INITIAL_WINDOW_SIZE
        6: 65536,     # MAX_HEADER_LIST_SIZE
    },
    window_update=12517377,
    pseudo_header_order=[":method", ":path", ":authority", ":scheme"],
    priority_frames=False,  # Firefox dropped PRIORITY in recent versions
    header_table_size=65536,
)

# Safari 17.5 HTTP/2 fingerprint
H2_SAFARI_17 = HTTP2Profile(
    browser=BrowserType.SAFARI,
    settings={
        1: 4096,      # HEADER_TABLE_SIZE (smaller than Chrome)
        2: 0,         # ENABLE_PUSH
        3: 100,       # MAX_CONCURRENT_STREAMS
        4: 2097152,   # INITIAL_WINDOW_SIZE
        8: 1,         # ENABLE_CONNECT_PROTOCOL
    },
    window_update=10485760,
    pseudo_header_order=[":method", ":scheme", ":path", ":authority"],
    priority_frames=True,
    header_table_size=4096,
)

H2_PROFILES: Dict[str, HTTP2Profile] = {
    "chrome_125": H2_CHROME_125,
    "firefox_126": H2_FIREFOX_126,
    "safari_17": H2_SAFARI_17,
}


# ═══════════════════════════════════════════════════════════════════
# Extended WebGL GPU Database (30+ real devices)
# ═══════════════════════════════════════════════════════════════════

WEBGL_RENDERERS_EXTENDED: List[Tuple[str, str]] = [
    # NVIDIA Desktop
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Ti SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    # AMD Desktop
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 7800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    # Intel Integrated
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 730 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    # Apple Silicon (macOS)
    ("Google Inc. (Apple)", "ANGLE (Apple, APPLE M3 Pro, OpenGL 4.1)"),
    ("Google Inc. (Apple)", "ANGLE (Apple, APPLE M3, OpenGL 4.1)"),
    ("Google Inc. (Apple)", "ANGLE (Apple, APPLE M2 Pro, OpenGL 4.1)"),
    ("Google Inc. (Apple)", "ANGLE (Apple, APPLE M2, OpenGL 4.1)"),
    ("Google Inc. (Apple)", "ANGLE (Apple, APPLE M1 Pro, OpenGL 4.1)"),
    ("Google Inc. (Apple)", "ANGLE (Apple, APPLE M1, OpenGL 4.1)"),
    # Linux Mesa
    ("Mesa", "Mesa Intel(R) UHD Graphics (TGL GT1)"),
    ("Mesa", "Mesa Intel(R) HD Graphics 630 (KBL GT2)"),
    ("Mesa/X.org", "AMD Radeon RX 6700 XT (navi22, LLVM 16.0.6, DRM 3.54, 6.5.0)"),
    ("Mesa/X.org", "NV166 (LLVM 16.0.6, DRM 3.54, 6.5.0)"),
    # Laptop GPUs
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Laptop GPU Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Laptop GPU Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"),
]

# GPU → Platform consistency mapping
GPU_PLATFORM_MAP: Dict[str, List[Platform]] = {
    "ANGLE": [Platform.WINDOWS],         # ANGLE = Windows/ChromeOS
    "Apple": [Platform.MACOS],           # Apple GPU = macOS only
    "Mesa": [Platform.LINUX],            # Mesa = Linux only
}


# ═══════════════════════════════════════════════════════════════════
# Updated JA3 Hashes (2025 browser versions)
# ═══════════════════════════════════════════════════════════════════

MODERN_JA3_HASHES: Dict[str, str] = {
    "chrome_125_win": "cd08e31494f9531f560d64c695473da9",
    "chrome_125_mac": "b32309a26951912be7dba376398abc3b",
    "chrome_124_win": "cd08e31494f9531f560d64c695473da9",
    "firefox_126_win": "b32309a26951912be7dba376398abc3b",
    "firefox_126_mac": "839bbe3ed7fed7ed27ee1399fc4f5bf1",
    "safari_17_5_mac": "773906b0efdefa24a7f2b8eb6985bf37",
    "edge_125_win": "cd08e31494f9531f560d64c695473da9",  # Same as Chrome (Chromium)
}


# ═══════════════════════════════════════════════════════════════════
# Residential Proxy Quality Scoring
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ProxyQuality:
    """Quality assessment for a proxy."""
    is_residential: bool = False
    is_datacenter: bool = True
    asn_type: str = "datacenter"       # residential, isp, datacenter, mobile
    country: str = ""
    city: str = ""
    response_time_ms: float = 0
    success_rate: float = 1.0
    last_checked: float = 0
    score: float = 0.0                 # 0-100 quality score


class ProxyQualityScorer:
    """Score proxies for stealth operations."""

    # Known datacenter ASN prefixes (will be detected by WAFs)
    DATACENTER_ASNS: Final[Set[str]] = {
        "AS14618", "AS16509",  # Amazon AWS
        "AS15169",             # Google Cloud
        "AS8075",              # Microsoft Azure
        "AS13335",             # Cloudflare
        "AS20473",             # Choopa/Vultr
        "AS63949",             # Linode
        "AS14061",             # DigitalOcean
        "AS24940",             # Hetzner
        "AS16276",             # OVH
    }

    @classmethod
    def score(cls, proxy: ProxyConfig, quality: ProxyQuality) -> float:
        """
        Score a proxy 0-100 for stealth use.

        Factors:
        - Residential IPs score highest (WAFs rarely block residential)
        - Datacenter IPs score lowest
        - Response time affects reliability
        - Success rate is critical
        """
        score = 0.0

        # IP type weight (50 points)
        if quality.asn_type == "residential":
            score += 50
        elif quality.asn_type == "isp":
            score += 40
        elif quality.asn_type == "mobile":
            score += 45  # Mobile IPs are excellent for stealth
        else:
            score += 10  # Datacenter

        # Response time (20 points)
        if quality.response_time_ms < 200:
            score += 20
        elif quality.response_time_ms < 500:
            score += 15
        elif quality.response_time_ms < 1000:
            score += 10
        elif quality.response_time_ms < 2000:
            score += 5

        # Success rate (20 points)
        score += quality.success_rate * 20

        # Geo diversity bonus (10 points)
        if quality.country:
            score += 5
        if quality.city:
            score += 5

        quality.score = min(100, max(0, score))
        return quality.score

    @classmethod
    def is_safe_for_stealth(cls, quality: ProxyQuality) -> bool:
        """Check if proxy is safe for stealth operations."""
        return (
            quality.score >= 50
            and quality.success_rate >= 0.8
            and quality.response_time_ms < 3000
        )


# ═══════════════════════════════════════════════════════════════════
# Request Timing Engine
# ═══════════════════════════════════════════════════════════════════

class RequestTimingEngine:
    """
    Generate human-realistic request timing patterns.

    Uses Poisson distribution for inter-request intervals,
    with time-of-day awareness and burst detection avoidance.
    """

    @staticmethod
    def poisson_delay(rate: float = 0.5) -> float:
        """
        Generate delay using Poisson process.

        Args:
            rate: Average requests per second (0.5 = 1 request per 2 seconds)

        Returns:
            Delay in seconds
        """
        import math
        return -math.log(1 - random.random()) / rate

    @staticmethod
    def human_browsing_delay() -> float:
        """Generate realistic browsing delay (between page navigations)."""
        import random as _stdlib_random
        # Log-normal: most delays are 2-5s, occasional long pauses (reading)
        delay = _stdlib_random.lognormvariate(1.2, 0.7)
        # Clamp to reasonable range
        return max(0.5, min(30.0, delay))

    @staticmethod
    def human_typing_delay() -> float:
        """Delay between keystrokes (ms)."""
        return random.gauss(95, 25)

    @staticmethod
    def api_request_delay(is_first: bool = False) -> float:
        """Delay for API requests (less aggressive than browsing)."""
        if is_first:
            return random.uniform(0.5, 2.0)
        return random.uniform(0.3, 1.5)

    @classmethod
    def generate_session_timing(
        cls,
        num_requests: int,
        duration_minutes: float = 5.0,
    ) -> List[float]:
        """
        Generate a realistic session timing profile.

        Returns list of delays (seconds) between consecutive requests.
        Mimics human browsing: fast bursts + reading pauses.
        """
        delays = []
        avg_rate = num_requests / (duration_minutes * 60)

        for i in range(num_requests - 1):
            if random.random() < 0.15:
                # Long pause (reading/thinking)
                delays.append(random.uniform(5.0, 15.0))
            elif random.random() < 0.3:
                # Quick burst (navigating rapidly)
                delays.append(random.uniform(0.3, 1.0))
            else:
                # Normal browsing
                delays.append(cls.poisson_delay(max(0.1, avg_rate)))

        return delays


# ═══════════════════════════════════════════════════════════════════
# Proxy Chain Manager
# ═══════════════════════════════════════════════════════════════════

class ProxyChainManager:
    """Manage and rotate proxy chains."""

    def __init__(self) -> None:
        self.proxies: List[ProxyConfig] = []
        self.current_index: int = 0
        self.failed_proxies: Set[str] = set()
        self.usage_count: Dict[str, int] = defaultdict(int)

    def add_proxy(self, proxy: ProxyConfig) -> None:
        self.proxies.append(proxy)

    def remove_proxy(self, host: str, port: int) -> None:
        self.proxies = [
            p for p in self.proxies
            if not (p.host == host and p.port == port)
        ]

    def get_next(self) -> Optional[ProxyConfig]:
        """Get next available proxy (round-robin)."""
        available = [
            p for p in self.proxies
            if p.url() not in self.failed_proxies
        ]
        if not available:
            return None

        proxy = available[self.current_index % len(available)]
        self.current_index += 1
        self.usage_count[proxy.url()] += 1
        return proxy

    def get_random(self) -> Optional[ProxyConfig]:
        """Get a random available proxy."""
        available = [
            p for p in self.proxies
            if p.url() not in self.failed_proxies
        ]
        return random.choice(available) if available else None

    def mark_failed(self, proxy: ProxyConfig) -> None:
        self.failed_proxies.add(proxy.url())

    def reset_failures(self) -> None:
        self.failed_proxies.clear()

    def get_chain(self, length: int = 2) -> List[ProxyConfig]:
        """Build a proxy chain of specified length."""
        available = [
            p for p in self.proxies
            if p.url() not in self.failed_proxies
        ]
        if len(available) < length:
            return available
        return random.sample(available, length)

    def stats(self) -> Dict[str, Any]:
        return {
            "total": len(self.proxies),
            "active": len(self.proxies) - len(self.failed_proxies),
            "failed": len(self.failed_proxies),
            "usage": dict(self.usage_count),
        }


# ═══════════════════════════════════════════════════════════════════
# Cookie Manager
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Cookie:
    """HTTP Cookie."""
    name: str
    value: str
    domain: str
    path: str = "/"
    secure: bool = False
    http_only: bool = False
    same_site: str = "Lax"
    expires: Optional[float] = None

    def is_expired(self) -> bool:
        if self.expires is None:
            return False
        return time.time() > self.expires

    def to_header(self) -> str:
        return f"{self.name}={self.value}"


class CookieJar:
    """Cookie management with domain isolation."""

    def __init__(self) -> None:
        self.cookies: Dict[str, List[Cookie]] = defaultdict(list)

    def set(self, cookie: Cookie) -> None:
        """Add or update a cookie."""
        domain_cookies = self.cookies[cookie.domain]
        # Replace existing
        self.cookies[cookie.domain] = [
            c for c in domain_cookies if c.name != cookie.name
        ]
        self.cookies[cookie.domain].append(cookie)

    def get(self, domain: str, name: Optional[str] = None) -> List[Cookie]:
        """Get cookies for a domain."""
        valid = [
            c for c in self.cookies.get(domain, [])
            if not c.is_expired()
        ]
        if name:
            return [c for c in valid if c.name == name]
        return valid

    def get_header(self, domain: str) -> str:
        """Get Cookie header value."""
        cookies = self.get(domain)
        return "; ".join(c.to_header() for c in cookies)

    def clear(self, domain: Optional[str] = None) -> None:
        if domain:
            self.cookies.pop(domain, None)
        else:
            self.cookies.clear()

    def count(self) -> int:
        return sum(len(v) for v in self.cookies.values())


# ═══════════════════════════════════════════════════════════════════
# Anti-Detection Engine (Main Interface)
# ═══════════════════════════════════════════════════════════════════

class AntiDetectionEngine:
    """
    Main anti-detection engine.

    Generates consistent browser fingerprints, manages proxies,
    and simulates human behavior.
    """

    def __init__(self) -> None:
        self.ua_generator = UserAgentGenerator()
        self.proxy_manager = ProxyChainManager()
        self.cookie_jar = CookieJar()
        self.behavior = BehaviorSimulator()
        self.active_fingerprints: List[BrowserFingerprint] = []
        self._seed = int.from_bytes(os.urandom(4), "big")

    def generate_fingerprint(
        self,
        browser: Optional[BrowserType] = None,
        platform: Optional[Platform] = None,
        timezone: Optional[str] = None,
    ) -> BrowserFingerprint:
        """Generate a complete, consistent browser fingerprint."""
        browser = browser or random.choice(list(BrowserType))
        platform = platform or random.choice([
            Platform.WINDOWS, Platform.MACOS, Platform.LINUX,
        ])

        # Select consistent components
        ua = self.ua_generator.generate(browser, platform)
        screen = random.choice(COMMON_SCREENS)
        tz = timezone or random.choice(list(TIMEZONE_OFFSETS.keys()))
        tz_offset = TIMEZONE_OFFSETS.get(tz, 0)

        # Platform-specific fonts
        if platform == Platform.WINDOWS:
            fonts = random.sample(COMMON_FONTS_WINDOWS, random.randint(10, 15))
        elif platform == Platform.MACOS:
            fonts = random.sample(COMMON_FONTS_MAC, random.randint(10, 14))
        else:
            fonts = random.sample(COMMON_FONTS_LINUX, random.randint(8, 11))

        # WebGL
        webgl = random.choice(WEBGL_RENDERERS)

        # Canvas hash (deterministic from seed + UA)
        canvas_seed = hashlib.sha256(f"{self._seed}:{ua}".encode()).hexdigest()

        # Languages
        lang_map = {
            "America/New_York": ("en-US", ["en-US", "en"]),
            "Europe/Berlin": ("de-DE", ["de-DE", "de", "en-US", "en"]),
            "Europe/London": ("en-GB", ["en-GB", "en"]),
            "Asia/Tokyo": ("ja-JP", ["ja-JP", "ja", "en-US", "en"]),
            "Asia/Tehran": ("fa-IR", ["fa-IR", "fa", "en-US", "en"]),
        }
        lang, languages = lang_map.get(tz, ("en-US", ["en-US", "en"]))

        # Platform string
        platform_str = {
            Platform.WINDOWS: "Windows",
            Platform.MACOS: "macOS",
            Platform.LINUX: "Linux",
            Platform.ANDROID: "Android",
            Platform.IOS: "iOS",
        }.get(platform, "Windows")

        fp = BrowserFingerprint(
            user_agent=ua,
            platform=platform_str,
            language=lang,
            languages=languages,
            screen=screen,
            timezone=tz,
            timezone_offset=tz_offset,
            webgl_vendor=webgl[0],
            webgl_renderer=webgl[1],
            fonts=fonts,
            plugins=["PDF Viewer", "Chrome PDF Viewer", "Chromium PDF Viewer"] if browser in (BrowserType.CHROME, BrowserType.EDGE) else [],
            canvas_hash=canvas_seed[:32],
            audio_context=random.uniform(0.00001, 0.00005),
            hardware_concurrency=random.choice([4, 8, 12, 16]),
            device_memory=random.choice([4, 8, 16, 32]),
            max_touch_points=0,
            do_not_track=random.choice([None, "1"]),
            headers=HeaderBuilder.build(
                BrowserFingerprint.__new__(BrowserFingerprint),
                browser,
            ) if False else {},
        )

        # Build proper headers
        fp.headers = HeaderBuilder.build(fp, browser)

        self.active_fingerprints.append(fp)
        return fp

    def rotate_fingerprint(self) -> BrowserFingerprint:
        """Generate a fresh fingerprint (rotation)."""
        self._seed = int.from_bytes(os.urandom(4), "big")
        return self.generate_fingerprint()

    def get_request_config(
        self,
        fingerprint: Optional[BrowserFingerprint] = None,
        use_proxy: bool = False,
    ) -> Dict[str, Any]:
        """Get a complete request configuration."""
        fp = fingerprint or self.generate_fingerprint()

        config: Dict[str, Any] = {
            "headers": fp.headers,
            "timeout": random.uniform(15, 30),
        }

        if use_proxy:
            proxy = self.proxy_manager.get_next()
            if proxy:
                config["proxy"] = proxy.url()

        # Add realistic request timing
        config["delay"] = self.behavior.generate_request_delay()

        return config

    def generate_consistent_profile(
        self,
        target_region: str = "us",
    ) -> Dict[str, Any]:
        """
        Generate a fully consistent browser profile.

        Returns a complete configuration dict for StealthWorker with
        matching fingerprint, TLS profile, HTTP/2 profile, Client Hints,
        and timing parameters — all internally consistent.
        """
        region_config = {
            "us": {
                "timezone": "America/New_York",
                "platform": Platform.WINDOWS,
                "browser": BrowserType.CHROME,
                "locale": "en-US",
            },
            "eu": {
                "timezone": "Europe/Berlin",
                "platform": Platform.WINDOWS,
                "browser": BrowserType.CHROME,
                "locale": "de-DE",
            },
            "fi": {
                "timezone": "Europe/Helsinki",
                "platform": Platform.WINDOWS,
                "browser": BrowserType.CHROME,
                "locale": "fi-FI",
            },
            "uk": {
                "timezone": "Europe/London",
                "platform": Platform.MACOS,
                "browser": BrowserType.SAFARI,
                "locale": "en-GB",
            },
            "jp": {
                "timezone": "Asia/Tokyo",
                "platform": Platform.MACOS,
                "browser": BrowserType.CHROME,
                "locale": "ja-JP",
            },
        }

        cfg = region_config.get(target_region, region_config["us"])
        browser = cfg["browser"]
        platform = cfg["platform"]

        # Generate fingerprint
        fp = self.generate_fingerprint(
            browser=browser,
            platform=platform,
            timezone=cfg["timezone"],
        )

        # Select consistent WebGL renderer for platform
        import random as _stdlib_random
        if platform == Platform.MACOS:
            candidates = [r for r in WEBGL_RENDERERS_EXTENDED if "Apple" in r[0] or "Apple" in r[1]]
            webgl = _stdlib_random.choice(candidates) if candidates else WEBGL_RENDERERS_EXTENDED[0]
        elif platform == Platform.LINUX:
            candidates = [r for r in WEBGL_RENDERERS_EXTENDED if "Mesa" in r[0] or "Mesa" in r[1]]
            webgl = _stdlib_random.choice(candidates) if candidates else WEBGL_RENDERERS_EXTENDED[0]
        else:
            # Windows: ANGLE-based, not Apple or Mesa
            candidates = [r for r in WEBGL_RENDERERS_EXTENDED
                          if "ANGLE" in r[1] and "Apple" not in r[1] and "Mesa" not in r[0]]
            webgl = _stdlib_random.choice(candidates) if candidates else WEBGL_RENDERERS_EXTENDED[0]

        # TLS profile
        tls = TLSProfileGenerator.get_profile(browser)

        # HTTP/2 profile
        h2_key = {
            BrowserType.CHROME: "chrome_125",
            BrowserType.FIREFOX: "firefox_126",
            BrowserType.SAFARI: "safari_17",
            BrowserType.EDGE: "chrome_125",
        }.get(browser, "chrome_125")
        h2 = H2_PROFILES.get(h2_key)

        # Client Hints
        client_hints = HeaderBuilder.build_client_hints(fp, browser)

        # Canvas/audio seeds (deterministic per session)
        canvas_seed = hash(fp.fingerprint_hash()) & 0x7FFFFFFF
        audio_seed = (canvas_seed * 31337) & 0x7FFFFFFF

        return {
            "fingerprint": fp,
            "user_agent": fp.user_agent,
            "headers": {**fp.headers, **client_hints},
            "tls_profile": tls,
            "http2_profile": h2,
            "webgl_vendor": webgl[0],
            "webgl_renderer": webgl[1],
            "canvas_seed": canvas_seed,
            "audio_seed": audio_seed,
            "timezone": cfg["timezone"],
            "locale": cfg["locale"],
            "platform": cfg["platform"],
            "browser": browser,
            "screen": fp.screen,
        }

    def stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "fingerprints_generated": len(self.active_fingerprints),
            "proxies": self.proxy_manager.stats(),
            "cookies": self.cookie_jar.count(),
        }


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Anti-Detection
# ══════════════════════════════════════════════════════════════

import random as _random
import hashlib as _hashlib


class BrowserProfilePool:
    """Manage a pool of realistic browser profiles for rotation."""

    _PROFILES = [
        {"browser": "Chrome", "version": "125.0.6422.60", "os": "Windows 10", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"},
        {"browser": "Chrome", "version": "124.0.6367.118", "os": "macOS 14", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"},
        {"browser": "Firefox", "version": "126.0", "os": "Linux", "ua": "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"},
        {"browser": "Safari", "version": "17.5", "os": "macOS 14", "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"},
        {"browser": "Edge", "version": "125.0.2535.51", "os": "Windows 11", "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"},
    ]

    def __init__(self) -> None:
        self._used: list[int] = []

    def get_profile(self) -> dict:
        """Get a random browser profile, avoiding recent repeats."""
        available = [i for i in range(len(self._PROFILES)) if i not in self._used[-2:]]
        if not available:
            available = list(range(len(self._PROFILES)))
        idx = _random.choice(available)
        self._used.append(idx)
        if len(self._used) > 20:
            self._used = self._used[-10:]
        return self._PROFILES[idx].copy()

    def get_headers(self) -> dict:
        """Generate realistic HTTP headers from a random profile."""
        p = self.get_profile()
        return {
            "User-Agent": p["ua"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": _random.choice([
                "en-US,en;q=0.9",
                "en-GB,en;q=0.9",
                "fa-IR,fa;q=0.9,en-US;q=0.8",
                "de-DE,de;q=0.9,en;q=0.8",
            ]),
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }


class CanvasDefense:
    """Generate consistent but unique canvas fingerprints."""

    @staticmethod
    def generate_noise_seed(session_id: str) -> int:
        """Deterministic noise seed from session."""
        return int(_hashlib.sha256(session_id.encode()).hexdigest()[:8], 16)

    @staticmethod
    def should_add_noise() -> bool:
        """Randomly decide whether to add canvas noise (anti-fingerprint)."""
        return _random.random() < 0.7  # 70% chance


class RequestThrottler:
    """Intelligent request throttling to avoid detection."""

    def __init__(self, min_delay: float = 0.5, max_delay: float = 3.0, burst_limit: int = 5) -> None:
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._burst_limit = burst_limit
        self._recent_requests: list[float] = []

    def get_delay(self) -> float:
        """Calculate delay before next request."""
        import time
        now = time.time()
        # Count requests in last 10 seconds
        self._recent_requests = [t for t in self._recent_requests if now - t < 10]
        
        if len(self._recent_requests) >= self._burst_limit:
            # Slow down — we're bursting
            return self._max_delay + _random.uniform(1, 5)
        
        delay = _random.uniform(self._min_delay, self._max_delay)
        # Add human-like jitter
        delay += _random.gauss(0, 0.2)
        return max(0.1, delay)

    def record_request(self) -> Any:
        import time
        self._recent_requests.append(time.time())


# v3.3: Unified proxy access point
class IntegratedProxyManager:
    """Combines anti_detection stealth profiles with proxy_rotator."""

    def __init__(self) -> None:
        self._rotator = get_proxy_rotator() if _PROXY_ROTATION else None
        self._ua_gen = UserAgentGenerator()
        self._tls_gen = TLSProfileGenerator()

    def get_stealth_config(self, prefer_country: str = "") -> dict:
        """Get complete stealth configuration: proxy + fingerprint + headers."""
        config = {
            "proxy": None,
            "user_agent": self._ua_gen.generate(),
            "headers": {},
        }
        if self._rotator:
            config["proxy"] = self._rotator.get_proxy(prefer_country=prefer_country)
        # Add anti-tracking headers
        config["headers"] = {
            "User-Agent": config["user_agent"],
            "DNT": "1",
            "Sec-GPC": "1",
            "Accept-Language": "en-US,en;q=0.5",
        }
        return config

    def report_proxy_result(self, proxy_url: str, success: bool, latency_ms: float = 0) -> None:
        if self._rotator and proxy_url:
            if success:
                self._rotator.report_success(proxy_url, latency_ms)
            else:
                self._rotator.report_failure(proxy_url)

    def get_stats(self) -> dict:
        stats = {"proxy_rotation_available": self._rotator is not None}
        if self._rotator:
            stats.update(self._rotator.stats)
        return stats


def get_integrated_proxy_manager() -> IntegratedProxyManager:
    return IntegratedProxyManager()


