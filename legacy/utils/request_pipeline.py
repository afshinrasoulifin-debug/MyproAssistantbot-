
from __future__ import annotations
"""
utils/request_pipeline.py — Intelligent Request Orchestration Engine v1.0-TITAN
════════════════════════════════════════════════════════════════════════════════
Orchestrates HTTP requests to appear as natural browser navigation:

 1. Referrer chain building (search engine → landing → internal nav)
 2. Realistic asset loading sequence (HTML→CSS→JS→fonts→images→XHR)
 3. Per-domain rate limiting & inter-request timing
 4. Navigation history simulation
 5. Cookie accumulation (natural buildup over browsing sessions)
 6. Retry with fingerprint rotation
 7. Resource prioritization (critical path vs deferred)
 8. Prefetch/preconnect simulation

Author: Arki Engine TITAN
License: Proprietary
"""


import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple
from collections import deque

logger = logging.getLogger("arki.request_pipeline")


# ═══════════════════════════════════════════════════════════
# Request Types & Constants
# ═══════════════════════════════════════════════════════════

class ResourceType(Enum):
    """Browser resource types in loading order."""
    DOCUMENT = "document"         # HTML page
    STYLESHEET = "stylesheet"     # CSS
    SCRIPT = "script"             # JavaScript
    FONT = "font"                 # Web fonts
    IMAGE = "image"               # Images
    XHR = "xhr"                   # AJAX/fetch
    WEBSOCKET = "websocket"       # WS connections
    MEDIA = "media"               # Video/audio
    MANIFEST = "manifest"         # Web app manifest
    PREFLIGHT = "preflight"       # CORS preflight
    OTHER = "other"


class RequestPriority(Enum):
    """Request priority levels (Chrome-like)."""
    HIGHEST = "highest"   # Main document
    HIGH = "high"         # CSS, critical JS
    MEDIUM = "medium"     # JS, fonts
    LOW = "low"           # Images, non-critical
    LOWEST = "lowest"     # Prefetch, analytics


# Resource loading order (simulates real browser)
RESOURCE_LOAD_ORDER: Dict[ResourceType, Tuple[int, RequestPriority]] = {
    ResourceType.DOCUMENT: (0, RequestPriority.HIGHEST),
    ResourceType.STYLESHEET: (1, RequestPriority.HIGH),
    ResourceType.SCRIPT: (2, RequestPriority.HIGH),
    ResourceType.FONT: (3, RequestPriority.MEDIUM),
    ResourceType.IMAGE: (4, RequestPriority.LOW),
    ResourceType.XHR: (5, RequestPriority.MEDIUM),
    ResourceType.MEDIA: (6, RequestPriority.LOW),
    ResourceType.MANIFEST: (7, RequestPriority.LOWEST),
}

# Realistic referrer chains
SEARCH_ENGINE_REFERRERS: List[str] = [
    "https://www.google.com/",
    "https://www.google.com/search?q=",
    "https://www.google.fi/",
    "https://www.bing.com/search?q=",
    "https://duckduckgo.com/?q=",
    "https://search.yahoo.com/search?p=",
]

SOCIAL_REFERRERS: List[str] = [
    "https://www.facebook.com/",
    "https://t.co/",
    "https://www.instagram.com/",
    "https://www.linkedin.com/",
    "https://www.reddit.com/",
    "https://www.pinterest.com/",
]

DIRECT_INDICATORS: List[str] = [
    "",  # Empty referrer = direct
    "android-app://com.google.android.gm/",  # Gmail app
]


# ═══════════════════════════════════════════════════════════
# Domain Rate Limiter
# ═══════════════════════════════════════════════════════════

