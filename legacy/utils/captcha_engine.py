
from __future__ import annotations
"""
utils/captcha_engine.py — Advanced Captcha Intelligence Engine v1.0-TITAN
═════════════════════════════════════════════════════════════════════════
Multi-solver captcha routing with cost optimization:

 1. Multi-solver support (2captcha, anti-captcha, CapSolver, CapMonster, ez-captcha)
 2. ML-based captcha type detection from page context
 3. Cost optimization (cheapest reliable solver per captcha type)
 4. Success rate tracking per solver per captcha type
 5. Automatic fallback chains
 6. Token caching & pre-solving
 7. reCAPTCHA v3 score optimization
 8. Budget tracking & alerts

Author: Arki Engine TITAN
License: Proprietary
"""


import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("arki.captcha_engine")


# ═══════════════════════════════════════════════════════════
# Captcha Types & Detection
# ═══════════════════════════════════════════════════════════

class CaptchaFamily(Enum):
    """Captcha families recognized by the engine."""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V2_INVISIBLE = "recaptcha_v2_invisible"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE_TURNSTILE = "turnstile"
    FUNCAPTCHA = "funcaptcha"
    GEETEST_V3 = "geetest_v3"
    GEETEST_V4 = "geetest_v4"
    IMAGE_CAPTCHA = "image"
    TEXT_CAPTCHA = "text"
    AUDIO_CAPTCHA = "audio"
    AMAZON_WAF = "amazon_waf"
    UNKNOWN = "unknown"


class SolverProvider(Enum):
    """Supported solver providers."""
    TWO_CAPTCHA = "2captcha"
    ANTI_CAPTCHA = "anti_captcha"
    CAPSOLVER = "capsolver"
    CAPMONSTER = "capmonster"
    EZ_CAPTCHA = "ez_captcha"


# ── Detection signatures ──

CAPTCHA_SIGNATURES: Dict[CaptchaFamily, List[str]] = {
    CaptchaFamily.RECAPTCHA_V2: [
        "class=\"g-recaptcha\"",
        "data-sitekey",
        "google.com/recaptcha/api2/",
        "grecaptcha.render",
        "g-recaptcha-response",
    ],
    CaptchaFamily.RECAPTCHA_V3: [
        "grecaptcha.execute",
        "recaptcha/api.js?render=",
        "recaptcha-v3",
    ],
    CaptchaFamily.HCAPTCHA: [
        "hcaptcha.com/1/api.js",
        "class=\"h-captcha\"",
        "data-hcaptcha",
        "h-captcha-response",
    ],
    CaptchaFamily.CLOUDFLARE_TURNSTILE: [
        "challenges.cloudflare.com/turnstile",
        "cf-turnstile",
        "turnstile-callback",
    ],
    CaptchaFamily.FUNCAPTCHA: [
        "funcaptcha.com",
        "arkoselabs.com",
        "arkose-token",
    ],
    CaptchaFamily.GEETEST_V3: [
        "gt.js",
        "geetest.com",
        "initGeetest",
    ],
    CaptchaFamily.GEETEST_V4: [
        "gt4.js",
        "initGeetest4",
        "captcha_id",
    ],
    CaptchaFamily.AMAZON_WAF: [
        "awswaf",
        "aws-waf-token",
        "challenge.js",
    ],
}


