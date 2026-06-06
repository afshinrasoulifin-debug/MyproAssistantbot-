
from __future__ import annotations
"""
utils/tls_fingerprint.py — Real TLS/JA3/JA4 Fingerprint Engine v1.0-TITAN
═══════════════════════════════════════════════════════════════════════════
Transport-level TLS fingerprint spoofing.

Problem: Playwright/Chrome uses its own TLS stack. Bot detectors compare
the TLS ClientHello (JA3 hash) against the claimed User-Agent.
If UA says "Chrome 125" but JA3 says "Python/aiohttp" → instant block.

Solution layers:
1. curl_cffi integration (impersonates real browser TLS stacks)
2. tls-client integration (Go-based, supports JA3 injection)
3. Custom cipher suite ordering for aiohttp/httpx sessions
4. JA3/JA4 hash computation and validation
5. Per-browser TLS profiles with exact cipher/extension ordering

Author: Arki Engine TITAN
License: Proprietary
"""


import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Final, List, Optional

logger = logging.getLogger("arki.tls_fingerprint")

# ═══════════════════════════════════════════════════════════
# TLS Constants
# ═══════════════════════════════════════════════════════════

class TLSVersion(Enum):
    TLS_1_0 = 0x0301
    TLS_1_1 = 0x0302
    TLS_1_2 = 0x0303
    TLS_1_3 = 0x0304


# Cipher suite hex codes used by real browsers
class CipherSuite:
    """Standard TLS cipher suite identifiers."""
    # TLS 1.3
    AES_128_GCM_SHA256 = 0x1301
    AES_256_GCM_SHA384 = 0x1302
    CHACHA20_POLY1305_SHA256 = 0x1303

    # TLS 1.2 (ECDHE)
    ECDHE_ECDSA_AES_128_GCM_SHA256 = 0xC02B
    ECDHE_RSA_AES_128_GCM_SHA256 = 0xC02F
    ECDHE_ECDSA_AES_256_GCM_SHA384 = 0xC02C
    ECDHE_RSA_AES_256_GCM_SHA384 = 0xC030
    ECDHE_ECDSA_CHACHA20_POLY1305 = 0xCCA9
    ECDHE_RSA_CHACHA20_POLY1305 = 0xCCA8
    ECDHE_RSA_AES_128_CBC_SHA = 0xC013
    ECDHE_RSA_AES_256_CBC_SHA = 0xC014
    RSA_AES_128_GCM_SHA256 = 0x009C
    RSA_AES_256_GCM_SHA384 = 0x009D
    RSA_AES_128_CBC_SHA = 0x002F
    RSA_AES_256_CBC_SHA = 0x0035

    # GREASE values (Google Random Extensions And Security Extensions)
    GREASE_VALUES = [
        0x0A0A, 0x1A1A, 0x2A2A, 0x3A3A, 0x4A4A,
        0x5A5A, 0x6A6A, 0x7A7A, 0x8A8A, 0x9A9A,
        0xAAAA, 0xBABA, 0xCACA, 0xDADA, 0xEAEA, 0xFAFA,
    ]


# TLS Extension IDs
class TLSExtension:
    SERVER_NAME = 0
    EC_POINT_FORMATS = 11
    SUPPORTED_GROUPS = 10
    SESSION_TICKET = 35
    ENCRYPT_THEN_MAC = 22
    EXTENDED_MASTER_SECRET = 23
    SIGNATURE_ALGORITHMS = 13
    SUPPORTED_VERSIONS = 43
    PSK_KEY_EXCHANGE_MODES = 45
    KEY_SHARE = 51
    APPLICATION_LAYER_PROTOCOL = 16
    STATUS_REQUEST = 5
    SIGNED_CERTIFICATE_TIMESTAMP = 18
    PADDING = 21
    RENEGOTIATION_INFO = 0xFF01
    COMPRESSED_CERTIFICATE = 27
    APPLICATION_SETTINGS = 0x4469
    DELEGATED_CREDENTIALS = 34
    RECORD_SIZE_LIMIT = 28
    GREASE = 0x0A0A  # placeholder, actual varies


# ═══════════════════════════════════════════════════════════
# JA3 Hash Computation
# ═══════════════════════════════════════════════════════════