@dataclass
class DomainState:
    """Track request state per domain."""
    domain: str
    request_count: int = 0
    last_request_time: float = 0
    total_bytes: int = 0
    cookies: Dict[str, str] = field(default_factory=dict)
    avg_latency_ms: float = 0
    errors: int = 0
    is_rate_limited: bool = False
    rate_limit_until: float = 0
    consecutive_fast_requests: int = 0

    @property
    def is_cooled_down(self) -> bool:
        return time.time() >= self.rate_limit_until

    def record_request(self, latency_ms: float = 0, bytes_received: int = 0) -> None:
        now = time.time()
        self.request_count += 1
        self.total_bytes += bytes_received

        # Update average latency (EMA)
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = 0.8 * self.avg_latency_ms + 0.2 * latency_ms

        # Detect suspicious fast request patterns
        if now - self.last_request_time < 0.1 and self.last_request_time > 0:
            self.consecutive_fast_requests += 1
        else:
            self.consecutive_fast_requests = 0

        self.last_request_time = now

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "request_count": self.request_count,
            "total_bytes": self.total_bytes,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "cookies_count": len(self.cookies),
            "errors": self.errors,
            "is_rate_limited": self.is_rate_limited and not self.is_cooled_down,
        }


class DomainRateLimiter:
    """
    Per-domain rate limiting with realistic inter-request delays.

    Prevents detection by rate-limiting APIs and also ensures
    requests look like natural browser behavior.
    """

    # Default delays per resource type (ms)
    DEFAULT_DELAYS: Dict[ResourceType, Tuple[float, float]] = {
        ResourceType.DOCUMENT: (500, 3000),
        ResourceType.STYLESHEET: (10, 100),
        ResourceType.SCRIPT: (10, 150),
        ResourceType.FONT: (20, 200),
        ResourceType.IMAGE: (10, 300),
        ResourceType.XHR: (100, 2000),
        ResourceType.MEDIA: (50, 500),
    }

    def __init__(
        self,
        max_requests_per_minute: int = 30,
        min_delay_ms: float = 200,
        max_delay_ms: float = 5000,
    ) -> None:
        self._domains: Dict[str, DomainState] = {}
        self._max_rpm = max_requests_per_minute
        self._min_delay = min_delay_ms
        self._max_delay = max_delay_ms
        self._global_request_times: Deque[float] = deque(maxlen=100)

    def get_domain_state(self, domain: str) -> DomainState:
        """Get or create domain state."""
        if domain not in self._domains:
            self._domains[domain] = DomainState(domain=domain)
        return self._domains[domain]

    def calculate_delay(
        self,
        domain: str,
        resource_type: ResourceType = ResourceType.DOCUMENT,
    ) -> float:
        """
        Calculate delay before next request to this domain.

        Returns delay in seconds.
        """
        state = self.get_domain_state(domain)

        # Base delay for resource type
        min_d, max_d = self.DEFAULT_DELAYS.get(
            resource_type, (self._min_delay, self._max_delay)
        )

        # Scale up if too many fast requests
        if state.consecutive_fast_requests > 3:
            min_d *= 2
            max_d *= 2

        # Scale up if rate limited
        if state.is_rate_limited and not state.is_cooled_down:
            remaining = state.rate_limit_until - time.time()
            return max(remaining, max_d / 1000)

        # Calculate with jitter
        delay_ms = random.uniform(min_d, max_d)

        # Add global rate limit check
        if len(self._global_request_times) >= self._max_rpm:
            oldest = self._global_request_times[0]
            elapsed = time.time() - oldest
            if elapsed < 60:
                # Too many requests in last minute
                backoff = (60 - elapsed) / self._max_rpm
                delay_ms = max(delay_ms, backoff * 1000)

        return delay_ms / 1000.0

    def record_request(
        self,
        domain: str,
        latency_ms: float = 0,
        bytes_received: int = 0,
        status_code: int = 200,
    ) -> None:
        """Record a completed request."""
        state = self.get_domain_state(domain)
        state.record_request(latency_ms, bytes_received)
        self._global_request_times.append(time.time())

        if status_code == 429:
            state.is_rate_limited = True
            state.rate_limit_until = time.time() + random.uniform(30, 120)

    def set_cookies(self, domain: str, cookies: Dict[str, str]) -> None:
        """Store cookies for a domain."""
        state = self.get_domain_state(domain)
        state.cookies.update(cookies)

    def get_cookies(self, domain: str) -> Dict[str, str]:
        """Get stored cookies for a domain."""
        state = self.get_domain_state(domain)
        return dict(state.cookies)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "tracked_domains": len(self._domains),
            "domains": {d: s.to_dict() for d, s in self._domains.items()},
            "global_rpm": len(self._global_request_times),
        }


# ═══════════════════════════════════════════════════════════
# Referrer Chain Builder
# ═══════════════════════════════════════════════════════════