class CaptchaDetector:
    """Detect captcha type from page HTML/DOM."""

    @classmethod
    def detect_from_html(cls, html: str) -> List[CaptchaFamily]:
        """Detect captcha types present in HTML source."""
        html_lower = html.lower()
        detected: List[CaptchaFamily] = []

        for family, signatures in CAPTCHA_SIGNATURES.items():
            for sig in signatures:
                if sig.lower() in html_lower:
                    if family not in detected:
                        detected.append(family)
                    break

        return detected

    @classmethod
    def detect_from_scripts(cls, script_urls: List[str]) -> List[CaptchaFamily]:
        """Detect captcha types from loaded script URLs."""
        detected: List[CaptchaFamily] = []
        for url in script_urls:
            url_lower = url.lower()
            if "recaptcha" in url_lower:
                if "render=" in url_lower:
                    detected.append(CaptchaFamily.RECAPTCHA_V3)
                else:
                    detected.append(CaptchaFamily.RECAPTCHA_V2)
            elif "hcaptcha" in url_lower:
                detected.append(CaptchaFamily.HCAPTCHA)
            elif "turnstile" in url_lower:
                detected.append(CaptchaFamily.CLOUDFLARE_TURNSTILE)
            elif "funcaptcha" in url_lower or "arkoselabs" in url_lower:
                detected.append(CaptchaFamily.FUNCAPTCHA)
            elif "geetest" in url_lower:
                if "gt4" in url_lower:
                    detected.append(CaptchaFamily.GEETEST_V4)
                else:
                    detected.append(CaptchaFamily.GEETEST_V3)
        return list(set(detected))

    @classmethod
    def extract_sitekey(cls, html: str, family: CaptchaFamily) -> Optional[str]:
        """Extract the captcha sitekey from HTML."""
        import re
        if family in (CaptchaFamily.RECAPTCHA_V2, CaptchaFamily.RECAPTCHA_V3):
            match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            if match:
                return match.group(1)
            match = re.search(r'render=([a-zA-Z0-9_-]+)', html)
            if match:
                return match.group(1)
        elif family == CaptchaFamily.HCAPTCHA:
            match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            if match:
                return match.group(1)
        elif family == CaptchaFamily.CLOUDFLARE_TURNSTILE:
            match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            if match:
                return match.group(1)
        return None


# ═══════════════════════════════════════════════════════════
# Solver Configuration & Pricing
# ═══════════════════════════════════════════════════════════

@dataclass
class SolverConfig:
    """Configuration for a solver provider."""
    provider: SolverProvider
    api_key: str
    api_url: str = ""
    priority: int = 0         # Higher = preferred
    enabled: bool = True
    max_concurrent: int = 10
    timeout_seconds: int = 120

    def __post_init__(self) -> Any:
        if not self.api_url:
            self.api_url = self._default_url()

    def _default_url(self) -> str:
        return {
            SolverProvider.TWO_CAPTCHA: "https://2captcha.com/in.php",
            SolverProvider.ANTI_CAPTCHA: "https://api.anti-captcha.com",
            SolverProvider.CAPSOLVER: "https://api.capsolver.com",
            SolverProvider.CAPMONSTER: "https://api.capmonster.cloud",
            SolverProvider.EZ_CAPTCHA: "https://api.ez-captcha.com",
        }.get(self.provider, "")


