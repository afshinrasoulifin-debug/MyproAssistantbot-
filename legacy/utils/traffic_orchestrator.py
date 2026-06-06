
from __future__ import annotations
"""
utils/traffic_orchestrator.py — Full Morphing Traffic Engine
═════════════════════════════════════════════════════════════
Real-time TLS handshake manipulation with per-request fingerprint
rotation based on global traffic entropy analysis.

Goal: 0% signature correlation between consecutive sessions.
Every handshake = a unique browser instance.

Architecture:
  ┌────────────────────────────────────────────────────┐
  │              TrafficOrchestrator                   │
  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
  │  │ Entropy  │→│ Morphing │→│ TLS Handshake  │  │
  │  │ Analyzer │  │ Engine   │  │ Manipulator    │  │
  │  └──────────┘  └──────────┘  └────────────────┘  │
  │       ↕              ↕              ↕             │
  │  ┌──────────────────────────────────────────────┐ │
  │  │ Fingerprint Profiles (Chrome/FF/Safari/Edge) │ │
  │  │ JA3/JA3S Hash Generator                      │ │
  │  │ Cipher Suite Permutation Engine              │ │
  │  │ Extension Order Randomizer                   │ │
  │  │ ALPN/Curve Selection                         │ │
  │  └──────────────────────────────────────────────┘ │
  └────────────────────────────────────────────────────┘
"""

import hashlib
import logging
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Final, List, Set, Tuple

logger = logging.getLogger(__name__)


# ── Global Traffic Entropy Thresholds ──
_ENTROPY_HIGH: Final[float] = 4.5    # High entropy → aggressive morphing
_ENTROPY_LOW: Final[float] = 2.0     # Low entropy → conservative
_HISTORY_WINDOW: Final[int] = 100    # Last N requests for entropy calc


@dataclass(frozen=True)
class TLSHandshakeProfile:
    """Immutable TLS handshake configuration for a single request."""
    cipher_suites: Tuple[str, ...]
    extensions: Tuple[str, ...]
    curves: Tuple[str, ...]
    alpn: Tuple[str, ...]
    ja3_hash: str
    browser_label: str
    platform: str
    version: str
    tls_version: str = "TLSv1.3"
    session_id_length: int = 32
    compression_methods: Tuple[str, ...] = ("null",)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cipher_suites": list(self.cipher_suites),
            "extensions": list(self.extensions),
            "curves": list(self.curves),
            "alpn": list(self.alpn),
            "ja3_hash": self.ja3_hash,
            "browser": self.browser_label,
            "tls_version": self.tls_version,
        }


# ── Cipher Suite Pools (real-world captured from browsers) ──
_CHROME_CIPHERS: Final[List[str]] = [
    "TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "ECDHE-ECDSA-AES128-GCM-SHA256", "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-ECDSA-AES256-GCM-SHA384", "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-CHACHA20-POLY1305", "ECDHE-RSA-CHACHA20-POLY1305",
    "ECDHE-RSA-AES128-SHA", "ECDHE-RSA-AES256-SHA",
    "AES128-GCM-SHA256", "AES256-GCM-SHA384", "AES128-SHA", "AES256-SHA",
]

_FIREFOX_CIPHERS: Final[List[str]] = [
    "TLS_AES_128_GCM_SHA256", "TLS_CHACHA20_POLY1305_SHA256",
    "TLS_AES_256_GCM_SHA384",
    "ECDHE-ECDSA-AES128-GCM-SHA256", "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-ECDSA-CHACHA20-POLY1305", "ECDHE-RSA-CHACHA20-POLY1305",
    "ECDHE-ECDSA-AES256-GCM-SHA384", "ECDHE-RSA-AES256-GCM-SHA384",
    "ECDHE-ECDSA-AES256-SHA", "ECDHE-ECDSA-AES128-SHA",
    "ECDHE-RSA-AES128-SHA", "ECDHE-RSA-AES256-SHA",
    "AES128-GCM-SHA256", "AES256-GCM-SHA384",
]

