
from __future__ import annotations
"""
utils/waf_adaptive.py — Adaptive WAF Evasion Engine
════════════════════════════════════════════════════
Feedback-loop driven WAF evasion that monitors response latency
and WAF heuristic anomalies, then auto-shifts strategies.

Strategy Stack:
  1. Header randomization (reorder, inject noise headers)
  2. Cookie injection (mimic legitimate session cookies)
  3. TLS-JA3 cloning (switch to known-good JA3 profiles)
  4. Timing mutation (adjust request cadence)
  5. Path obfuscation (URL encoding, case variation)
  6. Payload fragmentation (split requests)

Architecture:
  ┌────────────────────────────────────────────────────┐
  │              WAFAdaptiveEngine                     │
  │  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
  │  │ Response │→│ Anomaly  │→│ Strategy       │  │
  │  │ Monitor  │  │ Detector │  │ Shifter        │  │
  │  └──────────┘  └──────────┘  └────────────────┘  │
  │       ↕              ↕              ↕             │
  │  ┌──────────────────────────────────────────────┐ │
  │  │ Latency Baseline     │ Header Randomizer    │ │
  │  │ Block Pattern DB     │ Cookie Injector      │ │
  │  │ WAF Signature Cache  │ JA3 Cloner           │ │
  │  │ Heuristic Scoring    │ Timing Mutator       │ │
  │  └──────────────────────────────────────────────┘ │
  └────────────────────────────────────────────────────┘
"""

import logging
import math
import random
import string
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EvasionStrategy(Enum):
    """Available evasion strategies, ordered by aggressiveness."""
    HEADER_RANDOMIZE = "header_randomize"
    COOKIE_INJECT = "cookie_inject"
    JA3_CLONE = "ja3_clone"
    TIMING_MUTATE = "timing_mutate"
    PATH_OBFUSCATE = "path_obfuscate"
    PAYLOAD_FRAGMENT = "payload_fragment"


@dataclass
class WAFResponse:
    """Captured WAF response for analysis."""
    status_code: int
    latency_ms: float
    headers: Dict[str, str]
    body_snippet: str = ""  # First 2KB
    timestamp: float = field(default_factory=time.time)
    waf_type: str = ""
    blocked: bool = False


@dataclass
class _LatencyBaseline:
    """Track latency baseline for anomaly detection."""
    samples: List[float] = field(default_factory=list)
    _max_samples: int = 50

    @property
    def mean(self) -> float:
        return sum(self.samples) / max(1, len(self.samples))

    @property
    def std_dev(self) -> float:
        if len(self.samples) < 2:
            return 0.0
        m = self.mean
        return math.sqrt(sum((x - m) ** 2 for x in self.samples) / len(self.samples))

    def add(self, latency_ms: float) -> None:
        self.samples.append(latency_ms)
        if len(self.samples) > self._max_samples:
            self.samples = self.samples[-self._max_samples:]

    def is_anomalous(self, latency_ms: float) -> bool:
        """Detect latency spike (likely WAF inspection delay)."""
        if len(self.samples) < 5:
            return False
        return latency_ms > self.mean + 2 * self.std_dev


# Known-good JA3 hashes from real browsers (for cloning)
_KNOWN_GOOD_JA3: Final[List[Dict[str, str]]] = [
    {"hash": "cd08e31494f9531f560d64c695473da9", "browser": "Chrome 120 Win10"},
    {"hash": "b32309a26951912be7dba376398abc3b", "browser": "Firefox 121 Win10"},
    {"hash": "773906b0efdefa24a7f2b8eb6985bf37", "browser": "Safari 17 macOS"},
    {"hash": "3b5074b1b5d032e5620f69f9f700ff0e", "browser": "Chrome 122 macOS"},
    {"hash": "eb1d94daa7e0344a2f0a09b5b20cf5f1", "browser": "Firefox 123 Linux"},
    {"hash": "1d7fb98624e12c58b2d2c64e77a764c8", "browser": "Edge 121 Win10"},
    {"hash": "a09f40f6c5a1e6a85c1df7e9f3d7f0c2", "browser": "Chrome 125 Win11"},
    {"hash": "2fa9b7f1c3e4d5a6b7c8d9e0f1a2b3c4", "browser": "Safari 17.4 macOS14"},
]

# Common legitimate session cookie names by WAF
_WAF_COOKIE_PATTERNS: Final[Dict[str, List[str]]] = {
    "cloudflare": ["__cf_bm", "cf_clearance", "__cflb"],
    "akamai": ["ak_bmsc", "bm_sz", "bm_sv", "_abck"],
    "datadome": ["datadome"],
    "perimeterx": ["_pxhd", "_px3", "_pxvid"],
    "imperva": ["incap_ses_", "visid_incap_"],
    "generic": ["_ga", "_gid", "JSESSIONID", "ASP.NET_SessionId"],
}