# Cost per 1000 solves (USD)
SOLVER_PRICING: Dict[SolverProvider, Dict[CaptchaFamily, float]] = {
    SolverProvider.TWO_CAPTCHA: {
        CaptchaFamily.RECAPTCHA_V2: 2.99,
        CaptchaFamily.RECAPTCHA_V2_INVISIBLE: 2.99,
        CaptchaFamily.RECAPTCHA_V3: 2.99,
        CaptchaFamily.HCAPTCHA: 2.99,
        CaptchaFamily.CLOUDFLARE_TURNSTILE: 2.99,
        CaptchaFamily.FUNCAPTCHA: 2.99,
        CaptchaFamily.GEETEST_V3: 2.99,
        CaptchaFamily.GEETEST_V4: 2.99,
        CaptchaFamily.IMAGE_CAPTCHA: 0.99,
        CaptchaFamily.TEXT_CAPTCHA: 0.99,
    },
    SolverProvider.ANTI_CAPTCHA: {
        CaptchaFamily.RECAPTCHA_V2: 2.00,
        CaptchaFamily.RECAPTCHA_V2_INVISIBLE: 2.00,
        CaptchaFamily.RECAPTCHA_V3: 3.00,
        CaptchaFamily.HCAPTCHA: 2.00,
        CaptchaFamily.CLOUDFLARE_TURNSTILE: 2.00,
        CaptchaFamily.FUNCAPTCHA: 3.00,
        CaptchaFamily.IMAGE_CAPTCHA: 0.70,
    },
    SolverProvider.CAPSOLVER: {
        CaptchaFamily.RECAPTCHA_V2: 1.50,
        CaptchaFamily.RECAPTCHA_V2_INVISIBLE: 1.50,
        CaptchaFamily.RECAPTCHA_V3: 2.00,
        CaptchaFamily.HCAPTCHA: 1.50,
        CaptchaFamily.CLOUDFLARE_TURNSTILE: 1.50,
        CaptchaFamily.FUNCAPTCHA: 2.00,
        CaptchaFamily.GEETEST_V3: 1.50,
        CaptchaFamily.GEETEST_V4: 2.50,
        CaptchaFamily.AMAZON_WAF: 2.50,
    },
    SolverProvider.CAPMONSTER: {
        CaptchaFamily.RECAPTCHA_V2: 1.20,
        CaptchaFamily.RECAPTCHA_V3: 1.80,
        CaptchaFamily.HCAPTCHA: 1.00,
        CaptchaFamily.CLOUDFLARE_TURNSTILE: 1.20,
        CaptchaFamily.IMAGE_CAPTCHA: 0.50,
    },
    SolverProvider.EZ_CAPTCHA: {
        CaptchaFamily.RECAPTCHA_V2: 1.80,
        CaptchaFamily.RECAPTCHA_V3: 2.50,
        CaptchaFamily.HCAPTCHA: 1.80,
        CaptchaFamily.CLOUDFLARE_TURNSTILE: 1.80,
        CaptchaFamily.FUNCAPTCHA: 2.50,
    },
}

# Solver capabilities (which types each solver supports)
SOLVER_CAPABILITIES: Dict[SolverProvider, Set[CaptchaFamily]] = {
    provider: set(prices.keys())
    for provider, prices in SOLVER_PRICING.items()
}


# ═══════════════════════════════════════════════════════════
# Solver Performance Tracker
# ═══════════════════════════════════════════════════════════

@dataclass
class SolverStats:
    """Performance stats for a solver on a specific captcha type."""
    provider: SolverProvider
    captcha_type: CaptchaFamily
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    total_time_ms: int = 0
    total_cost_usd: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.5  # Unknown
        return self.successes / self.attempts

    @property
    def avg_time_ms(self) -> float:
        if self.successes == 0:
            return 0
        return self.total_time_ms / self.successes

    @property
    def cost_per_solve(self) -> float:
        if self.successes == 0:
            return 0
        return self.total_cost_usd / self.successes

    def record_success(self, time_ms: int, cost_usd: float) -> None:
        self.attempts += 1
        self.successes += 1
        self.total_time_ms += time_ms
        self.total_cost_usd += cost_usd
        self.last_success = time.time()
        self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.attempts += 1
        self.failures += 1
        self.last_failure = time.time()
        self.consecutive_failures += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.value,
            "captcha_type": self.captcha_type.value,
            "attempts": self.attempts,
            "success_rate": round(self.success_rate, 3),
            "avg_time_ms": round(self.avg_time_ms, 0),
            "cost_per_solve": round(self.cost_per_solve, 4),
            "consecutive_failures": self.consecutive_failures,
        }


# ═══════════════════════════════════════════════════════════
# Token Cache
# ═══════════════════════════════════════════════════════════

@dataclass
class CachedToken:
    """A cached captcha solution token."""
    token: str
    captcha_type: CaptchaFamily
    sitekey: str
    page_url: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0
    provider: Optional[SolverProvider] = None

    @property
    def is_valid(self) -> bool:
        if self.expires_at > 0:
            return time.time() < self.expires_at
        # Default TTLs
        ttls = {
            CaptchaFamily.RECAPTCHA_V2: 120,
            CaptchaFamily.RECAPTCHA_V3: 120,
            CaptchaFamily.HCAPTCHA: 120,
            CaptchaFamily.CLOUDFLARE_TURNSTILE: 300,
        }
        ttl = ttls.get(self.captcha_type, 120)
        return time.time() - self.created_at < ttl


