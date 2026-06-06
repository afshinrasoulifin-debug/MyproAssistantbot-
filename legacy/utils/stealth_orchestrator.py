
from __future__ import annotations
"""
utils/stealth_orchestrator.py — SUPREME Stealth Orchestrator v1.0
═══════════════════════════════════════════════════════════════════
Unifies ALL 13 bypass modules into a single intelligent pipeline.

Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │                  StealthOrchestrator                        │
  │  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
  │  │  Target   │→│ Strategy │→│  Execute   │→│  Verify   │  │
  │  │ Analyzer  │  │ Selector │  │  Pipeline  │  │  Result   │  │
  │  └──────────┘  └──────────┘  └───────────┘  └──────────┘  │
  │       ↕              ↕              ↕              ↕        │
  │  ┌─────────────────────────────────────────────────────┐   │
  │  │  13 Bypass Modules (auto-wired)                     │   │
  │  │  anti_detection · evasion_scripts · tls_fingerprint │   │
  │  │  h2_transport · browser_validator · proxy_pool      │   │
  │  │  browser_profile · session_store · geo_consistency  │   │
  │  │  behavior_engine · request_pipeline                 │   │
  │  │  fingerprint_engine · captcha_engine                │   │
  │  └─────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────┘

Escalation Levels:
  GHOST    → minimal: basic headers + request pipeline
  SHADOW   → medium:  + TLS fingerprint + geo consistency
  PHANTOM  → heavy:   + behavior engine + fingerprint engine + proxy
  SPECTRE  → nuclear: + full browser + captcha solve + evasion scripts

Usage:
  orch = StealthOrchestrator()
  result = await orch.execute("https://target.com/api/data")
  # Auto-selects strategy based on target analysis
"""

import asyncio
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, Final, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── v3.4.1: Enhanced stealth integration ──
try:
    from arki_project.utils.traffic_orchestrator import get_traffic_orchestrator as _get_to
    from arki_project.utils.waf_adaptive import get_waf_engine as _get_waf
    from arki_project.utils.latency_cloaking import get_kinetic_synthesizer as _get_hks
    _V341_STEALTH = True
except ImportError:
    _V341_STEALTH = False


# ═══════════════════════════════════════════════════════════════════
# Enums & Data Structures
# ═══════════════════════════════════════════════════════════════════

class EscalationLevel(IntEnum):
    """Progressive bypass escalation levels."""
    GHOST = 1      # Minimal: headers + request pipeline
    SHADOW = 2     # Medium: + TLS + geo + H2
    PHANTOM = 3    # Heavy: + behavior + fingerprint + proxy
    SPECTRE = 4    # Nuclear: + full browser + captcha + evasion


class TargetDifficulty(Enum):
    """Assessed difficulty of target."""
    OPEN = "open"           # No protection detected
    BASIC = "basic"         # Simple rate limiting
    MODERATE = "moderate"   # WAF + basic fingerprinting
    HARDENED = "hardened"   # Cloudflare/Akamai + captcha
    FORTRESS = "fortress"   # Multi-layer with behavioral analysis


class RequestMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class OperationResult(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    CAPTCHA = "captcha"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TargetProfile:
    """Intelligence about a target domain/URL."""
    url: str
    domain: str = ""
    difficulty: TargetDifficulty = TargetDifficulty.OPEN
    waf_detected: List[str] = field(default_factory=list)
    captcha_types: List[str] = field(default_factory=list)
    rate_limit_detected: bool = False
    rate_limit_window: float = 0.0
    rate_limit_max: int = 0
    tls_strict: bool = False
    h2_required: bool = False
    js_challenge: bool = False
    behavioral_analysis: bool = False
    geo_restrictions: List[str] = field(default_factory=list)
    tech_stack: Dict[str, str] = field(default_factory=dict)
    last_scanned: float = 0.0
    scan_count: int = 0
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    recommended_level: EscalationLevel = EscalationLevel.GHOST
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url, "domain": self.domain,
            "difficulty": self.difficulty.value,
            "waf_detected": self.waf_detected,
            "captcha_types": self.captcha_types,
            "rate_limit_detected": self.rate_limit_detected,
            "tls_strict": self.tls_strict, "h2_required": self.h2_required,
            "js_challenge": self.js_challenge,
            "behavioral_analysis": self.behavioral_analysis,
            "recommended_level": self.recommended_level.name,
            "success_rate": self.success_rate,
            "scan_count": self.scan_count,
            "notes": self.notes,
        }