class ReferrerSource(Enum):
    """How the user arrived at the page."""
    SEARCH_ENGINE = "search"
    SOCIAL_MEDIA = "social"
    DIRECT = "direct"
    EMAIL = "email"
    INTERNAL = "internal"
    BACKLINK = "backlink"


@dataclass
class NavigationEntry:
    """A single entry in browsing history."""
    url: str
    referrer: str = ""
    timestamp: float = 0
    source: ReferrerSource = ReferrerSource.DIRECT
    title: str = ""
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "referrer": self.referrer,
            "source": self.source.value,
            "timestamp": self.timestamp,
            "title": self.title,
            "duration_ms": self.duration_ms,
        }


class ReferrerChainBuilder:
    """Build realistic navigation referrer chains."""

    @staticmethod
    def build_search_chain(
        target_url: str,
        search_query: str = "",
        search_engine: str = "",
    ) -> List[NavigationEntry]:
        """
        Build: Search Engine → SERP → Target page

        Args:
            target_url: The URL we want to navigate to
            search_query: Search query (auto-generated if empty)
            search_engine: Preferred search engine URL
        """
        if not search_engine:
            search_engine = random.choice(SEARCH_ENGINE_REFERRERS)

        if not search_query:
            # Extract keywords from URL
            domain = _extract_domain(target_url)
            search_query = domain.replace(".", " ").replace("-", " ")

        chain = [
            NavigationEntry(
                url=f"{search_engine}{search_query.replace(' ', '+')}",
                referrer="",
                source=ReferrerSource.DIRECT,
                timestamp=time.time() - random.uniform(5, 30),
                duration_ms=random.randint(3000, 15000),
            ),
            NavigationEntry(
                url=target_url,
                referrer=search_engine,
                source=ReferrerSource.SEARCH_ENGINE,
                timestamp=time.time(),
            ),
        ]
        return chain

    @staticmethod
    def build_social_chain(
        target_url: str,
        platform: str = "",
    ) -> List[NavigationEntry]:
        """Build: Social Media → Target page"""
        if not platform:
            referrer = random.choice(SOCIAL_REFERRERS)
        else:
            referrer = f"https://www.{platform}.com/"

        return [
            NavigationEntry(
                url=target_url,
                referrer=referrer,
                source=ReferrerSource.SOCIAL_MEDIA,
                timestamp=time.time(),
            ),
        ]

    @staticmethod
    def build_direct_chain(target_url: str) -> List[NavigationEntry]:
        """Build: Direct navigation (no referrer)"""
        return [
            NavigationEntry(
                url=target_url,
                referrer="",
                source=ReferrerSource.DIRECT,
                timestamp=time.time(),
            ),
        ]

    @staticmethod
    def build_internal_chain(
        pages: List[str],
        entry_referrer: str = "",
    ) -> List[NavigationEntry]:
        """Build: Page1 → Page2 → Page3 (internal navigation)"""
        chain = []
        prev_url = entry_referrer
        base_time = time.time() - len(pages) * 30

        for i, url in enumerate(pages):
            chain.append(NavigationEntry(
                url=url,
                referrer=prev_url,
                source=ReferrerSource.INTERNAL if i > 0 else ReferrerSource.DIRECT,
                timestamp=base_time + i * random.uniform(10, 60),
                duration_ms=random.randint(5000, 60000),
            ))
            prev_url = url

        return chain

    @staticmethod
    def select_entry_method() -> ReferrerSource:
        """Randomly select how a user arrived at a site."""
        return random.choices(
            [
                ReferrerSource.SEARCH_ENGINE,
                ReferrerSource.DIRECT,
                ReferrerSource.SOCIAL_MEDIA,
                ReferrerSource.EMAIL,
                ReferrerSource.BACKLINK,
            ],
            weights=[0.45, 0.25, 0.15, 0.08, 0.07],
            k=1,
        )[0]


# ═══════════════════════════════════════════════════════════
# Asset Loading Simulator
# ═══════════════════════════════════════════════════════════

@dataclass
class AssetRequest:
    """A simulated asset request."""
    url: str
    resource_type: ResourceType
    priority: RequestPriority
    referrer: str = ""
    delay_ms: float = 0
    initiator: str = ""  # "parser", "script", "preload"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "type": self.resource_type.value,
            "priority": self.priority.value,
            "delay_ms": self.delay_ms,
            "initiator": self.initiator,
        }