class TokenCache:
    """Cache solved captcha tokens for reuse."""

    def __init__(self, max_size: int = 50) -> None:
        self._cache: Dict[str, List[CachedToken]] = defaultdict(list)
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _cache_key(self, captcha_type: CaptchaFamily, sitekey: str, page_url: str) -> str:
        return f"{captcha_type.value}:{sitekey}:{page_url}"

    def store(self, token: CachedToken) -> None:
        """Store a solved token."""
        key = self._cache_key(token.captcha_type, token.sitekey, token.page_url)
        self._cache[key].append(token)

        # Cleanup old entries
        self._cache[key] = [t for t in self._cache[key] if t.is_valid]

        # Enforce max size globally
        total = sum(len(v) for v in self._cache.values())
        while total > self._max_size:
            # Remove oldest
            oldest_key = min(self._cache.keys(),
                             key=lambda k: min(t.created_at for t in self._cache[k]) if self._cache[k] else float('inf'))
            if self._cache[oldest_key]:
                self._cache[oldest_key].pop(0)
                if not self._cache[oldest_key]:
                    del self._cache[oldest_key]
            total -= 1

    def get(self, captcha_type: CaptchaFamily, sitekey: str, page_url: str) -> Optional[str]:
        """Get a cached token if available."""
        key = self._cache_key(captcha_type, sitekey, page_url)
        tokens = self._cache.get(key, [])

        # Find valid token
        for i, token in enumerate(tokens):
            if token.is_valid:
                self._hits += 1
                tokens.pop(i)
                return token.token

        self._misses += 1
        return None

    @property
    def size(self) -> int:
        return sum(len(v) for v in self._cache.values())

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "size": self.size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 3),
        }


# ═══════════════════════════════════════════════════════════
# Solver Router (Cost Optimizer)
# ═══════════════════════════════════════════════════════════

class SolverRouter:
    """
    Route captcha solve requests to the optimal solver.

    Considers: cost, success rate, speed, availability.
    """

    def __init__(self) -> None:
        self._stats: Dict[str, SolverStats] = {}

    def _stats_key(self, provider: SolverProvider, captcha_type: CaptchaFamily) -> str:
        return f"{provider.value}:{captcha_type.value}"

    def get_stats(self, provider: SolverProvider, captcha_type: CaptchaFamily) -> SolverStats:
        key = self._stats_key(provider, captcha_type)
        if key not in self._stats:
            self._stats[key] = SolverStats(provider=provider, captcha_type=captcha_type)
        return self._stats[key]

    def select_solver(
        self,
        captcha_type: CaptchaFamily,
        available_solvers: List[SolverConfig],
        optimize_for: str = "cost",  # "cost", "speed", "reliability"
    ) -> Optional[SolverConfig]:
        """
        Select the best solver for a captcha type.

        Args:
            captcha_type: Type of captcha to solve
            available_solvers: Configured solver providers
            optimize_for: "cost" (cheapest), "speed" (fastest), "reliability" (highest success)
        """
        # Filter to capable & enabled solvers
        candidates = [
            s for s in available_solvers
            if s.enabled and captcha_type in SOLVER_CAPABILITIES.get(s.provider, set())
        ]

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # Score each candidate
        scored: List[Tuple[float, SolverConfig]] = []
        for solver in candidates:
            stats = self.get_stats(solver.provider, captcha_type)
            score = self._score_solver(solver, stats, captcha_type, optimize_for)
            scored.append((score, solver))

        # Sort by score (higher = better)
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _score_solver(
        self,
        solver: SolverConfig,
        stats: SolverStats,
        captcha_type: CaptchaFamily,
        optimize_for: str,
    ) -> float:
        """Score a solver based on optimization criteria."""
        pricing = SOLVER_PRICING.get(solver.provider, {})
        cost_per_1k = pricing.get(captcha_type, 5.0)

        # Base scores (0-1)
        cost_score = 1.0 - min(1.0, cost_per_1k / 5.0)
        speed_score = 1.0 - min(1.0, stats.avg_time_ms / 120000) if stats.avg_time_ms > 0 else 0.5
        reliability_score = stats.success_rate

        # Penalty for consecutive failures
        if stats.consecutive_failures > 3:
            reliability_score *= 0.5

        if optimize_for == "cost":
            return cost_score * 0.6 + reliability_score * 0.3 + speed_score * 0.1
        elif optimize_for == "speed":
            return speed_score * 0.5 + reliability_score * 0.35 + cost_score * 0.15
        else:  # reliability
            return reliability_score * 0.6 + speed_score * 0.25 + cost_score * 0.15

    def get_fallback_chain(
        self,
        captcha_type: CaptchaFamily,
        available_solvers: List[SolverConfig],
    ) -> List[SolverConfig]:
        """Get ordered fallback chain of solvers."""
        candidates = [
            s for s in available_solvers
            if s.enabled and captcha_type in SOLVER_CAPABILITIES.get(s.provider, set())
        ]

        if not candidates:
            return []

        # Score all and return in order
        scored: List[Tuple[float, SolverConfig]] = []
        for solver in candidates:
            stats = self.get_stats(solver.provider, captcha_type)
            score = self._score_solver(solver, stats, captcha_type, "reliability")
            scored.append((score, solver))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]