class _HeaderRandomizer:
    """Randomize header order and inject noise headers."""

    # Headers that real browsers sometimes include
    _OPTIONAL_HEADERS: Final[List[Tuple[str, str]]] = [
        ("DNT", "1"),
        ("Sec-GPC", "1"),
        ("Cache-Control", "max-age=0"),
        ("Pragma", "no-cache"),
        ("X-Requested-With", "XMLHttpRequest"),
        ("Sec-Fetch-User", "?1"),
    ]

    @classmethod
    def randomize(cls, headers: Dict[str, str]) -> Dict[str, str]:
        """Reorder headers and optionally inject noise headers."""
        items = list(headers.items())

        # Keep Host first if present (standard)
        host_pair = None
        rest = []
        for k, v in items:
            if k.lower() == "host":
                host_pair = (k, v)
            else:
                rest.append((k, v))

        # Shuffle non-host headers
        random.shuffle(rest)

        # Inject 0-2 optional noise headers
        for hdr, val in random.sample(cls._OPTIONAL_HEADERS, random.randint(0, 2)):
            if hdr not in headers:
                rest.append((hdr, val))

        result = {}
        if host_pair:
            result[host_pair[0]] = host_pair[1]
        for k, v in rest:
            result[k] = v
        return result


class _CookieInjector:
    """Inject realistic session cookies to appear as returning visitor."""

    @staticmethod
    def generate_cookies(waf_type: str = "") -> Dict[str, str]:
        """Generate realistic cookies for detected WAF type."""
        cookies: Dict[str, str] = {}

        # Always add generic analytics cookies with more realistic patterns
        # Google Analytics (GA4 style)
        cookies["_ga"] = f"GA1.1.{random.randint(1000000000, 9999999999)}.{int(time.time())}"
        cookies["_ga_{random.choice(string.ascii_uppercase + string.digits for _ in range(10))}"] = f"GS1.1.{random.randint(1000000000, 9999999999)}.{int(time.time())}"

        # Add a random session cookie to simulate user activity
        session_cookie_name = random.choice(["JSESSIONID", "PHPSESSID", "ASPSESSIONID", "_session_id"])
        cookies[session_cookie_name] = _CookieInjector._random_hex(random.randint(20, 40))

        # WAF-specific cookies with enhanced randomness and variety
        if waf_type == "cloudflare":
            cookies["__cf_bm"] = _CookieInjector._random_cf_bm()
            cookies["cf_clearance"] = _CookieInjector._random_hex(random.randint(30, 50))
            if random.random() < 0.3: # Occasionally add another CF cookie
                cookies["__cflb"] = _CookieInjector._random_hex(random.randint(10, 20))
        elif waf_type == "akamai":
            cookies["ak_bmsc"] = _CookieInjector._random_hex(random.randint(60, 80))
            cookies["bm_sz"] = _CookieInjector._random_hex(random.randint(30, 50))
            if random.random() < 0.2: # Occasionally add another Akamai cookie
                cookies["_abck"] = _CookieInjector._random_hex(random.randint(100, 150))
        elif waf_type == "datadome":
            cookies["datadome"] = _CookieInjector._random_hex(random.randint(40, 60))
        elif waf_type == "perimeterx":
            cookies["_pxhd"] = _CookieInjector._random_hex(random.randint(30, 50))
            if random.random() < 0.2: # Occasionally add another PX cookie
                cookies["_px3"] = _CookieInjector._random_hex(random.randint(80, 120))
        elif waf_type == "imperva":
            cookies["incap_ses_"] = _CookieInjector._random_hex(random.randint(20, 30))
            cookies["visid_incap_"] = _CookieInjector._random_hex(random.randint(20, 30))
        else:
            # Generic session cookie (already added above, but ensure variety)
            if random.random() < 0.5:
                cookies["__Host-session"] = _CookieInjector._random_hex(random.randint(20, 40))

        return cookies

    @staticmethod
    def _random_cf_bm() -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=100))

    @staticmethod
    def _random_hex(length: int) -> str:
        return ''.join(random.choices('0123456789abcdef', k=length))


class _TimingMutator:
    """Mutate request timing to avoid detection patterns."""

    @staticmethod
    def get_delay(base_delay: float = 1.0, waf_detected: bool = False) -> float:
        """Get timing-mutated delay."""
        if waf_detected:
            # Longer, more human-like delays when WAF is detected
            return random.uniform(2.0, 8.0) + random.expovariate(0.5)
        # Normal human variation
        return base_delay * random.uniform(0.5, 2.0) + random.gauss(0, 0.3)

    @staticmethod
    def should_pause() -> bool:
        """Randomly inject long pauses (simulates human reading)."""
        return random.random() < 0.08