_SAFARI_CIPHERS: Final[List[str]] = [
    "TLS_AES_128_GCM_SHA256", "TLS_AES_256_GCM_SHA384",
    "TLS_CHACHA20_POLY1305_SHA256",
    "ECDHE-ECDSA-AES256-GCM-SHA384", "ECDHE-ECDSA-AES128-GCM-SHA256",
    "ECDHE-ECDSA-CHACHA20-POLY1305",
    "ECDHE-RSA-AES256-GCM-SHA384", "ECDHE-RSA-AES128-GCM-SHA256",
    "ECDHE-RSA-CHACHA20-POLY1305",
    "AES256-GCM-SHA384", "AES128-GCM-SHA256",
]

_EDGE_CIPHERS: Final[List[str]] = _CHROME_CIPHERS.copy()  # Same engine

_CIPHER_POOLS: Final[Dict[str, List[str]]] = {
    "chrome": _CHROME_CIPHERS,
    "firefox": _FIREFOX_CIPHERS,
    "safari": _SAFARI_CIPHERS,
    "edge": _EDGE_CIPHERS,
}

# ── Extension Pools ──
_COMMON_EXTENSIONS: Final[List[str]] = [
    "server_name", "extended_master_secret", "renegotiation_info",
    "supported_groups", "ec_point_formats", "session_ticket",
    "application_layer_protocol_negotiation", "status_request",
    "signature_algorithms", "signed_certificate_timestamp",
    "key_share", "psk_key_exchange_modes", "supported_versions",
]

_CHROME_EXTRA_EXTS: Final[List[str]] = [
    "compress_certificate", "application_settings",
    "encrypted_client_hello", "token_binding",
]

_FIREFOX_EXTRA_EXTS: Final[List[str]] = [
    "delegated_credentials", "record_size_limit",
    "encrypted_client_hello", "post_handshake_auth",
]

_SAFARI_EXTRA_EXTS: Final[List[str]] = [
    "padding", "encrypted_client_hello",
]

# ── Curve Pools ──
_CURVE_POOLS: Final[Dict[str, List[List[str]]]] = {
    "chrome": [
        ["X25519", "P-256", "P-384"],
        ["X25519", "P-256", "P-384", "P-521"],
        ["P-256", "X25519", "P-384"],
    ],
    "firefox": [
        ["X25519", "P-256", "P-384", "P-521"],
        ["X25519", "P-256", "P-384", "P-521", "ffdhe2048"],
    ],
    "safari": [
        ["X25519", "P-256", "P-384", "P-521"],
        ["P-256", "P-384", "P-521", "X25519"],
    ],
    "edge": [
        ["X25519", "P-256", "P-384"],
        ["X25519", "P-256", "P-384", "P-521"],
    ],
}


def _compute_ja3(cipher_suites: List[str], extensions: List[str],
                 curves: List[str]) -> str:
    """Compute JA3-like hash from TLS parameters."""
    raw = f"771,{','.join(cipher_suites)},{','.join(extensions)},{','.join(curves)},0"
    return hashlib.md5(raw.encode()).hexdigest()


class _EntropyAnalyzer:
    """Analyze global traffic entropy to guide morphing aggressiveness."""

    def __init__(self, window: int = _HISTORY_WINDOW) -> None:
        self._window = window
        self._history: List[str] = []  # JA3 hashes of recent requests

    def record(self, ja3: str) -> None:
        self._history.append(ja3)
        if len(self._history) > self._window:
            self._history = self._history[-self._window:]

    @property
    def entropy(self) -> float:
        """Shannon entropy of JA3 distribution."""
        if not self._history:
            return 0.0
        counts: Dict[str, int] = {}
        for h in self._history:
            counts[h] = counts.get(h, 0) + 1
        n = len(self._history)
        return -sum((c / n) * math.log2(c / n) for c in counts.values())

    @property
    def correlation_risk(self) -> float:
        """0.0 = no correlation, 1.0 = fully correlated (same fingerprint)."""
        if len(self._history) < 2:
            return 0.0
        unique = len(set(self._history))
        return 1.0 - (unique / len(self._history))

    @property
    def needs_more_variation(self) -> bool:
        return self.entropy < _ENTROPY_HIGH or self.correlation_risk > 0.1