@dataclass
class JA3Components:
    """Components that make up a JA3 fingerprint."""
    tls_version: int = TLSVersion.TLS_1_2.value
    cipher_suites: List[int] = field(default_factory=list)
    extensions: List[int] = field(default_factory=list)
    elliptic_curves: List[int] = field(default_factory=list)
    ec_point_formats: List[int] = field(default_factory=list)

    def compute_hash(self) -> str:
        """Compute JA3 hash from components."""
        # Filter out GREASE values
        grease = set(CipherSuite.GREASE_VALUES)
        ciphers = [c for c in self.cipher_suites if c not in grease]
        exts = [e for e in self.extensions if e not in grease]
        curves = [c for c in self.elliptic_curves if c not in grease]

        parts = [
            str(self.tls_version),
            "-".join(str(c) for c in ciphers),
            "-".join(str(e) for e in exts),
            "-".join(str(c) for c in curves),
            "-".join(str(f) for f in self.ec_point_formats),
        ]
        ja3_string = ",".join(parts)
        return hashlib.md5(ja3_string.encode()).hexdigest()

    def to_string(self) -> str:
        """Return the raw JA3 string (before hashing)."""
        grease = set(CipherSuite.GREASE_VALUES)
        ciphers = [c for c in self.cipher_suites if c not in grease]
        exts = [e for e in self.extensions if e not in grease]
        curves = [c for c in self.elliptic_curves if c not in grease]
        parts = [
            str(self.tls_version),
            "-".join(str(c) for c in ciphers),
            "-".join(str(e) for e in exts),
            "-".join(str(c) for c in curves),
            "-".join(str(f) for f in self.ec_point_formats),
        ]
        return ",".join(parts)


@dataclass
class JA4Components:
    """JA4 fingerprint (successor to JA3)."""
    protocol: str = "t"          # t=TCP, q=QUIC
    tls_version: str = "13"      # 10, 11, 12, 13
    sni: str = "d"               # d=domain, i=IP
    cipher_count: int = 0
    extension_count: int = 0
    alpn_first: str = "h2"       # h2, h1
    cipher_suites_sorted: List[int] = field(default_factory=list)
    extensions_sorted: List[int] = field(default_factory=list)
    signature_algorithms: List[int] = field(default_factory=list)

    def compute_hash(self) -> str:
        """Compute JA4 fingerprint string."""
        # JA4_a: protocol + version + sni + cipher_count + ext_count + alpn
        ja4_a = f"{self.protocol}{self.tls_version}{self.sni}{self.cipher_count:02d}{self.extension_count:02d}{self.alpn_first}"

        # JA4_b: sorted cipher suites hash (first 12 chars of SHA256)
        cipher_str = ",".join(f"{c:04x}" for c in sorted(self.cipher_suites_sorted))
        ja4_b = hashlib.sha256(cipher_str.encode()).hexdigest()[:12]

        # JA4_c: sorted extensions + signature algorithms hash
        ext_str = ",".join(f"{e:04x}" for e in sorted(self.extensions_sorted))
        sig_str = ",".join(f"{s:04x}" for s in self.signature_algorithms)
        combined = f"{ext_str}_{sig_str}"
        ja4_c = hashlib.sha256(combined.encode()).hexdigest()[:12]

        return f"{ja4_a}_{ja4_b}_{ja4_c}"


# ═══════════════════════════════════════════════════════════
# Real Browser TLS Profiles
# ═══════════════════════════════════════════════════════════

@dataclass
class RealTLSProfile:
    """Complete TLS ClientHello profile mimicking a real browser."""
    name: str
    browser: str
    version: str
    platform: str

    # ClientHello fields
    tls_version: int = TLSVersion.TLS_1_2.value  # record layer
    supported_versions: List[int] = field(default_factory=list)
    cipher_suites: List[int] = field(default_factory=list)
    extensions: List[int] = field(default_factory=list)
    elliptic_curves: List[int] = field(default_factory=list)  # supported_groups
    ec_point_formats: List[int] = field(default_factory=list)
    signature_algorithms: List[int] = field(default_factory=list)
    alpn_protocols: List[str] = field(default_factory=list)

    # GREASE insertion points
    grease_cipher_index: int = 0   # Where to insert GREASE in ciphers
    grease_extension_indices: List[int] = field(default_factory=list)

    # curl_cffi impersonate string
    curl_impersonate: str = ""

    # Pre-computed hashes
    ja3_hash: str = ""
    ja4_hash: str = ""

    def get_ja3(self) -> JA3Components:
        """Get JA3 components for this profile."""
        return JA3Components(
            tls_version=self.tls_version,
            cipher_suites=self.cipher_suites,
            extensions=self.extensions,
            elliptic_curves=self.elliptic_curves,
            ec_point_formats=self.ec_point_formats,
        )