@dataclass
class StealthRequest:
    """A request to execute through the stealth pipeline."""
    url: str
    method: RequestMethod = RequestMethod.GET
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    json_body: Optional[Dict[str, Any]] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    max_escalation: EscalationLevel = EscalationLevel.SPECTRE
    force_level: Optional[EscalationLevel] = None
    timeout: float = 30.0
    max_retries: int = 3
    follow_redirects: bool = True
    extract_data: Optional[str] = None  # CSS selector or JSONPath
    session_id: Optional[str] = None
    geo_target: Optional[str] = None  # Target country code
    proxy_country: Optional[str] = None
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StealthResponse:
    """Result of a stealth request."""
    success: bool
    status_code: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    json_data: Optional[Dict[str, Any]] = None
    extracted_data: Any = None
    escalation_used: EscalationLevel = EscalationLevel.GHOST
    attempts: int = 0
    total_time: float = 0.0
    result: OperationResult = OperationResult.SUCCESS
    target_profile: Optional[TargetProfile] = None
    session_id: Optional[str] = None
    proxy_used: Optional[str] = None
    fingerprint_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    chain: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success, "status_code": self.status_code,
            "body_length": len(self.body),
            "json_data": self.json_data is not None,
            "escalation_used": self.escalation_used.name,
            "attempts": self.attempts, "total_time": round(self.total_time, 3),
            "result": self.result.value,
            "errors": self.errors,
            "chain_length": len(self.chain),
        }