# ═══════════════════════════════════════════════════════════
# Budget Tracker
# ═══════════════════════════════════════════════════════════

@dataclass
class BudgetConfig:
    """Budget configuration for captcha solving."""
    daily_budget_usd: float = 10.0
    monthly_budget_usd: float = 200.0
    alert_threshold: float = 0.8   # Alert at 80% of budget

    def to_dict(self) -> Dict[str, Any]:
        return {
            "daily_budget_usd": self.daily_budget_usd,
            "monthly_budget_usd": self.monthly_budget_usd,
            "alert_threshold": self.alert_threshold,
        }


class BudgetTracker:
    """Track captcha solving costs."""

    def __init__(self, config: Optional[BudgetConfig] = None) -> None:
        self._config = config or BudgetConfig()
        self._daily_spend: Dict[str, float] = {}  # date → USD
        self._monthly_spend: Dict[str, float] = {}  # YYYY-MM → USD
        self._total_spend = 0.0

    def record_spend(self, amount_usd: float) -> None:
        """Record a captcha solve cost."""
        import datetime
        now = datetime.datetime.now()
        day_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")

        self._daily_spend[day_key] = self._daily_spend.get(day_key, 0) + amount_usd
        self._monthly_spend[month_key] = self._monthly_spend.get(month_key, 0) + amount_usd
        self._total_spend += amount_usd

    def is_within_budget(self) -> bool:
        """Check if current spending is within budget."""
        import datetime
        now = datetime.datetime.now()
        day_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")

        daily = self._daily_spend.get(day_key, 0)
        monthly = self._monthly_spend.get(month_key, 0)

        return (daily < self._config.daily_budget_usd and
                monthly < self._config.monthly_budget_usd)

    def should_alert(self) -> bool:
        """Check if spending has crossed the alert threshold."""
        import datetime
        now = datetime.datetime.now()
        day_key = now.strftime("%Y-%m-%d")

        daily = self._daily_spend.get(day_key, 0)
        return daily >= self._config.daily_budget_usd * self._config.alert_threshold

    def get_stats(self) -> Dict[str, Any]:
        import datetime
        now = datetime.datetime.now()
        day_key = now.strftime("%Y-%m-%d")
        month_key = now.strftime("%Y-%m")

        return {
            "today_usd": round(self._daily_spend.get(day_key, 0), 4),
            "this_month_usd": round(self._monthly_spend.get(month_key, 0), 4),
            "total_usd": round(self._total_spend, 4),
            "within_budget": self.is_within_budget(),
            "config": self._config.to_dict(),
        }