# Chrome 125 on Windows (most common browser, most scrutinized)
CHROME_125_WIN = RealTLSProfile(
    name="chrome_125_win",
    browser="chrome",
    version="125",
    platform="windows",
    tls_version=TLSVersion.TLS_1_2.value,
    supported_versions=[TLSVersion.TLS_1_3.value, TLSVersion.TLS_1_2.value],
    cipher_suites=[
        CipherSuite.AES_128_GCM_SHA256,
        CipherSuite.AES_256_GCM_SHA384,
        CipherSuite.CHACHA20_POLY1305_SHA256,
        CipherSuite.ECDHE_ECDSA_AES_128_GCM_SHA256,
        CipherSuite.ECDHE_RSA_AES_128_GCM_SHA256,
        CipherSuite.ECDHE_ECDSA_AES_256_GCM_SHA384,
        CipherSuite.ECDHE_RSA_AES_256_GCM_SHA384,
        CipherSuite.ECDHE_ECDSA_CHACHA20_POLY1305,
        CipherSuite.ECDHE_RSA_CHACHA20_POLY1305,
        CipherSuite.ECDHE_RSA_AES_128_CBC_SHA,
        CipherSuite.ECDHE_RSA_AES_256_CBC_SHA,
        CipherSuite.RSA_AES_128_GCM_SHA256,
        CipherSuite.RSA_AES_256_GCM_SHA384,
        CipherSuite.RSA_AES_128_CBC_SHA,
        CipherSuite.RSA_AES_256_CBC_SHA,
    ],
    extensions=[
        TLSExtension.SERVER_NAME,
        TLSExtension.EXTENDED_MASTER_SECRET,
        TLSExtension.RENEGOTIATION_INFO,
        TLSExtension.SUPPORTED_GROUPS,
        TLSExtension.EC_POINT_FORMATS,
        TLSExtension.SESSION_TICKET,
        TLSExtension.APPLICATION_LAYER_PROTOCOL,
        TLSExtension.STATUS_REQUEST,
        TLSExtension.SIGNATURE_ALGORITHMS,
        TLSExtension.SIGNED_CERTIFICATE_TIMESTAMP,
        TLSExtension.KEY_SHARE,
        TLSExtension.PSK_KEY_EXCHANGE_MODES,
        TLSExtension.SUPPORTED_VERSIONS,
        TLSExtension.COMPRESSED_CERTIFICATE,
        TLSExtension.APPLICATION_SETTINGS,
        TLSExtension.PADDING,
    ],
    elliptic_curves=[0x001D, 0x0017, 0x0018, 0x0019, 0x0100, 0x0101],
    ec_point_formats=[0],
    signature_algorithms=[
        0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501,
        0x0806, 0x0601, 0x0201,
    ],
    alpn_protocols=["h2", "http/1.1"],
    grease_cipher_index=0,
    grease_extension_indices=[0, 4],
    curl_impersonate="chrome125",
    ja3_hash="cd08e31494f9531f560d64c695473da9",
)

CHROME_125_MAC = RealTLSProfile(
    name="chrome_125_mac",
    browser="chrome",
    version="125",
    platform="macos",
    tls_version=TLSVersion.TLS_1_2.value,
    supported_versions=[TLSVersion.TLS_1_3.value, TLSVersion.TLS_1_2.value],
    cipher_suites=CHROME_125_WIN.cipher_suites.copy(),
    extensions=CHROME_125_WIN.extensions.copy(),
    elliptic_curves=CHROME_125_WIN.elliptic_curves.copy(),
    ec_point_formats=[0],
    signature_algorithms=CHROME_125_WIN.signature_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    curl_impersonate="chrome125",
    ja3_hash="cd08e31494f9531f560d64c695473da9",
)