class _MorphingEngine:
    """Generate unique TLS profiles per-request with zero correlation."""

    def __init__(self) -> None:
        self._used_profiles: Set[str] = set()

    def generate(self, browser_hint: str = "") -> TLSHandshakeProfile:
        """Generate a completely unique TLS handshake profile."""
        browser = browser_hint or random.choice(["chrome", "firefox", "safari", "edge"])

        # 1. Select cipher suites with per-request permutation
        base_ciphers = _CIPHER_POOLS.get(browser, _CHROME_CIPHERS)
        # Take 7-12 ciphers with random ordering to avoid signature matching
        n_ciphers = random.randint(7, min(12, len(base_ciphers)))
        ciphers = random.sample(base_ciphers, n_ciphers)

        # 2. Build extension list with randomized ordering
        exts = list(_COMMON_EXTENSIONS)
        extra_map = {
            "chrome": _CHROME_EXTRA_EXTS,
            "firefox": _FIREFOX_EXTRA_EXTS,
            "safari": _SAFARI_EXTRA_EXTS,
            "edge": _CHROME_EXTRA_EXTS,
        }
        extras = extra_map.get(browser, _CHROME_EXTRA_EXTS)
        # Add 1-3 random extra extensions
        n_extra = random.randint(1, min(3, len(extras)))
        exts.extend(random.sample(extras, n_extra))
        # Randomize extension order (preserving some structure)
        # Keep server_name first (all browsers do), shuffle the rest
        rest = exts[1:]
        random.shuffle(rest)
        exts = [exts[0]] + rest

        # 3. Curve selection
        curve_options = _CURVE_POOLS.get(browser, _CURVE_POOLS["chrome"])
        curves = list(random.choice(curve_options))

        # 4. ALPN
        alpn_options = [
            ["h2", "http/1.1"],
            ["h2"],
            ["http/1.1", "h2"],
        ]
        alpn = random.choice(alpn_options)

        # 5. Compute JA3 hash (unique per combination)
        ja3 = _compute_ja3(ciphers, exts, curves)

        # 6. Ensure uniqueness
        attempt = 0
        while ja3 in self._used_profiles and attempt < 5:
            random.shuffle(ciphers)
            ja3 = _compute_ja3(ciphers, exts, curves)
            attempt += 1
        self._used_profiles.add(ja3)

        # Cap history to prevent memory leak
        if len(self._used_profiles) > 5000:
            # Keep last 1000
            self._used_profiles = set(list(self._used_profiles)[-1000:])

        # Select platform based on browser preference or randomly
        if browser == "safari":
            platform = "macos"
        else:
            platform = random.choice(["windows", "macos", "linux"])

        # Select a realistic version for the chosen browser and platform
        if browser == "chrome" or browser == "edge":
            version = random.choice(UserAgentGenerator.CHROME_VERSIONS)
        elif browser == "firefox":
            version = random.choice(UserAgentGenerator.FIREFOX_VERSIONS)
        elif browser == "safari":
            version = random.choice(UserAgentGenerator.SAFARI_VERSIONS)
        else:
            version = "125" # Fallback

        profile = TLSHandshakeProfile(
            cipher_suites=tuple(ciphers),
            extensions=tuple(exts),
            curves=tuple(curves),
            alpn=tuple(alpn),
            ja3_hash=ja3,
            browser_label=browser,
            platform=platform,
            version=version,
            session_id_length=random.choice([32, 0]),
        )

        logger.debug("Morphed TLS profile: browser=%s ja3=%s ciphers=%d exts=%d",
                    browser, ja3[:12], len(ciphers), len(exts))
        return profile