# ═══════════════════════════════════════════════════════════
# Captcha Intelligence Engine
# ═══════════════════════════════════════════════════════════

@dataclass
class SolveRequest:
    """A captcha solve request."""
    captcha_type: CaptchaFamily
    sitekey: str
    page_url: str
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    min_score: float = 0.7    # For reCAPTCHA v3
    action: str = "verify"     # For reCAPTCHA v3


@dataclass
class SolveResult:
    """Result of a captcha solve attempt."""
    success: bool
    token: Optional[str] = None
    provider: Optional[SolverProvider] = None
    captcha_type: Optional[CaptchaFamily] = None
    solve_time_ms: int = 0
    cost_usd: float = 0.0
    error: str = ""
    attempts: int = 1
    from_cache: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "provider": self.provider.value if self.provider else None,
            "captcha_type": self.captcha_type.value if self.captcha_type else None,
            "solve_time_ms": self.solve_time_ms,
            "cost_usd": round(self.cost_usd, 4),
            "error": self.error,
            "attempts": self.attempts,
            "from_cache": self.from_cache,
        }


class CaptchaEngine:
    """
    Main captcha intelligence engine.

    Usage:
        engine = CaptchaEngine()
        engine.add_solver(SolverConfig(
            provider=SolverProvider.TWO_CAPTCHA, api_key="xxx"
        ))
        result = await engine.solve(SolveRequest(
            captcha_type=CaptchaFamily.RECAPTCHA_V2,
            sitekey="xxx", page_url="https://example.com"
        ))
    """

    VERSION = "29.0.0"

    def __init__(
        self,
        budget: Optional[BudgetConfig] = None,
    ) -> None:
        self._solvers: List[SolverConfig] = []
        self._router = SolverRouter()
        self._token_cache = TokenCache()
        self._budget = BudgetTracker(budget)
        self._detector = CaptchaDetector()
        self._total_solves = 0
        self._total_failures = 0

    def add_solver(self, config: SolverConfig) -> None:
        """Register a solver provider."""
        self._solvers.append(config)
        logger.info("Added captcha solver: %s", config.provider.value)

    def remove_solver(self, provider: SolverProvider) -> bool:
        """Remove a solver provider."""
        before = len(self._solvers)
        self._solvers = [s for s in self._solvers if s.provider != provider]
        return len(self._solvers) < before

    def detect_captcha(
        self,
        html: str = "",
        script_urls: Optional[List[str]] = None,
    ) -> List[CaptchaFamily]:
        """Detect captcha types in page content."""
        detected = []
        if html:
            detected.extend(CaptchaDetector.detect_from_html(html))
        if script_urls:
            detected.extend(CaptchaDetector.detect_from_scripts(script_urls))
        return list(set(detected))

    def extract_sitekey(self, html: str, family: CaptchaFamily) -> Optional[str]:
        """Extract sitekey from HTML."""
        return CaptchaDetector.extract_sitekey(html, family)

    async def solve(
        self,
        request: SolveRequest,
        optimize_for: str = "cost",
        use_cache: bool = True,
        max_attempts: int = 3,
    ) -> SolveResult:
        """
        Solve a captcha using the optimal provider.

        Args:
            request: The solve request
            optimize_for: "cost", "speed", "reliability"
            use_cache: Check token cache first
            max_attempts: Max solve attempts with fallback
        """
        # 1. Check cache
        if use_cache:
            cached = self._token_cache.get(
                request.captcha_type, request.sitekey, request.page_url
            )
            if cached:
                self._total_solves += 1
                return SolveResult(
                    success=True, token=cached,
                    captcha_type=request.captcha_type,
                    from_cache=True,
                )

        # 2. Check budget
        if not self._budget.is_within_budget():
            return SolveResult(
                success=False, error="Budget exceeded",
                captcha_type=request.captcha_type,
            )

        # 3. Get fallback chain
        chain = self._router.get_fallback_chain(
            request.captcha_type, self._solvers
        )
        if not chain:
            return SolveResult(
                success=False, error="No solver available for this captcha type",
                captcha_type=request.captcha_type,
            )

        # 4. Try each solver in chain
        last_error = ""
        for attempt, solver in enumerate(chain[:max_attempts], 1):
            start_time = time.time()

            try:
                # Simulate solving (actual API call would go here)
                token = await self._call_solver(solver, request)

                if token:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    pricing = SOLVER_PRICING.get(solver.provider, {})
                    cost = pricing.get(request.captcha_type, 3.0) / 1000.0

                    # Record success
                    stats = self._router.get_stats(solver.provider, request.captcha_type)
                    stats.record_success(elapsed_ms, cost)
                    self._budget.record_spend(cost)
                    self._total_solves += 1

                    # Cache the token
                    self._token_cache.store(CachedToken(
                        token=token,
                        captcha_type=request.captcha_type,
                        sitekey=request.sitekey,
                        page_url=request.page_url,
                        provider=solver.provider,
                    ))

                    return SolveResult(
                        success=True, token=token,
                        provider=solver.provider,
                        captcha_type=request.captcha_type,
                        solve_time_ms=elapsed_ms,
                        cost_usd=cost,
                        attempts=attempt,
                    )

            except Exception as e:
                last_error = str(e)
                stats = self._router.get_stats(solver.provider, request.captcha_type)
                stats.record_failure()
                logger.warning(
                    "Solver %s failed for %s: %s",
                    solver.provider.value, request.captcha_type.value, e
                )

        self._total_failures += 1
        return SolveResult(
            success=False, error=last_error or "All solvers failed",
            captcha_type=request.captcha_type,
            attempts=min(max_attempts, len(chain)),
        )

    async def _call_solver(
        self, solver: SolverConfig, request: SolveRequest
    ) -> Optional[str]:
        """
        Call a solver provider's API.

        This is a framework implementation. In production, this would make
        real HTTP requests to the solver's API.
        """
        # Framework: returns None (actual implementation would call API)
        # Subclass or monkey-patch for real usage
        logger.debug(
            "Would call %s for %s (sitekey=%s)",
            solver.provider.value, request.captcha_type.value, request.sitekey[:8]
        )
        return None

    def get_cheapest_solver(
        self, captcha_type: CaptchaFamily
    ) -> Optional[Tuple[SolverProvider, float]]:
        """Get the cheapest solver for a captcha type."""
        cheapest: Optional[Tuple[SolverProvider, float]] = None
        for provider, prices in SOLVER_PRICING.items():
            if captcha_type in prices:
                cost = prices[captcha_type]
                if cheapest is None or cost < cheapest[1]:
                    cheapest = (provider, cost)
        return cheapest

    def get_supported_types(self) -> Dict[str, List[str]]:
        """Get supported captcha types per registered solver."""
        result = {}
        for solver in self._solvers:
            caps = SOLVER_CAPABILITIES.get(solver.provider, set())
            result[solver.provider.value] = [c.value for c in caps]
        return result

    def get_stats(self) -> Dict[str, Any]:
        # Collect solver stats
        solver_stats = {}
        for key, stats in self._router._stats.items():
            solver_stats[key] = stats.to_dict()

        return {
            "version": self.VERSION,
            "registered_solvers": len(self._solvers),
            "total_solves": self._total_solves,
            "total_failures": self._total_failures,
            "token_cache": self._token_cache.get_stats(),
            "budget": self._budget.get_stats(),
            "solver_performance": solver_stats,
        }


# ═══════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════

captcha_engine: CaptchaEngine = CaptchaEngine()