FIREFOX_126_WIN = RealTLSProfile(
    name="firefox_126_win",
    browser="firefox",
    version="126",
    platform="windows",
    tls_version=TLSVersion.TLS_1_2.value,
    supported_versions=[TLSVersion.TLS_1_3.value, TLSVersion.TLS_1_2.value],
    cipher_suites=[
        CipherSuite.AES_128_GCM_SHA256,
        CipherSuite.CHACHA20_POLY1305_SHA256,
        CipherSuite.AES_256_GCM_SHA384,
        CipherSuite.ECDHE_ECDSA_AES_128_GCM_SHA256,
        CipherSuite.ECDHE_RSA_AES_128_GCM_SHA256,
        CipherSuite.ECDHE_ECDSA_CHACHA20_POLY1305,
        CipherSuite.ECDHE_RSA_CHACHA20_POLY1305,
        CipherSuite.ECDHE_ECDSA_AES_256_GCM_SHA384,
        CipherSuite.ECDHE_RSA_AES_256_GCM_SHA384,
        CipherSuite.ECDHE_RSA_AES_128_CBC_SHA,
        CipherSuite.ECDHE_RSA_AES_256_CBC_SHA,
        CipherSuite.RSA_AES_128_GCM_SHA256,
        CipherSuite.RSA_AES_256_GCM_SHA384,
        CipherSuite.RSA_AES_128_CBC_SHA,
        CipherSuite.RSA_AES_256_CBC_SHA,
    ],
    extensions=[
        TLSExtension.SERVER_NAME,
        TLSExtension.EXTENDED_MASTER_SECRET,
        TLSExtension.RENEGOTIATION_INFO,
        TLSExtension.SUPPORTED_GROUPS,
        TLSExtension.EC_POINT_FORMATS,
        TLSExtension.SESSION_TICKET,
        TLSExtension.APPLICATION_LAYER_PROTOCOL,
        TLSExtension.STATUS_REQUEST,
        TLSExtension.DELEGATED_CREDENTIALS,
        TLSExtension.KEY_SHARE,
        TLSExtension.PSK_KEY_EXCHANGE_MODES,
        TLSExtension.SUPPORTED_VERSIONS,
        TLSExtension.SIGNATURE_ALGORITHMS,
        TLSExtension.RECORD_SIZE_LIMIT,
        TLSExtension.PADDING,
    ],
    elliptic_curves=[0x001D, 0x0017, 0x0018, 0x0100, 0x0101],
    ec_point_formats=[0],
    signature_algorithms=[
        0x0403, 0x0503, 0x0603, 0x0804, 0x0805, 0x0806,
        0x0401, 0x0501, 0x0601, 0x0203, 0x0201,
    ],
    alpn_protocols=["h2", "http/1.1"],
    curl_impersonate="firefox126",
    ja3_hash="b32309a26951912be7dba376398abc3b",
)