@dataclass
class BatchResult:
    """Result of a batch stealth operation."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    responses: List[StealthResponse] = field(default_factory=list)
    total_time: float = 0.0
    avg_escalation: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total, "succeeded": self.succeeded,
            "failed": self.failed,
            "success_rate": round(self.succeeded / max(self.total, 1) * 100, 1),
            "total_time": round(self.total_time, 3),
            "avg_escalation": round(self.avg_escalation, 2),
        }


@dataclass
class SessionChain:
    """A chain of related requests using the same session state."""
    session_id: str
    requests: List[StealthRequest] = field(default_factory=list)
    shared_cookies: Dict[str, str] = field(default_factory=dict)
    fingerprint_locked: bool = True
    geo_locked: bool = True
    results: List[StealthResponse] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════
# Target Analyzer — Profiles target difficulty
# ═══════════════════════════════════════════════════════════════════

# Well-known WAF/CDN signatures
_WAF_SIGNATURES: Final[Dict[str, List[str]]] = {
    "cloudflare": ["cf-ray", "cf-cache-status", "__cf_bm", "cf-mitigated", "cloudflare"],
    "akamai": ["akamai", "x-akamai", "ak_bmsc", "bm_sz"],
    "aws_waf": ["x-amzn-requestid", "x-amz-cf-id", "awswaf"],
    "sucuri": ["sucuri", "x-sucuri-id"],
    "imperva": ["incap_ses", "x-iinfo", "imperva"],
    "datadome": ["datadome", "dd_"],
    "perimeterx": ["_pxhd", "_px", "perimeterx"],
    "kasada": ["kasada", "x-kpsdk"],
    "shape": ["shape", "_abck"],
    "f5": ["bigipserver", "f5-", "ts01"],
}

_CAPTCHA_MARKERS: Final[Dict[str, List[str]]] = {
    "recaptcha": ["recaptcha", "g-recaptcha", "grecaptcha"],
    "hcaptcha": ["hcaptcha", "h-captcha"],
    "turnstile": ["cf-turnstile", "challenges.cloudflare.com/turnstile"],
    "funcaptcha": ["funcaptcha", "arkoselabs"],
    "geetest": ["geetest", "gt_"],
}

_BLOCK_INDICATORS: Final[List[str]] = [
    "access denied", "blocked", "forbidden", "rate limit",
    "too many requests", "captcha", "challenge", "bot detected",
    "automated", "suspicious activity", "please verify",
    "enable javascript", "browser check",
]


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.netloc or parsed.path.split("/")[0]
    except Exception:
        return url.split("/")[0]


def _detect_wafs_from_headers(headers: Dict[str, str]) -> List[str]:
    """Detect WAFs from response headers."""
    detected = []
    header_str = json.dumps(headers).lower()
    for waf_name, sigs in _WAF_SIGNATURES.items():
        if any(s in header_str for s in sigs):
            detected.append(waf_name)
    return detected


def _detect_captchas_from_body(body: str) -> List[str]:
    """Detect captcha types from response body."""
    detected = []
    body_lower = body.lower()
    for cap_name, markers in _CAPTCHA_MARKERS.items():
        if any(m in body_lower for m in markers):
            detected.append(cap_name)
    return detected


def _detect_block(status_code: int, body: str) -> bool:
    """Detect if the response indicates a block."""
    if status_code in (403, 429, 503, 401):
        return True
    body_lower = body.lower()[:5000]
    return sum(1 for ind in _BLOCK_INDICATORS if ind in body_lower) >= 2


def _assess_difficulty(profile: TargetProfile) -> TargetDifficulty:
    """Assess target difficulty from profile data."""
    score = 0
    score += len(profile.waf_detected) * 15
    score += len(profile.captcha_types) * 20
    if profile.rate_limit_detected:
        score += 10
    if profile.tls_strict:
        score += 10
    if profile.js_challenge:
        score += 25
    if profile.behavioral_analysis:
        score += 30
    if profile.h2_required:
        score += 5
    if score < 10:
        return TargetDifficulty.OPEN
    elif score < 25:
        return TargetDifficulty.BASIC
    elif score < 50:
        return TargetDifficulty.MODERATE
    elif score < 80:
        return TargetDifficulty.HARDENED
    else:
        return TargetDifficulty.FORTRESS


def _recommend_level(difficulty: TargetDifficulty) -> EscalationLevel:
    """Recommend escalation level based on difficulty."""
    return {
        TargetDifficulty.OPEN: EscalationLevel.GHOST,
        TargetDifficulty.BASIC: EscalationLevel.SHADOW,
        TargetDifficulty.MODERATE: EscalationLevel.PHANTOM,
        TargetDifficulty.HARDENED: EscalationLevel.SPECTRE,
        TargetDifficulty.FORTRESS: EscalationLevel.SPECTRE,
    }[difficulty]


# ═══════════════════════════════════════════════════════════════════
# Strategy Engine — Builds execution plans
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ExecutionPlan:
    """Plan for executing a stealth request."""
    level: EscalationLevel
    steps: List[str] = field(default_factory=list)
    use_proxy: bool = False
    proxy_country: Optional[str] = None
    use_browser: bool = False
    use_h2: bool = False
    tls_profile: Optional[str] = None
    geo_spoof: bool = False
    behavior_sim: bool = False
    fingerprint_randomize: bool = False
    captcha_solver: bool = False
    evasion_scripts: bool = False
    request_pipeline: bool = True
    session_persist: bool = False
    delay_range: Tuple[float, float] = (0.5, 2.0)
    max_concurrent: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.name, "steps": self.steps,
            "use_proxy": self.use_proxy, "use_browser": self.use_browser,
            "use_h2": self.use_h2, "captcha_solver": self.captcha_solver,
            "evasion_scripts": self.evasion_scripts,
        }


def _build_plan(
    profile: TargetProfile,
    request: StealthRequest,
) -> ExecutionPlan:
    """Build execution plan based on target profile and request."""
    level = request.force_level or max(
        profile.recommended_level,
        EscalationLevel.GHOST,
    )
    # Cap at max escalation
    if level > request.max_escalation:
        level = request.max_escalation

    plan = ExecutionPlan(level=level)
    steps = []

    # GHOST: Basic stealth
    steps.append("apply_request_pipeline")
    steps.append("randomize_headers")
    steps.append("apply_cookies")

    if level >= EscalationLevel.SHADOW:
        steps.append("apply_tls_fingerprint")
        plan.tls_profile = "chrome_latest"
        if profile.h2_required or level >= EscalationLevel.SHADOW:
            steps.append("use_h2_transport")
            plan.use_h2 = True
        steps.append("apply_geo_consistency")
        plan.geo_spoof = True
        plan.delay_range = (1.0, 3.0)

    if level >= EscalationLevel.PHANTOM:
        steps.append("apply_fingerprint_engine")
        plan.fingerprint_randomize = True
        steps.append("apply_behavior_simulation")
        plan.behavior_sim = True
        steps.append("select_proxy")
        plan.use_proxy = True
        plan.proxy_country = request.proxy_country or request.geo_target
        plan.delay_range = (2.0, 5.0)
        plan.max_concurrent = 3

    if level >= EscalationLevel.SPECTRE:
        steps.append("launch_browser")
        plan.use_browser = True
        steps.append("inject_evasion_scripts")
        plan.evasion_scripts = True
        if profile.captcha_types:
            steps.append("solve_captcha")
            plan.captcha_solver = True
        steps.append("validate_stealth")
        plan.session_persist = True
        plan.delay_range = (3.0, 8.0)
        plan.max_concurrent = 2

    plan.steps = steps
    return plan


# ═══════════════════════════════════════════════════════════════════
# Module Integrator — Lazy-loads and wires all 13 modules
# ═══════════════════════════════════════════════════════════════════

class _ModuleHub:
    """Lazy-loading hub for all bypass modules."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._available: Dict[str, bool] = {}

    def _try_load(self, name: str, loader: Callable) -> Optional[Any]:
        if name in self._cache:
            return self._cache[name]
        try:
            obj = loader()
            self._cache[name] = obj
            self._available[name] = True
            return obj
        except Exception as e:
            logger.debug("Module %s unavailable: %s", name, e)
            self._available[name] = False
            self._cache[name] = None
            return None

    @property
    def anti_detection(self) -> Any:
        return self._try_load("anti_detection", lambda: (
            __import__("utils.anti_detection", fromlist=["AntiDetection"]).AntiDetection()
        ))

    @property
    def evasion(self) -> Any:
        return self._try_load("evasion", lambda: (
            __import__("utils.evasion_scripts", fromlist=["EvasionScriptEngine"]).EvasionScriptEngine()
        ))

    @property
    def tls(self) -> Any:
        return self._try_load("tls", lambda: (
            __import__("utils.tls_fingerprint", fromlist=["TLSFingerprintEngine"]).TLSFingerprintEngine()
        ))

    @property
    def h2(self) -> Any:
        return self._try_load("h2", lambda: (
            __import__("utils.h2_transport", fromlist=["H2TransportEngine"]).H2TransportEngine()
        ))

    @property
    def browser_validator(self) -> Any:
        return self._try_load("browser_validator", lambda: (
            __import__("utils.browser_validator", fromlist=["BrowserStealthValidator"]).BrowserStealthValidator()
        ))

    @property
    def proxy_pool(self) -> Any:
        return self._try_load("proxy_pool", lambda: (
            __import__("utils.proxy_pool", fromlist=["ProxyPool"]).ProxyPool()
        ))

    @property
    def browser_profile(self) -> Any:
        return self._try_load("browser_profile", lambda: (
            __import__("sessions.browser_profile", fromlist=["BrowserProfileManager"]).BrowserProfileManager()
        ))

    @property
    def session_store(self) -> Any:
        return self._try_load("session_store", lambda: (
            __import__("sessions.session_store", fromlist=["SessionStore"]).SessionStore()
        ))

    @property
    def geo(self) -> Any:
        return self._try_load("geo", lambda: (
            __import__("utils.geo_consistency", fromlist=["GeoConsistencyEngine"]).GeoConsistencyEngine()
        ))

    @property
    def behavior(self) -> Any:
        return self._try_load("behavior", lambda: (
            __import__("utils.behavior_engine", fromlist=["BehaviorEngine"]).BehaviorEngine()
        ))

    @property
    def request_pipeline(self) -> Any:
        return self._try_load("request_pipeline", lambda: (
            __import__("utils.request_pipeline", fromlist=["RequestPipelineEngine"]).RequestPipelineEngine()
        ))

    @property
    def fingerprint(self) -> Any:
        return self._try_load("fingerprint", lambda: (
            __import__("utils.fingerprint_engine", fromlist=["FingerprintEngine"]).FingerprintEngine()
        ))

    @property
    def captcha(self) -> Any:
        return self._try_load("captcha", lambda: (
            __import__("utils.captcha_engine", fromlist=["CaptchaEngine"]).CaptchaEngine()
        ))

    def get_status(self) -> Dict[str, bool]:
        """Get availability status of all modules."""
        # Force-check all
        _ = (self.anti_detection, self.evasion, self.tls, self.h2,
             self.browser_validator, self.proxy_pool, self.browser_profile,
             self.session_store, self.geo, self.behavior,
             self.request_pipeline, self.fingerprint, self.captcha)
        return dict(self._available)