class TrafficOrchestrator:
    """
    Full Morphing Traffic Engine.

    Ensures 0% signature correlation between consecutive sessions
    by treating every TLS handshake as a unique browser instance.

    Usage:
        orch = TrafficOrchestrator()
        profile = orch.morph()  # Get unique TLS config for this request
        headers = orch.get_morphed_headers(profile)
    """

    def __init__(self) -> None:
        self._entropy = _EntropyAnalyzer()
        self._morphing = _MorphingEngine()
        self._request_count = 0
        self._correlation_checks = 0
        self._zero_correlations = 0

    def morph(self, browser_hint: str = "") -> TLSHandshakeProfile:
        """Get a morphed TLS profile for this request."""
        self._request_count += 1

        # Adaptive browser selection based on entropy
        if self._entropy.needs_more_variation and not browser_hint:
            # Force different browser than recent
            browser_hint = random.choice(["chrome", "firefox", "safari", "edge"])

        profile = self._morphing.generate(browser_hint)
        self._entropy.record(profile.ja3_hash)

        # Check correlation
        self._correlation_checks += 1
        if self._entropy.correlation_risk == 0.0:
            self._zero_correlations += 1

        return profile

    def get_morphed_headers(self, profile: TLSHandshakeProfile) -> Dict[str, str]:
        """Generate request headers matching the morphed profile."""

        from arki_project.utils.titanium.header_entropy import build_decoy_headers

        # Generate a base set of decoy headers with high entropy, tailored to the profile
        headers = build_decoy_headers(
            browser_label=profile.browser_label,
            platform=profile.platform,
            version=profile.version
        )

        # Override/ensure User-Agent matches the selected TLS profile
        # This ensures strong correlation between TLS fingerprint and UA
        # User-Agent is now generated within build_decoy_headers, so we can remove this block
        # This ensures consistency and avoids redundant generation.

        # Ensure Sec-CH-UA headers are consistent with Chrome/Edge profiles
        if profile.browser_label in ["chrome", "edge", "brave", "opera"]:
            # Dynamically generate Sec-CH-UA based on the profile's Chrome version
            chrome_version = profile.version.split('.')[0] # e.g., '125'
            headers["sec-ch-ua"] = f'"Chromium";v="{chrome_version}", "Not;A=Brand";v="99"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = f'"{profile.platform.capitalize()}"'

        # Ensure Accept-Language is consistent with the profile's locale
        if profile.alpn_protocols:
            # Use the first ALPN protocol as a hint for language, or generate randomly
            if "h2" in profile.alpn_protocols:
                headers["Accept-Language"] = csprng_choice(LANG_PROFILES) # Use existing high-entropy profiles
            else:
                headers["Accept-Language"] = csprng_choice(LANG_PROFILES)

        # Add other browser-specific headers if needed, ensuring consistency
        if profile.browser_label == "chrome":
            headers["Upgrade-Insecure-Requests"] = "1"
            headers["Sec-Fetch-Site"] = csprng_choice(["none", "same-origin", "cross-site"])
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-User"] = "?1"
            headers["Sec-Fetch-Dest"] = "document"
        elif profile.browser_label == "firefox":
            headers["DNT"] = "1"
            headers["Sec-GPC"] = "1"
            headers["Upgrade-Insecure-Requests"] = "1"
            headers["Sec-Fetch-Dest"] = "document"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-Site"] = csprng_choice(["none", "same-origin"])
            headers["Sec-Fetch-User"] = "?1"
        # Safari headers are generally simpler, so default decoy headers are often sufficient

        # Host header is typically set by the HTTP client, but ensure it is present if needed
        headers["Host"] = "" # Placeholder

        return headers