SAFARI_17_MAC = RealTLSProfile(
    name="safari_17_mac",
    browser="safari",
    version="17.5",
    platform="macos",
    tls_version=TLSVersion.TLS_1_2.value,
    supported_versions=[TLSVersion.TLS_1_3.value, TLSVersion.TLS_1_2.value],
    cipher_suites=[
        CipherSuite.AES_128_GCM_SHA256,
        CipherSuite.AES_256_GCM_SHA384,
        CipherSuite.CHACHA20_POLY1305_SHA256,
        CipherSuite.ECDHE_ECDSA_AES_256_GCM_SHA384,
        CipherSuite.ECDHE_ECDSA_AES_128_GCM_SHA256,
        CipherSuite.ECDHE_ECDSA_CHACHA20_POLY1305,
        CipherSuite.ECDHE_RSA_AES_256_GCM_SHA384,
        CipherSuite.ECDHE_RSA_AES_128_GCM_SHA256,
        CipherSuite.ECDHE_RSA_CHACHA20_POLY1305,
        CipherSuite.ECDHE_ECDSA_AES_256_GCM_SHA384,
        CipherSuite.RSA_AES_256_GCM_SHA384,
        CipherSuite.RSA_AES_128_GCM_SHA256,
    ],
    extensions=[
        TLSExtension.SERVER_NAME,
        TLSExtension.EXTENDED_MASTER_SECRET,
        TLSExtension.RENEGOTIATION_INFO,
        TLSExtension.SUPPORTED_GROUPS,
        TLSExtension.EC_POINT_FORMATS,
        TLSExtension.APPLICATION_LAYER_PROTOCOL,
        TLSExtension.STATUS_REQUEST,
        TLSExtension.SIGNATURE_ALGORITHMS,
        TLSExtension.SIGNED_CERTIFICATE_TIMESTAMP,
        TLSExtension.KEY_SHARE,
        TLSExtension.PSK_KEY_EXCHANGE_MODES,
        TLSExtension.SUPPORTED_VERSIONS,
        TLSExtension.PADDING,
    ],
    elliptic_curves=[0x001D, 0x0017, 0x0018, 0x0019],
    ec_point_formats=[0],
    signature_algorithms=[
        0x0403, 0x0503, 0x0603, 0x0804, 0x0805, 0x0806,
        0x0401, 0x0501, 0x0601,
    ],
    alpn_protocols=["h2", "http/1.1"],
    curl_impersonate="safari17_5",
    ja3_hash="773906b0efdefa24a7f2b8eb6985bf37",
)

EDGE_125_WIN = RealTLSProfile(
    name="edge_125_win",
    browser="edge",
    version="125",
    platform="windows",
    tls_version=CHROME_125_WIN.tls_version,
    supported_versions=CHROME_125_WIN.supported_versions.copy(),
    cipher_suites=CHROME_125_WIN.cipher_suites.copy(),
    extensions=CHROME_125_WIN.extensions.copy(),
    elliptic_curves=CHROME_125_WIN.elliptic_curves.copy(),
    ec_point_formats=[0],
    signature_algorithms=CHROME_125_WIN.signature_algorithms.copy(),
    alpn_protocols=["h2", "http/1.1"],
    curl_impersonate="chrome125",
    ja3_hash=CHROME_125_WIN.ja3_hash,
)

# Profile registry
ALL_TLS_PROFILES: Final[Dict[str, RealTLSProfile]] = {
    "chrome_125_win": CHROME_125_WIN,
    "chrome_125_mac": CHROME_125_MAC,
    "firefox_126_win": FIREFOX_126_WIN,
    "safari_17_mac": SAFARI_17_MAC,
    "edge_125_win": EDGE_125_WIN,
}


# ═══════════════════════════════════════════════════════════
# TLS Fingerprint Engine
# ═══════════════════════════════════════════════════════════

# Check for curl_cffi (best option for real TLS spoofing)
try:
    from curl_cffi.requests import AsyncSession as CurlAsyncSession
    CURL_CFFI_AVAILABLE: bool = True
except ImportError:
    CURL_CFFI_AVAILABLE = False

# Check for tls_client (Go-based alternative)
try:
    import tls_client
    TLS_CLIENT_AVAILABLE: bool = True
except ImportError:
    TLS_CLIENT_AVAILABLE = False