class AssetLoadSimulator:
    """
    Simulate realistic browser asset loading patterns.

    Real browsers load resources in a specific order with specific timing.
    This creates a realistic loading sequence.
    """

    # Typical asset counts per page type
    PAGE_ASSET_PROFILES: Dict[str, Dict[ResourceType, Tuple[int, int]]] = {
        "landing_page": {
            ResourceType.STYLESHEET: (2, 5),
            ResourceType.SCRIPT: (5, 15),
            ResourceType.FONT: (2, 5),
            ResourceType.IMAGE: (10, 30),
            ResourceType.XHR: (3, 10),
        },
        "article": {
            ResourceType.STYLESHEET: (2, 4),
            ResourceType.SCRIPT: (4, 12),
            ResourceType.FONT: (1, 4),
            ResourceType.IMAGE: (3, 15),
            ResourceType.XHR: (2, 8),
        },
        "spa": {
            ResourceType.STYLESHEET: (1, 3),
            ResourceType.SCRIPT: (8, 25),
            ResourceType.FONT: (1, 3),
            ResourceType.IMAGE: (5, 20),
            ResourceType.XHR: (10, 30),
        },
        "e_commerce": {
            ResourceType.STYLESHEET: (3, 6),
            ResourceType.SCRIPT: (8, 20),
            ResourceType.FONT: (2, 5),
            ResourceType.IMAGE: (20, 50),
            ResourceType.XHR: (5, 15),
        },
    }

    @classmethod
    def generate_loading_sequence(
        cls,
        page_url: str,
        page_type: str = "landing_page",
        domain: str = "",
    ) -> List[AssetRequest]:
        """Generate a realistic page load asset sequence."""
        if not domain:
            domain = _extract_domain(page_url)

        profile = cls.PAGE_ASSET_PROFILES.get(
            page_type, cls.PAGE_ASSET_PROFILES["landing_page"]
        )

        assets: List[AssetRequest] = []

        # 1. Main document (always first)
        assets.append(AssetRequest(
            url=page_url,
            resource_type=ResourceType.DOCUMENT,
            priority=RequestPriority.HIGHEST,
            delay_ms=0,
            initiator="navigation",
        ))

        # 2. Generate assets in browser order
        cumulative_delay = random.uniform(50, 200)  # Initial parse time

        for res_type, (min_count, max_count) in sorted(
            profile.items(),
            key=lambda x: RESOURCE_LOAD_ORDER.get(x[0], (99, RequestPriority.LOWEST))[0],
        ):
            count = random.randint(min_count, max_count)
            order, priority = RESOURCE_LOAD_ORDER.get(
                res_type, (99, RequestPriority.LOW)
            )

            for i in range(count):
                # Simulate staggered loading
                delay = cumulative_delay + random.uniform(10, 200)

                ext = _resource_extension(res_type)
                asset_url = f"https://{domain}/assets/{res_type.value}/{_random_hash()[:8]}{ext}"

                # Some assets come from CDNs
                if random.random() < 0.3:
                    cdn = random.choice(["cdn.example.com", "static.example.com",
                                         "assets.cloudflare.com", "cdnjs.cloudflare.com"])
                    asset_url = f"https://{cdn}/{res_type.value}/{_random_hash()[:8]}{ext}"

                initiator = "parser" if res_type in (
                    ResourceType.STYLESHEET, ResourceType.SCRIPT
                ) else "script"

                assets.append(AssetRequest(
                    url=asset_url,
                    resource_type=res_type,
                    priority=priority,
                    referrer=page_url,
                    delay_ms=delay,
                    initiator=initiator,
                ))

            cumulative_delay += random.uniform(50, 300)

        return assets

    @classmethod
    def generate_xhr_sequence(
        cls,
        base_url: str,
        endpoints: Optional[List[str]] = None,
        count: int = 0,
    ) -> List[AssetRequest]:
        """Generate realistic XHR/API request sequence."""
        if not endpoints:
            endpoints = [
                "/api/v1/user/profile",
                "/api/v1/analytics/track",
                "/api/v1/config",
                "/api/v1/notifications",
                "/api/v1/recommendations",
            ]

        if count == 0:
            count = random.randint(2, min(8, len(endpoints)))

        selected = random.sample(endpoints, min(count, len(endpoints)))
        requests = []
        cumulative = random.uniform(500, 2000)

        for endpoint in selected:
            requests.append(AssetRequest(
                url=f"{base_url.rstrip('/')}{endpoint}",
                resource_type=ResourceType.XHR,
                priority=RequestPriority.MEDIUM,
                referrer=base_url,
                delay_ms=cumulative,
                initiator="script",
            ))
            cumulative += random.uniform(200, 3000)

        return requests