# ═══════════════════════════════════════════════════════════════════
# Execution Engine — Runs the plan step by step
# ═══════════════════════════════════════════════════════════════════

class _ExecutionEngine:
    """Executes stealth plans using wired modules."""

    def __init__(self, hub: _ModuleHub) -> None:
        self._hub = hub
        self._http_session = None

    async def execute(
        self,
        request: StealthRequest,
        plan: ExecutionPlan,
        profile: TargetProfile,
    ) -> StealthResponse:
        """Execute a stealth request following the plan."""
        start = time.monotonic()
        chain = []

        # Build headers
        headers = dict(request.headers)
        if not headers.get("User-Agent"):
            headers["User-Agent"] = self._generate_user_agent(plan)
        if not headers.get("Accept"):
            headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        if not headers.get("Accept-Language"):
            headers["Accept-Language"] = "en-US,en;q=0.9,fi;q=0.8"

        chain.append({"step": "headers_prepared", "count": len(headers)})

        # Apply request pipeline
        pipeline = self._hub.request_pipeline
        if pipeline:
            try:
                domain = profile.domain
                if hasattr(pipeline, 'check_rate_limit'):
                    await pipeline.check_rate_limit(domain)
                chain.append({"step": "request_pipeline", "status": "applied"})
            except Exception as e:
                chain.append({"step": "request_pipeline", "status": "skipped", "error": str(e)})

        # TLS fingerprint (SHADOW+)
        if "apply_tls_fingerprint" in plan.steps:
            tls = self._hub.tls
            if tls:
                try:
                    fp = tls.generate_fingerprint(plan.tls_profile or "chrome_latest")
                    chain.append({"step": "tls_fingerprint", "profile": plan.tls_profile})
                except Exception as e:
                    chain.append({"step": "tls_fingerprint", "error": str(e)})

        # Geo consistency (SHADOW+)
        if "apply_geo_consistency" in plan.steps:
            geo = self._hub.geo
            if geo:
                try:
                    target_country = request.geo_target or "FI"
                    consistency = await geo.validate_geo_consistency(
                        headers=headers, target_country=target_country
                    )
                    chain.append({"step": "geo_consistency", "country": target_country})
                except Exception as e:
                    chain.append({"step": "geo_consistency", "error": str(e)})

        # Fingerprint engine (PHANTOM+)
        fp_id = None
        if "apply_fingerprint_engine" in plan.steps:
            fp_engine = self._hub.fingerprint
            if fp_engine:
                try:
                    fp_data = fp_engine.generate_fingerprint()
                    fp_id = hashlib.md5(json.dumps(fp_data, sort_keys=True).encode()).hexdigest()[:12]
                    chain.append({"step": "fingerprint_engine", "id": fp_id})
                except Exception as e:
                    chain.append({"step": "fingerprint_engine", "error": str(e)})

        # Proxy selection (PHANTOM+)
        proxy_used = None
        if "select_proxy" in plan.steps:
            pool = self._hub.proxy_pool
            if pool:
                try:
                    proxy_info = await pool.get_proxy(
                        country=plan.proxy_country,
                        protocol="https",
                    )
                    if proxy_info:
                        proxy_used = proxy_info.get("url", str(proxy_info))
                        chain.append({"step": "proxy_selected", "country": plan.proxy_country})
                except Exception as e:
                    chain.append({"step": "proxy_selection", "error": str(e)})

        # Delay (human-like timing)
        delay = random.uniform(*plan.delay_range)
        await asyncio.sleep(min(delay, 0.1))  # Capped for testing

        # Execute the actual request
        try:
            status_code, resp_headers, body = await self._make_request(
                url=request.url,
                method=request.method.value,
                headers=waf_result["headers"],
                cookies=waf_result["cookies"], # Pass generated cookies
                body=request.body or (json.dumps(request.json_body) if request.json_body else None),
                proxy=proxy_used,
                timeout=request.timeout,
                use_h2=plan.use_h2,
            )
            chain.append({"step": "request_sent", "status": status_code})
        except Exception as e:
            elapsed = time.monotonic() - start
            return StealthResponse(
                success=False, result=OperationResult.ERROR,
                escalation_used=plan.level, total_time=elapsed,
                errors=[str(e)], chain=chain,
            )

        # Check for blocks
        blocked = _detect_block(status_code, body)
        if blocked and plan.level < EscalationLevel.SPECTRE:
            chain.append({"step": "block_detected", "escalating": True})

        # Build response
        elapsed = time.monotonic() - start
        json_data = None
        try:
            if body.strip().startswith(("{", "[")):
                json_data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            pass

        result = OperationResult.SUCCESS
        if blocked:
            if status_code == 429:
                result = OperationResult.RATE_LIMITED
            elif any(c in body.lower() for c in ["captcha", "challenge"]):
                result = OperationResult.CAPTCHA
            else:
                result = OperationResult.BLOCKED

        return StealthResponse(
            success=not blocked and 200 <= status_code < 400,
            status_code=status_code,
            headers=resp_headers,
            body=body,
            json_data=json_data,
            escalation_used=plan.level,
            attempts=1,
            total_time=elapsed,
            result=result,
            target_profile=profile,
            session_id=request.session_id,
            proxy_used=proxy_used,
            fingerprint_id=fp_id,
            chain=chain,
        )

    async def _make_request(
        self, url: str, method: str, headers: Dict, cookies: Dict[str, str],
        body: Optional[str], proxy: Optional[str],
        timeout: float, use_h2: bool,
    ) -> Tuple[int, Dict[str, str], str]:
        """Make the actual HTTP request via async pipeline.
        
        v17.3: ASYNC_TRANSFORMATION — Zero blocking calls.
        All requests go through aiohttp + TrafficOrchestrator.
        Legacy urllib fallback REMOVED (was blocking main thread).
        """
        import asyncio

        # v17.3: Apply TrafficOrchestrator morphing to every request
        if _V341_STEALTH:
            try:
                traffic_orch = _get_to()
                profile = traffic_orch.morph()
                morphed_headers = traffic_orch.get_morphed_headers(profile)
                # Merge caller headers over morphed (caller wins on conflicts)
                merged = {**morphed_headers, **headers}
                headers = merged

                # Apply latency cloaking (non-deterministic delay)
                hks = _get_hks()
                delay = hks.api_request_delay()
                if delay > 0:
                    await asyncio.sleep(min(delay, 5.0))
            except Exception:
                pass  # Stealth enhancement is best-effort

        # Primary: aiohttp (fully async, supports proxy)
        try:
            import aiohttp
            connector_kwargs: Dict[str, Any] = {"ssl": False}
            connector = aiohttp.TCPConnector(**connector_kwargs)
            async with aiohttp.ClientSession(connector=connector) as session:
                kwargs: Dict[str, Any] = {
                    "method": method, "url": url, "headers": headers,
                    "cookies": cookies, # Use the generated cookies
                    "timeout": aiohttp.ClientTimeout(total=timeout),
                }
                if body:
                    kwargs["data"] = body
                if proxy:
                    kwargs["proxy"] = proxy
                async with session.request(**kwargs) as resp:
                    text = await resp.text()
                    status = resp.status
                    resp_headers = dict(resp.headers)

                    # v17.3: Feed response back to WAF adaptive engine
                    if _V341_STEALTH:
                        try:
                            waf = _get_waf()
                            from arki_project.utils.waf_adaptive import WAFResponse
                            _latency = (time.monotonic() - start) * 1000  # v29.0: real latency
                            waf.record_response(WAFResponse(
                                status_code=status,
                                latency_ms=_latency,
                                headers=resp_headers,
                                body_snippet=text[:2000],
                                blocked=status in (403, 429, 503),
                            ))
                        except Exception as _err:
                            logger.warning("Suppressed error: %s", _err)

                    return status, resp_headers, text
        except ImportError:
            pass

        # Fallback: asyncio-wrapped non-blocking HTTP (NO urllib)
        # Uses raw asyncio sockets — zero blocking on main thread
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname or ""
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"
            if parsed.query:
                path += f"?{parsed.query}"

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=(parsed.scheme == "https")),
                timeout=timeout,
            )
            # Build raw HTTP request
            req_line = f"{method} {path} HTTP/1.1\r\n"
            req_headers = f"Host: {host}\r\n"
            for k, v in headers.items():
                if k.lower() != "host":
                    req_headers += f"{k}: {v}\r\n"
            if body:
                req_headers += f"Content-Length: {len(body.encode())}\r\n"
            req_headers += "Connection: close\r\n\r\n"
            raw_req = (req_line + req_headers).encode()
            if body:
                raw_req += body.encode()
            writer.write(raw_req)
            await writer.drain()

            # Read response
            raw_resp = await asyncio.wait_for(reader.read(65536), timeout=timeout)
            writer.close()

            # Parse status line
            resp_text = raw_resp.decode("utf-8", errors="replace")
            lines = resp_text.split("\r\n")
            status_line = lines[0] if lines else ""
            status_code = 0
            if " " in status_line:
                try:
                    status_code = int(status_line.split(" ")[1])
                except (ValueError, IndexError):
                    pass
            # Find body (after empty line)
            body_start = resp_text.find("\r\n\r\n")
            resp_body = resp_text[body_start + 4:] if body_start >= 0 else ""
            return status_code, {}, resp_body

        except Exception as e:
            return 0, {}, f"Async request failed: {e}"

    def _generate_user_agent(self, plan: ExecutionPlan) -> str:
        """Generate appropriate user agent based on plan level."""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        ]
        ad = self._hub.anti_detection
        if ad and hasattr(ad, "get_random_user_agent"):
            try:
                return ad.get_random_user_agent()
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)
        return random.choice(agents)