class TLSFingerprintEngine:
    """
    Real TLS fingerprint spoofing engine.

    Priority:
    1. curl_cffi — Best: replays exact Chrome/Firefox/Safari TLS handshake
    2. tls_client — Good: Go crypto/tls with JA3 injection
    3. Standard aiohttp/httpx — Fallback: only header spoofing, TLS fingerprint
       will be Python's default (detectable by advanced WAFs)
    """

    def __init__(self, default_profile: str = "chrome_125_win") -> None:
        self._default_profile_name = default_profile
        self._default_profile = ALL_TLS_PROFILES.get(default_profile, CHROME_125_WIN)
        self._sessions: Dict[str, Any] = {}

        # Stats
        self._stats = {
            "requests_sent": 0,
            "curl_cffi_used": 0,
            "tls_client_used": 0,
            "fallback_used": 0,
        }

        logger.info(
            "🔐 TLSFingerprintEngine initialized (curl_cffi: %s, tls_client: %s)",
            "✅" if CURL_CFFI_AVAILABLE else "❌",
            "✅" if TLS_CLIENT_AVAILABLE else "❌",
        )

    def get_best_backend(self) -> str:
        """Return the best available TLS backend."""
        if CURL_CFFI_AVAILABLE:
            return "curl_cffi"
        if TLS_CLIENT_AVAILABLE:
            return "tls_client"
        return "fallback"

    def select_profile(self, browser: str = "chrome", platform: str = "windows") -> RealTLSProfile:
        """Select a matching TLS profile for the given browser/platform."""
        key = f"{browser.lower()}_{platform.lower()}"
        # Try exact match
        for name, profile in ALL_TLS_PROFILES.items():
            if profile.browser == browser.lower() and profile.platform == platform.lower():
                return profile
        # Try browser-only match
        for name, profile in ALL_TLS_PROFILES.items():
            if profile.browser == browser.lower():
                return profile
        return self._default_profile

    async def create_session(
        self,
        profile: Optional[RealTLSProfile] = None,
        proxy: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> "TLSSession":
        """Create a TLS session with the specified profile.

        Returns a TLSSession wrapper that abstracts the backend.
        """
        prof = profile or self._default_profile

        if CURL_CFFI_AVAILABLE and prof.curl_impersonate:
            session = TLSSession(
                backend="curl_cffi",
                profile=prof,
                proxy=proxy,
                headers=headers,
            )
            await session._init_curl_cffi()
            self._stats["curl_cffi_used"] += 1
        elif TLS_CLIENT_AVAILABLE:
            session = TLSSession(
                backend="tls_client",
                profile=prof,
                proxy=proxy,
                headers=headers,
            )
            session._init_tls_client()
            self._stats["tls_client_used"] += 1
        else:
            session = TLSSession(
                backend="fallback",
                profile=prof,
                proxy=proxy,
                headers=headers,
            )
            self._stats["fallback_used"] += 1

        session_id = f"{prof.name}_{id(session)}"
        self._sessions[session_id] = session
        return session

    def validate_ja3(self, profile: RealTLSProfile, observed_ja3: str) -> bool:
        """Validate that observed JA3 matches the expected profile."""
        expected = profile.get_ja3().compute_hash()
        match = expected == observed_ja3
        if not match:
            logger.warning(
                "⚠️ JA3 mismatch! Expected %s (%s) but got %s",
                expected, profile.name, observed_ja3,
            )
        return match

    def compute_ja3(self, profile: RealTLSProfile) -> str:
        """Compute the JA3 hash for a profile."""
        return profile.get_ja3().compute_hash()

    def compute_ja4(self, profile: RealTLSProfile) -> str:
        """Compute the JA4 hash for a profile."""
        grease = set(CipherSuite.GREASE_VALUES)
        ciphers = [c for c in profile.cipher_suites if c not in grease]
        exts = [e for e in profile.extensions if e not in grease]

        ja4 = JA4Components(
            protocol="t",
            tls_version="13" if TLSVersion.TLS_1_3.value in profile.supported_versions else "12",
            sni="d",
            cipher_count=len(ciphers),
            extension_count=len(exts),
            alpn_first=profile.alpn_protocols[0] if profile.alpn_protocols else "h1",
            cipher_suites_sorted=ciphers,
            extensions_sorted=exts,
            signature_algorithms=profile.signature_algorithms,
        )
        return ja4.compute_hash()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "backend": self.get_best_backend(),
            "profiles": len(ALL_TLS_PROFILES),
            "active_sessions": len(self._sessions),
            **self._stats,
        }