# ═══════════════════════════════════════════════════════════
# Cookie Accumulator
# ═══════════════════════════════════════════════════════════

@dataclass
class CookieProfile:
    """Represents accumulated cookies across browsing sessions."""
    cookies: Dict[str, Dict[str, str]] = field(default_factory=dict)  # domain → {name: value}
    first_visit: Dict[str, float] = field(default_factory=dict)       # domain → timestamp
    visit_count: Dict[str, int] = field(default_factory=dict)         # domain → count

    def add_cookies(self, domain: str, cookies: Dict[str, str]) -> None:
        if domain not in self.cookies:
            self.cookies[domain] = {}
            self.first_visit[domain] = time.time()
            self.visit_count[domain] = 0
        self.cookies[domain].update(cookies)
        self.visit_count[domain] += 1

    def get_cookies(self, domain: str) -> Dict[str, str]:
        return dict(self.cookies.get(domain, {}))

    def has_visited(self, domain: str) -> bool:
        return domain in self.cookies

    @property
    def total_domains(self) -> int:
        return len(self.cookies)

    @property
    def total_cookies(self) -> int:
        return sum(len(c) for c in self.cookies.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_domains": self.total_domains,
            "total_cookies": self.total_cookies,
            "domains": {d: len(c) for d, c in self.cookies.items()},
        }


class CookieAccumulator:
    """
    Simulate natural cookie accumulation over browsing sessions.

    New users have few cookies; returning users have many.
    """

    # Common tracking cookies that most users have
    COMMON_COOKIES: Dict[str, Dict[str, str]] = {
        ".google.com": {
            "NID": lambda: _random_hash()[:50],
            "1P_JAR": lambda: time.strftime("%Y-%m-%d-%H"),
        },
        ".facebook.com": {
            "fr": lambda: _random_hash()[:20],
        },
        ".doubleclick.net": {
            "IDE": lambda: _random_hash()[:30],
        },
    }

    @classmethod
    def generate_new_user_cookies(cls) -> CookieProfile:
        """Generate minimal cookies for a new user."""
        profile = CookieProfile()
        # New users typically have 0-2 tracking cookies
        if random.random() < 0.3:
            profile.add_cookies(".google.com", {"NID": _random_hash()[:50]})
        return profile

    @classmethod
    def generate_returning_user_cookies(
        cls,
        domains_visited: int = 10,
    ) -> CookieProfile:
        """Generate cookies for a returning user."""
        profile = CookieProfile()

        # Common tracking cookies
        for domain, cookie_gen in cls.COMMON_COOKIES.items():
            if random.random() < 0.7:
                cookies = {}
                for name, gen_fn in cookie_gen.items():
                    cookies[name] = gen_fn() if callable(gen_fn) else gen_fn
                profile.add_cookies(domain, cookies)

        # Session cookies from recent visits
        for _ in range(min(domains_visited, 20)):
            domain = f".site{random.randint(1, 100)}.com"
            cookies = {
                "_session": _random_hash()[:32],
            }
            if random.random() < 0.5:
                cookies["_ga"] = f"GA1.2.{random.randint(100000, 999999)}.{int(time.time())}"
            profile.add_cookies(domain, cookies)

        return profile


# ═══════════════════════════════════════════════════════════
# Navigation History Simulator
# ═══════════════════════════════════════════════════════════