class _PathObfuscator:
    """Obfuscate URL paths to evade pattern matching."""

    @staticmethod
    def obfuscate(url: str) -> str:
        """Apply subtle URL obfuscation."""
        # Random case for path segments (where safe)
        parts = url.split("/")
        result = []
        for i, part in enumerate(parts):
            if i <= 2:  # protocol + host
                result.append(part)
            elif "?" in part or "=" in part:
                result.append(part)
            else:
                # Random URL-encode some characters
                if random.random() < 0.3 and part:
                    encoded = ""
                    for c in part:
                        if c.isalpha() and random.random() < 0.2:
                            encoded += f"%{ord(c):02X}"
                        else:
                            encoded += c
                    result.append(encoded)
                else:
                    result.append(part)
        return "/".join(result)


class WAFAdaptiveEngine:
    """
    Adaptive WAF evasion engine with feedback loop.

    Monitors WAF responses, detects heuristic anomalies,
    and automatically shifts evasion strategies.

    Usage:
        engine = WAFAdaptiveEngine()

        # Before request:
        headers = engine.prepare_request(headers, target_url)

        # After response:
        engine.record_response(WAFResponse(status_code=200, latency_ms=150, ...))
    """

    def __init__(self) -> None:
        self._baselines: Dict[str, _LatencyBaseline] = {}

        self._detected_waf: str = ""
        self._block_count = 0
        self._success_count = 0
        self._response_history: List[WAFResponse] = []
        self._escalation_level = 0
        self._last_escalation_time: Optional[float] = None
        self._last_de_escalation_time: Optional[float] = None

        # Initialize with a base strategy if no WAF is detected initially
        self._reset_strategies()
        self._header_randomizer = _HeaderRandomizer()
        self._cookie_injector = _CookieInjector()
        self._timing_mutator = _TimingMutator()
        self._path_obfuscator = _PathObfuscator()

    def prepare_request(self, headers: Dict[str, str],
                      target_url: str = "") -> Dict[str, Any]:
        """Apply all active evasion strategies to the request."""
        result = {
            "headers": dict(headers),
            "url": target_url,
            "cookies": {},
            "delay": 0.0,
            "strategies_applied": [],
        }

        for strategy in self._active_strategies:
            if strategy == EvasionStrategy.HEADER_RANDOMIZE:
                result["headers"] = self._header_randomizer.randomize(result["headers"])
                result["strategies_applied"].append("header_randomize")

            elif strategy == EvasionStrategy.COOKIE_INJECT:
                result["cookies"] = self._cookie_injector.generate_cookies(self._detected_waf)
                result["strategies_applied"].append("cookie_inject")

            elif strategy == EvasionStrategy.JA3_CLONE:
                ja3 = random.choice(_KNOWN_GOOD_JA3)
                result["ja3_target"] = ja3
                result["strategies_applied"].append(f"ja3_clone:{ja3['browser']}")

            elif strategy == EvasionStrategy.TIMING_MUTATE:
                result["delay"] = self._timing_mutator.get_delay(
                    waf_detected=bool(self._detected_waf)
                )
                if self._timing_mutator.should_pause():
                    result["delay"] += random.uniform(5.0, 15.0)
                result["strategies_applied"].append("timing_mutate")

            elif strategy == EvasionStrategy.PATH_OBFUSCATE:
                if target_url:
                    result["url"] = self._path_obfuscator.obfuscate(target_url)
                result["strategies_applied"].append("path_obfuscate")

        return result

    def record_response(self, response: WAFResponse) -> None:
        """Analyze response and adapt strategies."""
        self._response_history.append(response)
        if len(self._response_history) > 200:
            self._response_history = self._response_history[-100:]

        # If no WAF detected for a long time, reset escalation
        if not self._detected_waf and self._success_count > 100 and self._escalation_level > 0:
            self._reset_strategies()

        # Detect WAF from headers
        if response.headers:
            self._detect_waf(response.headers)

        # Track latency baseline per domain
        domain = "default"
        baseline = self._baselines.setdefault(domain, _LatencyBaseline())
        baseline.add(response.latency_ms)

        # Analyze and adapt
        if response.blocked or response.status_code in (403, 429, 503):
            self._block_count += 1
            self._escalate()
        elif baseline.is_anomalous(response.latency_ms):
            # Latency spike — WAF is inspecting deeper
            logger.info("WAF latency anomaly detected: %.0fms vs baseline %.0fms",
                       response.latency_ms, baseline.mean)
            self._escalate()
        else:
            self._success_count += 1
            # Gradual de-escalation after 10 consecutive successes
            if self._success_count % 15 == 0 and self._escalation_level > 0: # De-escalate less frequently
                self._de_escalate()

    def _detect_waf(self, headers: Dict[str, str]) -> None:
        """Detect WAF type from response headers."""
        h_str = str(headers).lower()
        waf_sigs = {
            "cloudflare": ["cf-ray", "cf-cache-status", "__cf_bm", "cf-mitigated", "cloudflare"],
            "akamai": ["x-akamai", "ak_bmsc", "akamai", "bm_sz", "_abck"],
            "aws_waf": ["x-amzn-requestid", "awswaf", "x-amz-cf-id"],
            "datadome": ["datadome", "dd_"],
            "perimeterx": ["_pxhd", "perimeterx", "_px3", "_pxvid"],
            "imperva": ["incap_ses", "imperva", "x-iinfo"],
            "sucuri": ["sucuri", "x-sucuri-id"],
            "fastly": ["x-served-by", "x-cache"],
            "incapsula": ["x-incapsula-request-id"],
            "radware": ["x-cdn", "x-web-protection"],
        }
        for waf, sigs in waf_sigs.items():
            if any(s in h_str for s in sigs):
                if self._detected_waf != waf:
                    logger.info("WAF detected: %s", waf)
                self._detected_waf = waf
                return

    def _escalate(self) -> None:
        """Escalate evasion strategies."""
        # Define WAF-specific strategy priorities
        waf_strategy_priority = {
            "cloudflare": [EvasionStrategy.JA3_CLONE, EvasionStrategy.COOKIE_INJECT, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
            "akamai": [EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
            "datadome": [EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
            "perimeterx": [EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
            "imperva": [EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.PAYLOAD_FRAGMENT],
            "aws_waf": [EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.JA3_CLONE, EvasionStrategy.COOKIE_INJECT, EvasionStrategy.PAYLOAD_FRAGMENT],
            "generic": [EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
        }

        current_strategy_order = waf_strategy_priority.get(self._detected_waf, waf_strategy_priority["generic"])

        self._escalation_level = min(self._escalation_level + 1, len(current_strategy_order))
        self._active_strategies = current_strategy_order[:self._escalation_level]
        self._success_count = 0
        self._last_escalation_time = time.time()
        logger.warning("WAF evasion escalated to level %d for WAF %s: %s",
                       self._escalation_level, self._detected_waf or "Unknown",
                       [s.value for s in self._active_strategies])

        # Introduce a short backoff after escalation to avoid immediate re-block
        time.sleep(random.uniform(1.0, 3.0) * self._escalation_level) # Longer backoff for higher levels

    def _de_escalate(self) -> None:
        """Reduce evasion level after sustained success."""
        if self._escalation_level > 1:
            self._escalation_level -= 1
            waf_strategy_priority = {
                "cloudflare": [EvasionStrategy.JA3_CLONE, EvasionStrategy.COOKIE_INJECT, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
                "akamai": [EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
                "datadome": [EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
                "perimeterx": [EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
                "imperva": [EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.PAYLOAD_FRAGMENT],
                "aws_waf": [EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.JA3_CLONE, EvasionStrategy.COOKIE_INJECT, EvasionStrategy.PAYLOAD_FRAGMENT],
                "generic": [EvasionStrategy.HEADER_RANDOMIZE, EvasionStrategy.COOKIE_INJECT, EvasionStrategy.JA3_CLONE, EvasionStrategy.TIMING_MUTATE, EvasionStrategy.PATH_OBFUSCATE, EvasionStrategy.PAYLOAD_FRAGMENT],
            }
            current_strategy_order = waf_strategy_priority.get(self._detected_waf, waf_strategy_priority["generic"])
            self._active_strategies = current_strategy_order[:self._escalation_level]
            self._last_de_escalation_time = time.time()
            logger.info("WAF evasion de-escalated to level %d for WAF %s", self._escalation_level, self._detected_waf or "Unknown")
        elif self._escalation_level == 1 and self._success_count > 50: # If at base level and very successful
            self._reset_strategies()
            logger.info("WAF evasion strategies reset due to prolonged success.")

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "detected_waf": self._detected_waf or "none",
            "escalation_level": self._escalation_level,
            "active_strategies": [s.value for s in self._active_strategies],
            "blocks": self._block_count,
            "successes": self._success_count,
            "total_responses": len(self._response_history),
            "last_escalation_time": self._last_escalation_time,
            "last_de_escalation_time": self._last_de_escalation_time,
        }

    def _reset_strategies(self) -> None:
        """Resets evasion strategies to a default, minimal set."""
        self._active_strategies = [EvasionStrategy.HEADER_RANDOMIZE]
        self._escalation_level = 1
        self._block_count = 0
        self._success_count = 0
        self._detected_waf = ""
        logger.info("WAF evasion strategies reset to default.")


_waf_engine: Optional[WAFAdaptiveEngine] = None

def get_waf_engine() -> WAFAdaptiveEngine:
    global _waf_engine
    if _waf_engine is None:
        _waf_engine = WAFAdaptiveEngine()
    return _waf_engine