class TLSSession:
    """
    Abstracted TLS session that wraps curl_cffi, tls_client, or fallback.

    Usage:
        engine = TLSFingerprintEngine()
        session = await engine.create_session(profile=CHROME_125_WIN)
        response = await session.get("https://example.com")
        await session.close()
    """

    def __init__(
        self,
        backend: str,
        profile: RealTLSProfile,
        proxy: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.backend = backend
        self.profile = profile
        self.proxy = proxy
        self.headers = headers or {}
        self._session: Any = None
        self._closed = False

    async def _init_curl_cffi(self) -> None:
        """Initialize curl_cffi session with browser impersonation."""
        if not CURL_CFFI_AVAILABLE:
            return
        self._session = CurlAsyncSession(
            impersonate=self.profile.curl_impersonate,
            headers=self.headers,
            proxies={"https": self.proxy, "http": self.proxy} if self.proxy else None,
        )

    def _init_tls_client(self) -> None:
        """Initialize tls_client session."""
        if not TLS_CLIENT_AVAILABLE:
            return
        # Map profile to tls_client identifier
        client_id_map = {
            "chrome": "chrome_125",
            "firefox": "firefox_126",
            "safari": "safari_17_5",
        }
        client_id = client_id_map.get(self.profile.browser, "chrome_125")
        self._session = tls_client.Session(
            client_identifier=client_id,
            random_tls_extension_order=True,
        )
        if self.proxy:
            self._session.proxies = {"https": self.proxy, "http": self.proxy}

    async def get(self, url: str, **kwargs) -> "TLSResponse":
        """Send GET request with spoofed TLS fingerprint."""
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> "TLSResponse":
        """Send POST request with spoofed TLS fingerprint."""
        return await self._request("POST", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs) -> "TLSResponse":
        """Internal request dispatcher."""
        merged_headers = {**self.headers, **kwargs.pop("headers", {})}

        if self.backend == "curl_cffi" and self._session:
            resp = await self._session.request(
                method, url, headers=merged_headers, **kwargs,
            )
            return TLSResponse(
                status_code=resp.status_code,
                headers=dict(resp.headers),
                text=resp.text,
                content=resp.content,
                url=str(resp.url),
            )

        elif self.backend == "tls_client" and self._session:
            if method.upper() == "GET":
                resp = self._session.get(url, headers=merged_headers, **kwargs)
            else:
                resp = self._session.post(url, headers=merged_headers, **kwargs)
            return TLSResponse(
                status_code=resp.status_code,
                headers=dict(resp.headers),
                text=resp.text,
                content=resp.content,
                url=url,
            )

        else:
            # Fallback: aiohttp (TLS fingerprint will be Python-default)
            import aiohttp
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(
                connector=connector, headers=merged_headers,
            ) as sess:
                async with sess.request(method, url, proxy=self.proxy, **kwargs) as resp:
                    content = await resp.read()
                    text = content.decode("utf-8", errors="replace")
                    return TLSResponse(
                        status_code=resp.status,
                        headers=dict(resp.headers),
                        text=text,
                        content=content,
                        url=str(resp.url),
                    )

    async def close(self) -> None:
        """Close the session."""
        if self._closed:
            return
        self._closed = True
        if self.backend == "curl_cffi" and self._session:
            await self._session.close()
        elif self.backend == "tls_client" and self._session:
            self._session.close()


@dataclass
class TLSResponse:
    """Unified response from any TLS backend."""
    status_code: int
    headers: Dict[str, str]
    text: str
    content: bytes
    url: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> Any:
        return json.loads(self.text)


# ═══════════════════════════════════════════════════════════
# GREASE Injection Helper
# ═══════════════════════════════════════════════════════════

class GREASEInjector:
    """
    Inject GREASE values into TLS ClientHello.

    GREASE (Generate Random Extensions And Sustain Extensibility)
    is used by Chrome to prevent extension ossification. Missing
    GREASE in a "Chrome" ClientHello is a detection signal.
    """

    import random as _rand

    @classmethod
    def get_random_grease(cls) -> int:
        """Get a random GREASE value."""
        return cls._rand.choice(CipherSuite.GREASE_VALUES)

    @classmethod
    def inject_into_ciphers(cls, ciphers: List[int], index: int = 0) -> List[int]:
        """Insert a GREASE value at the specified index."""
        result = ciphers.copy()
        result.insert(index, cls.get_random_grease())
        return result

    @classmethod
    def inject_into_extensions(cls, extensions: List[int], indices: Optional[List[int]] = None) -> List[int]:
        """Insert GREASE values at specified indices."""
        result = extensions.copy()
        for i, idx in enumerate(sorted(indices or [0])):
            result.insert(idx + i, cls.get_random_grease())
        return result


# ═══════════════════════════════════════════════════════════
# Module-level singleton
# ═══════════════════════════════════════════════════════════

tls_engine = TLSFingerprintEngine()