class NavigationHistory:
    """
    Maintain a realistic browser navigation history.
    Handles back/forward navigation patterns.
    """

    def __init__(self, max_entries: int = 50) -> None:
        self._entries: List[NavigationEntry] = []
        self._current_index: int = -1
        self._max_entries = max_entries

    def navigate(self, entry: NavigationEntry) -> None:
        """Navigate to a new page (clears forward history)."""
        self._current_index += 1
        # Clear forward history
        self._entries = self._entries[:self._current_index]
        self._entries.append(entry)

        # Trim if too long
        if len(self._entries) > self._max_entries:
            overflow = len(self._entries) - self._max_entries
            self._entries = self._entries[overflow:]
            self._current_index -= overflow

    def can_go_back(self) -> bool:
        return self._current_index > 0

    def can_go_forward(self) -> bool:
        return self._current_index < len(self._entries) - 1

    def go_back(self) -> Optional[NavigationEntry]:
        if not self.can_go_back():
            return None
        self._current_index -= 1
        return self._entries[self._current_index]

    def go_forward(self) -> Optional[NavigationEntry]:
        if not self.can_go_forward():
            return None
        self._current_index += 1
        return self._entries[self._current_index]

    @property
    def current(self) -> Optional[NavigationEntry]:
        if 0 <= self._current_index < len(self._entries):
            return self._entries[self._current_index]
        return None

    @property
    def length(self) -> int:
        return len(self._entries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "length": self.length,
            "current_index": self._current_index,
            "current_url": self.current.url if self.current else None,
            "can_back": self.can_go_back(),
            "can_forward": self.can_go_forward(),
        }


# ═══════════════════════════════════════════════════════════
# Retry Engine with Fingerprint Rotation
# ═══════════════════════════════════════════════════════════

@dataclass
class RetryConfig:
    """Configuration for the retry engine."""
    max_retries: int = 3
    base_delay_seconds: float = 2.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.3
    rotate_fingerprint: bool = True
    rotate_proxy: bool = True
    retry_on_status: List[int] = field(default_factory=lambda: [429, 503, 502, 500])


class RetryEngine:
    """
    Retry failed requests with fingerprint and proxy rotation.
    Each retry looks like a different user.
    """

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        self._config = config or RetryConfig()
        self._retry_count: Dict[str, int] = {}  # url → retries
        self._total_retries = 0

    def should_retry(self, url: str, status_code: int) -> bool:
        """Check if we should retry this request."""
        retries = self._retry_count.get(url, 0)
        if retries >= self._config.max_retries:
            return False
        return status_code in self._config.retry_on_status

    def get_retry_delay(self, url: str) -> float:
        """Calculate delay before next retry (exponential backoff + jitter)."""
        retries = self._retry_count.get(url, 0)
        delay = self._config.base_delay_seconds * (
            self._config.exponential_base ** retries
        )
        delay = min(delay, self._config.max_delay_seconds)

        # Add jitter
        jitter = delay * self._config.jitter
        delay += random.uniform(-jitter, jitter)

        return max(0.5, delay)

    def record_retry(self, url: str) -> int:
        """Record a retry attempt. Returns current retry count."""
        self._retry_count[url] = self._retry_count.get(url, 0) + 1
        self._total_retries += 1
        return self._retry_count[url]

    def reset(self, url: Optional[str] = None) -> None:
        """Reset retry counter."""
        if url:
            self._retry_count.pop(url, None)
        else:
            self._retry_count.clear()

    def get_retry_strategy(self, url: str) -> Dict[str, Any]:
        """Get the retry strategy for next attempt."""
        retries = self._retry_count.get(url, 0)
        return {
            "attempt": retries + 1,
            "delay_seconds": self.get_retry_delay(url),
            "rotate_fingerprint": self._config.rotate_fingerprint and retries > 0,
            "rotate_proxy": self._config.rotate_proxy and retries > 1,
            "remaining_retries": max(0, self._config.max_retries - retries),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_retries": self._total_retries,
            "urls_tracked": len(self._retry_count),
            "config": {
                "max_retries": self._config.max_retries,
                "rotate_fingerprint": self._config.rotate_fingerprint,
                "rotate_proxy": self._config.rotate_proxy,
            },
        }


# ═══════════════════════════════════════════════════════════
# Request Pipeline Engine
# ═══════════════════════════════════════════════════════════