# ═══════════════════════════════════════════════════════════════════
# StealthOrchestrator — The SUPREME Coordinator
# ═══════════════════════════════════════════════════════════════════

class StealthOrchestrator:
    """
    Supreme Stealth Orchestrator — unifies all 13 bypass modules.

    Usage:
        orch = StealthOrchestrator()
        result = await orch.execute("https://target.com")
        batch = await orch.batch_execute(["url1", "url2", ...])
        chain = await orch.execute_chain([req1, req2, ...])
    """

    def __init__(
        self,
        default_level: EscalationLevel = EscalationLevel.GHOST,
        auto_escalate: bool = True,
        max_retries: int = 3,
        learn_from_failures: bool = True,
    ) -> None:
        self._hub = _ModuleHub()
        self._engine = _ExecutionEngine(self._hub)
        self._default_level = default_level
        self._auto_escalate = auto_escalate
        self._max_retries = max_retries
        self._learn = learn_from_failures
        self._target_cache: Dict[str, TargetProfile] = {}
        self._stats = {
            "total_requests": 0, "successful": 0, "failed": 0,
            "escalations": 0, "retries": 0, "captchas_solved": 0,
            "avg_response_time": 0.0, "level_distribution": {
                "GHOST": 0, "SHADOW": 0, "PHANTOM": 0, "SPECTRE": 0,
            },
        }
        self._lock = asyncio.Lock()

    # ─── Public API ───────────────────────────────────────────

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        json_body: Optional[Dict[str, Any]] = None,
        level: Optional[EscalationLevel] = None,
        timeout: float = 30.0,
        geo_target: Optional[str] = None,
        session_id: Optional[str] = None,
        extract: Optional[str] = None,
    ) -> StealthResponse:
        """Execute a single stealth request with auto-escalation."""
        request = StealthRequest(
            url=url,
            method=RequestMethod(method.upper()),
            headers=headers or {},
            body=body,
            json_body=json_body,
            force_level=level,
            timeout=timeout,
            geo_target=geo_target,
            session_id=session_id,
            extract_data=extract,
            max_retries=self._max_retries,
        )
        return await self._execute_with_escalation(request)

    async def batch_execute(
        self,
        urls: List[str],
        method: str = "GET",
        concurrency: int = 5,
        level: Optional[EscalationLevel] = None,
        delay_between: float = 1.0,
    ) -> BatchResult:
        """Execute multiple URLs with controlled concurrency."""
        start = time.monotonic()
        semaphore = asyncio.Semaphore(concurrency)
        results: List[StealthResponse] = []

        async def _run_one(url: str) -> StealthResponse:
            async with semaphore:
                if delay_between > 0:
                    await asyncio.sleep(random.uniform(0, min(delay_between, 0.05)))
                return await self.execute(url, method=method, level=level)

        tasks = [_run_one(u) for u in urls]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for resp in responses:
            if isinstance(resp, Exception):
                results.append(StealthResponse(
                    success=False, result=OperationResult.ERROR,
                    errors=[str(resp)],
                ))
            else:
                results.append(resp)

        elapsed = time.monotonic() - start
        succeeded = sum(1 for r in results if r.success)
        levels = [r.escalation_used for r in results]
        avg_level = sum(l.value for l in levels) / max(len(levels), 1)

        return BatchResult(
            total=len(urls), succeeded=succeeded,
            failed=len(urls) - succeeded, responses=results,
            total_time=elapsed, avg_escalation=avg_level,
        )

    async def execute_chain(
        self,
        requests: List[StealthRequest],
        stop_on_failure: bool = True,
    ) -> List[StealthResponse]:
        """Execute a chain of requests sharing session state."""
        results = []
        session_cookies: Dict[str, str] = {}

        for req in requests:
            req.cookies.update(session_cookies)
            resp = await self._execute_with_escalation(req)
            results.append(resp)

            # Carry cookies forward
            for k, v in resp.headers.items():
                if k.lower() == "set-cookie":
                    parts = v.split(";")[0].split("=", 1)
                    if len(parts) == 2:
                        session_cookies[parts[0].strip()] = parts[1].strip()

            if not resp.success and stop_on_failure:
                break

        return results

    async def analyze_target(self, url: str) -> TargetProfile:
        """Analyze a target URL to assess difficulty and recommend strategy."""
        domain = _extract_domain(url)
        if domain in self._target_cache:
            cached = self._target_cache[domain]
            if time.time() - cached.last_scanned < 300:
                return cached

        profile = TargetProfile(url=url, domain=domain)

        # Quick probe
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            }
            status, resp_headers, body = await self._engine._make_request(
                url, "GET", headers, None, None, 10.0, False,
            )

            profile.waf_detected = _detect_wafs_from_headers(resp_headers)
            profile.captcha_types = _detect_captchas_from_body(body)
            profile.rate_limit_detected = status == 429
            profile.js_challenge = any(
                m in body.lower()
                for m in ["enable javascript", "browser check", "checking your browser"]
            )

            # Tech detection
            server = resp_headers.get("server", resp_headers.get("Server", ""))
            if server:
                profile.tech_stack["server"] = server
            powered = resp_headers.get("x-powered-by", resp_headers.get("X-Powered-By", ""))
            if powered:
                profile.tech_stack["powered_by"] = powered

        except Exception as e:
            profile.notes.append(f"Probe error: {e}")

        profile.difficulty = _assess_difficulty(profile)
        profile.recommended_level = _recommend_level(profile.difficulty)
        profile.last_scanned = time.time()
        profile.scan_count += 1

        self._target_cache[domain] = profile
        return profile

    def get_module_status(self) -> Dict[str, bool]:
        """Get availability of all bypass modules."""
        return self._hub.get_status()

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            **self._stats,
            "modules_available": sum(
                1 for v in self._hub.get_status().values() if v
            ),
            "modules_total": 13,
            "targets_profiled": len(self._target_cache),
            "auto_escalate": self._auto_escalate,
            "default_level": self._default_level.name,
        }

    def clear_target_cache(self) -> int:
        """Clear cached target profiles. Returns count cleared."""
        count = len(self._target_cache)
        self._target_cache.clear()
        return count

    def get_target_profile(self, domain: str) -> Optional[TargetProfile]:
        """Get cached target profile."""
        return self._target_cache.get(domain)

    # ─── Internal ─────────────────────────────────────────────

    async def _execute_with_escalation(
        self, request: StealthRequest,
    ) -> StealthResponse:
        """Execute with auto-escalation on failure."""
        profile = await self.analyze_target(request.url)
        current_level = request.force_level or max(
            profile.recommended_level, self._default_level,
        )

        last_response: Optional[StealthResponse] = None

        for attempt in range(request.max_retries + 1):
            plan = _build_plan(profile, request)
            plan.level = current_level

            response = await self._engine.execute(request, plan, profile)
            last_response = response
            response.attempts = attempt + 1

            # Track stats
            async with self._lock:
                self._stats["total_requests"] += 1
                self._stats["level_distribution"][current_level.name] += 1

            if response.success:
                async with self._lock:
                    self._stats["successful"] += 1
                    # Update running average
                    n = self._stats["successful"]
                    self._stats["avg_response_time"] = (
                        self._stats["avg_response_time"] * (n - 1) + response.total_time
                    ) / n

                # Learn: lower difficulty if we succeed at low level
                if self._learn and current_level <= EscalationLevel.SHADOW:
                    profile.success_rate = min(1.0, profile.success_rate + 0.1)
                return response

            # Failed — should we escalate?
            if (
                self._auto_escalate
                and current_level < request.max_escalation
                and current_level < EscalationLevel.SPECTRE
                and response.result != OperationResult.TIMEOUT
            ):
                old_level = current_level
                current_level = EscalationLevel(min(current_level + 1, EscalationLevel.SPECTRE))
                async with self._lock:
                    self._stats["escalations"] += 1
                    self._stats["retries"] += 1
                logger.info(
                    "Escalating %s → %s for %s (attempt %d)",
                    old_level.name, current_level.name, request.url, attempt + 1,
                )

                # Learn: raise difficulty
                if self._learn:
                    profile.success_rate = max(0.0, profile.success_rate - 0.2)
                    profile.recommended_level = current_level
                    profile.difficulty = _assess_difficulty(profile)

                # Delay before retry
                await asyncio.sleep(min(random.uniform(1, 3) * (attempt + 1), 0.1))
            else:
                break

        # All retries exhausted
        if last_response:
            async with self._lock:
                self._stats["failed"] += 1
            return last_response

        return StealthResponse(
            success=False, result=OperationResult.ERROR,
            errors=["All retries exhausted"],
        )


# ═══════════════════════════════════════════════════════════════════
# Convenience functions
# ═══════════════════════════════════════════════════════════════════

_default_orchestrator: Optional[StealthOrchestrator] = None


def get_orchestrator(**kwargs) -> StealthOrchestrator:
    """Get or create the default orchestrator singleton."""
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = StealthOrchestrator(**kwargs)
    return _default_orchestrator


async def stealth_get(url: str, **kwargs) -> StealthResponse:
    """Quick stealth GET request."""
    return await get_orchestrator().execute(url, method="GET", **kwargs)


async def stealth_post(url: str, **kwargs) -> StealthResponse:
    """Quick stealth POST request."""
    return await get_orchestrator().execute(url, method="POST", **kwargs)


async def analyze_target(url: str) -> TargetProfile:
    """Quick target analysis."""
    return await get_orchestrator().analyze_target(url)