class RequestPipeline:
    """
    Main request orchestration engine.

    Combines all sub-systems to create realistic HTTP request patterns.

    Usage:
        pipeline = RequestPipeline()
        chain = pipeline.build_referrer_chain(url, source="search")
        assets = pipeline.generate_page_load(url, "e_commerce")
        delay = pipeline.get_delay("example.com")
    """

    VERSION = "29.0.0"

    def __init__(
        self,
        max_rpm: int = 30,
        cookie_profile: Optional[CookieProfile] = None,
    ) -> None:
        self._rate_limiter = DomainRateLimiter(max_requests_per_minute=max_rpm)
        self._referrer_builder = ReferrerChainBuilder()
        self._asset_simulator = AssetLoadSimulator()
        self._retry_engine = RetryEngine()
        self._history = NavigationHistory()
        self._cookie_profile = cookie_profile or CookieAccumulator.generate_new_user_cookies()
        self._requests_total = 0

    def build_referrer_chain(
        self,
        target_url: str,
        source: str = "auto",
        search_query: str = "",
    ) -> List[NavigationEntry]:
        """
        Build a referrer chain to a target URL.

        Args:
            target_url: Destination URL
            source: "search", "social", "direct", "auto"
            search_query: Optional search query for search referrer
        """
        if source == "auto":
            src = ReferrerChainBuilder.select_entry_method()
        else:
            src = ReferrerSource(source) if source in [s.value for s in ReferrerSource] else ReferrerSource.DIRECT

        if src == ReferrerSource.SEARCH_ENGINE:
            chain = ReferrerChainBuilder.build_search_chain(target_url, search_query)
        elif src == ReferrerSource.SOCIAL_MEDIA:
            chain = ReferrerChainBuilder.build_social_chain(target_url)
        else:
            chain = ReferrerChainBuilder.build_direct_chain(target_url)

        # Record in history
        for entry in chain:
            self._history.navigate(entry)

        return chain

    def generate_page_load(
        self,
        page_url: str,
        page_type: str = "landing_page",
    ) -> List[AssetRequest]:
        """Generate realistic page load asset sequence."""
        return AssetLoadSimulator.generate_loading_sequence(page_url, page_type)

    def get_delay(
        self,
        domain: str,
        resource_type: ResourceType = ResourceType.DOCUMENT,
    ) -> float:
        """Get delay before next request to domain (seconds)."""
        return self._rate_limiter.calculate_delay(domain, resource_type)

    def record_request(
        self,
        domain: str,
        latency_ms: float = 0,
        status_code: int = 200,
        cookies: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a completed request."""
        self._rate_limiter.record_request(domain, latency_ms, status_code=status_code)
        self._requests_total += 1
        if cookies:
            self._cookie_profile.add_cookies(f".{domain}", cookies)

    def should_retry(self, url: str, status_code: int) -> bool:
        """Check if request should be retried."""
        return self._retry_engine.should_retry(url, status_code)

    def get_retry_strategy(self, url: str) -> Dict[str, Any]:
        """Get retry strategy for a failed request."""
        return self._retry_engine.get_retry_strategy(url)

    @property
    def history(self) -> NavigationHistory:
        return self._history

    @property
    def cookies(self) -> CookieProfile:
        return self._cookie_profile

    def get_stats(self) -> Dict[str, Any]:
        return {
            "version": self.VERSION,
            "total_requests": self._requests_total,
            "rate_limiter": self._rate_limiter.get_stats(),
            "retry": self._retry_engine.get_stats(),
            "history": self._history.to_dict(),
            "cookies": self._cookie_profile.to_dict(),
        }


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split("/")[0]
    except Exception:
        return url.split("//")[-1].split("/")[0]


def _random_hash() -> str:
    """Generate a random hex hash."""
    return hashlib.md5(str(random.random()).encode()).hexdigest()


def _resource_extension(res_type: ResourceType) -> str:
    """Get typical file extension for resource type."""
    return {
        ResourceType.STYLESHEET: ".css",
        ResourceType.SCRIPT: ".js",
        ResourceType.FONT: ".woff2",
        ResourceType.IMAGE: random.choice([".png", ".jpg", ".webp", ".svg"]),
        ResourceType.MEDIA: random.choice([".mp4", ".webm"]),
        ResourceType.MANIFEST: ".json",
    }.get(res_type, "")


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

request_pipeline: RequestPipeline = RequestPipeline()


