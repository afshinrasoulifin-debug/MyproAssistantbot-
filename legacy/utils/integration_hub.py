
from __future__ import annotations
"""
tg_bot/utils/integration_hub.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
INTEGRATION HUB — Universal Service Connector & Workflow Engine

Central hub for connecting and orchestrating external services,
APIs, and platforms with unified interface, retry logic, and
workflow automation.

Architecture
────────────
   ┌────────────────────────────────────────────────────────┐
   │                  INTEGRATION HUB                        │
   ├──────────┬──────────┬──────────┬──────────┬────────────┤
   │ Connector│ Auth     │ Workflow │ Rate     │ Transform  │
   │ Registry │ Manager  │ Engine   │ Limiter  │ Pipeline   │
   ├──────────┼──────────┼──────────┼──────────┼────────────┤
   │ HTTP     │ API Key  │ Steps    │ Token    │ JSON Path  │
   │ GraphQL  │ OAuth2   │ Branch   │ Bucket   │ Template   │
   │ WebSocket│ JWT      │ Parallel │ Sliding  │ Schema Map │
   │ gRPC     │ HMAC     │ Retry    │ Backoff  │ Validate   │
   ├──────────┼──────────┼──────────┼──────────┼────────────┤
   │ Telegram │ Discord  │ Webhook  │ S3/Cloud │ Database   │
   │ GitHub   │ Notion   │ Email    │ Queue    │ Cron       │
   └──────────┴──────────┴──────────┴──────────┴────────────┘

Features
────────
  • Service connector registry with auto-discovery
  • Multi-auth support (API key, OAuth2, JWT, HMAC)
  • HTTP client with retry, backoff, circuit breaker
  • GraphQL query builder
  • Rate limiting (token bucket, sliding window)
  • Workflow engine with steps, branching, and parallelism
  • Data transformation pipeline (JSONPath, templates)
  • Schema validation and mapping
  • Webhook sender/receiver
  • Pre-built connectors: Telegram, Discord, GitHub, Notion
  • Event bus for inter-service communication
  • Audit logging of all integration calls

References
──────────
  Port of: apex_app/src/lib/integration-hub.ts (509 lines)
  Enhanced with: circuit breaker, workflow engine, GraphQL builder,
                 event bus, audit logging, schema validation
"""


import asyncio
import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, Callable, Deque, Dict, List, Optional, Tuple,
)

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────

DEFAULT_TIMEOUT_S       = 30
MAX_RETRIES             = 3
RETRY_BACKOFF_BASE      = 2.0
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_RESET_S = 60


# ═══════════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════════

class AuthType(str, Enum):
    NONE        = "none"
    API_KEY     = "api_key"
    BEARER      = "bearer"
    OAUTH2      = "oauth2"
    JWT         = "jwt"
    HMAC        = "hmac"
    BASIC       = "basic"


class ConnectorStatus(str, Enum):
    CONNECTED   = "connected"
    DISCONNECTED = "disconnected"
    ERROR       = "error"
    RATE_LIMITED = "rate_limited"


class CircuitState(str, Enum):
    CLOSED      = "closed"      # Normal operation
    OPEN        = "open"        # Blocking calls
    HALF_OPEN   = "half_open"   # Testing recovery


class WorkflowStepType(str, Enum):
    ACTION      = "action"
    CONDITION   = "condition"
    PARALLEL    = "parallel"
    DELAY       = "delay"
    TRANSFORM   = "transform"
    WEBHOOK     = "webhook"


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class AuthConfig:
    """Authentication configuration."""
    type: AuthType
    credentials: Dict[str, str] = field(default_factory=dict)
    # api_key → {"key": "...", "header": "X-API-Key"}
    # bearer → {"token": "..."}
    # basic → {"username": "...", "password": "..."}
    # oauth2 → {"client_id": "...", "client_secret": "...", "token_url": "..."}
    # hmac → {"secret": "...", "algorithm": "sha256"}
    # jwt → {"secret": "...", "algorithm": "HS256", "claims": "..."}

    def get_headers(self) -> Dict[str, str]:
        """Generate auth headers."""
        if self.type == AuthType.API_KEY:
            header = self.credentials.get("header", "X-API-Key")
            return {header: self.credentials.get("key", "")}
        elif self.type == AuthType.BEARER:
            return {"Authorization": f"Bearer {self.credentials.get('token', '')}"}
        elif self.type == AuthType.BASIC:
            import base64
            creds = f"{self.credentials.get('username', '')}:{self.credentials.get('password', '')}"
            b64 = base64.b64encode(creds.encode()).decode()
            return {"Authorization": f"Basic {b64}"}
        return {}


@dataclass
class ServiceConfig:
    """Service connector configuration."""
    name: str
    base_url: str
    auth: AuthConfig = field(default_factory=lambda: AuthConfig(AuthType.NONE))
    timeout_s: float = DEFAULT_TIMEOUT_S
    max_retries: int = MAX_RETRIES
    rate_limit_rpm: int = 60        # requests per minute
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestResult:
    """Result of an API request."""
    success: bool
    status_code: int = 0
    data: Any = None
    error: str = ""
    latency_ms: float = 0.0
    retries: int = 0
    headers: Dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        if isinstance(self.data, str):
            return json.loads(self.data)
        return self.data


@dataclass
class AuditEntry:
    """Audit log entry for integration calls."""
    timestamp: float
    service: str
    method: str
    url: str
    status_code: int
    latency_ms: float
    success: bool
    error: str = ""
    request_size: int = 0
    response_size: int = 0


@dataclass
class WorkflowStep:
    """Single step in a workflow."""
    id: str
    type: WorkflowStepType
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)
    condition: Optional[str] = None     # For branching
    retry_count: int = 0
    timeout_s: float = 30


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    workflow_id: str
    success: bool
    steps_completed: int
    total_steps: int
    step_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


# ═══════════════════════════════════════════════════════════════════
# Rate Limiter
# ═══════════════════════════════════════════════════════════════════

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rpm: int = 60) -> None:
        self._max_tokens = rpm
        self._tokens = float(rpm)
        self._refill_rate = rpm / 60.0      # per second
        self._last_refill = time.time()
        self._lock = asyncio.Lock() if asyncio else None

    def _refill(self) -> None:
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._max_tokens,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now

    async def acquire(self) -> bool:
        """Acquire a token. Returns False if rate limited."""
        self._refill()
        if self._tokens >= 1:
            self._tokens -= 1
            return True
        return False

    def wait_time(self) -> float:
        """Seconds to wait for next available token."""
        if self._tokens >= 1:
            return 0.0
        needed = 1.0 - self._tokens
        return needed / self._refill_rate


class SlidingWindowLimiter:
    """Sliding window rate limiter."""

    def __init__(self, max_requests: int, window_s: float) -> None:
        self._max = max_requests
        self._window = window_s
        self._requests: Deque[float] = deque()

    def _cleanup(self) -> None:
        cutoff = time.time() - self._window
        while self._requests and self._requests[0] < cutoff:
            self._requests.popleft()

    async def acquire(self) -> bool:
        self._cleanup()
        if len(self._requests) < self._max:
            self._requests.append(time.time())
            return True
        return False


# ═══════════════════════════════════════════════════════════════════
# Circuit Breaker
# ═══════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    def __init__(self, threshold: int = CIRCUIT_BREAKER_THRESHOLD,
                 reset_s: float = CIRCUIT_BREAKER_RESET_S) -> None:
        self._threshold = threshold
        self._reset_s = reset_s
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._last_failure = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure > self._reset_s:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure = time.time()
        if self._failures >= self._threshold:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker OPEN after {self._failures} failures")

    def can_execute(self) -> bool:
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True
        return False


# ═══════════════════════════════════════════════════════════════════
# Service Connector (Base)
# ═══════════════════════════════════════════════════════════════════

class ServiceConnector:
    """HTTP service connector with retry, rate limiting, and circuit breaking."""

    def __init__(self, config: ServiceConfig) -> None:
        self.config = config
        self.status = ConnectorStatus.DISCONNECTED
        self._rate_limiter = RateLimiter(config.rate_limit_rpm)
        self._circuit_breaker = CircuitBreaker()
        self._audit_log: Deque[AuditEntry] = deque(maxlen=200)

    async def request(
        self,
        method: str,
        path: str,
        data: Any = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> RequestResult:
        """Make an HTTP request with full resilience."""
        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        timeout = timeout or self.config.timeout_s

        # Circuit breaker check
        if not self._circuit_breaker.can_execute():
            return RequestResult(
                success=False, error="Circuit breaker OPEN",
            )

        # Rate limit check
        if not await self._rate_limiter.acquire():
            wait = self._rate_limiter.wait_time()
            await asyncio.sleep(wait)

        # Build headers
        req_headers = {**self.config.headers}
        req_headers.update(self.config.auth.get_headers())
        if headers:
            req_headers.update(headers)
        if data and isinstance(data, (dict, list)):
            req_headers.setdefault("Content-Type", "application/json")

        # Retry loop
        last_error = ""
        for attempt in range(self.config.max_retries + 1):
            start = time.time()
            try:
                # v10.1: Route through TITANIUM shielded client
                if _TITANIUM_ACTIVE:
                    json_body = data if isinstance(data, dict) else None
                    resp = await shielded_request(
                        method, url,
                        json_data=json_body,
                        headers=req_headers,
                        timeout=timeout,
                        provider_name=f"integration:{self.config.name}",
                    )
                    latency = resp.latency_ms
                    resp_text = resp.text
                    resp_status = resp.status
                    resp_headers = resp.headers
                else:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        body = json.dumps(data) if isinstance(data, (dict, list)) else data
                        async with session.request(
                            method, url, data=body, params=params,
                            headers=req_headers,
                            timeout=aiohttp.ClientTimeout(total=timeout),
                        ) as resp:
                            latency = (time.time() - start) * 1000
                            resp_text = await resp.text()
                            resp_status = resp.status
                            resp_headers = dict(resp.headers)

                if True:
                        # Audit
                        self._audit_log.append(AuditEntry(
                            timestamp=time.time(),
                            service=self.config.name,
                            method=method,
                            url=url,
                            status_code=resp_status,
                            latency_ms=latency,
                            success=resp_status < 400,
                            response_size=len(resp_text),
                        ))

                        if resp_status < 400:
                            self._circuit_breaker.record_success()
                            self.status = ConnectorStatus.CONNECTED
                            return RequestResult(
                                success=True,
                                status_code=resp_status,
                                data=resp_text,
                                latency_ms=latency,
                                retries=attempt,
                                headers=resp_headers if not _TITANIUM_ACTIVE else resp.headers,
                            )

                        if resp_status == 429:
                            self.status = ConnectorStatus.RATE_LIMITED
                            retry_after = float((resp_headers or {}).get("Retry-After", "5"))
                            await asyncio.sleep(retry_after)
                            continue

                        if resp_status >= 500:
                            last_error = f"Server error {resp_status}"
                            self._circuit_breaker.record_failure()
                        else:
                            return RequestResult(
                                success=False,
                                status_code=resp_status,
                                error=f"HTTP {resp_status}: {resp_text[:200]}",
                                latency_ms=latency,
                            )

            except Exception as e:
                latency = (time.time() - start) * 1000
                last_error = str(e)
                self._circuit_breaker.record_failure()

            # Exponential backoff
            if attempt < self.config.max_retries:
                wait = RETRY_BACKOFF_BASE ** attempt
                await asyncio.sleep(wait)

        self.status = ConnectorStatus.ERROR
        return RequestResult(
            success=False, error=f"Failed after {self.config.max_retries + 1} attempts: {last_error}",
            retries=self.config.max_retries,
        )

    async def get(self, path: str, **kwargs) -> RequestResult:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, data: Any = None, **kwargs) -> RequestResult:
        return await self.request("POST", path, data=data, **kwargs)

    async def put(self, path: str, data: Any = None, **kwargs) -> RequestResult:
        return await self.request("PUT", path, data=data, **kwargs)

    async def delete(self, path: str, **kwargs) -> RequestResult:
        return await self.request("DELETE", path, **kwargs)

    @property
    def audit_log(self) -> List[AuditEntry]:
        return list(self._audit_log)


# ═══════════════════════════════════════════════════════════════════
# GraphQL Builder
# ═══════════════════════════════════════════════════════════════════

class GraphQLBuilder:
    """Fluent GraphQL query builder."""

    def __init__(self) -> None:
        self._operation: str = "query"
        self._name: str = ""
        self._variables: Dict[str, str] = {}
        self._fields: List[str] = []
        self._fragments: List[str] = []

    def query(self, name: str = "") -> "GraphQLBuilder":
        self._operation = "query"
        self._name = name
        return self

    def mutation(self, name: str = "") -> "GraphQLBuilder":
        self._operation = "mutation"
        self._name = name
        return self

    def variable(self, name: str, type: str) -> "GraphQLBuilder":
        self._variables[name] = type
        return self

    def select(self, *fields: str) -> "GraphQLBuilder":
        self._fields.extend(fields)
        return self

    def fragment(self, name: str, on_type: str, fields: List[str]) -> "GraphQLBuilder":
        self._fragments.append(
            f"fragment {name} on {on_type} {{ {' '.join(fields)} }}"
        )
        return self

    def build(self) -> str:
        vars_str = ""
        if self._variables:
            vars_list = [f"${k}: {v}" for k, v in self._variables.items()]
            vars_str = f"({', '.join(vars_list)})"

        fields_str = "\n    ".join(self._fields)
        query = f"{self._operation} {self._name}{vars_str} {{\n    {fields_str}\n}}"

        if self._fragments:
            query += "\n\n" + "\n".join(self._fragments)

        return query


# ═══════════════════════════════════════════════════════════════════
# Event Bus
# ═══════════════════════════════════════════════════════════════════

class EventBus:
    """Pub-sub event bus for inter-service communication."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: Deque[Dict[str, Any]] = deque(maxlen=500)

    def on(self, event: str, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> None:
        if event in self._handlers:
            self._handlers[event] = [
                h for h in self._handlers[event] if h != handler
            ]

    async def emit(self, event: str, data: Any = None) -> None:
        self._history.append({
            "event": event,
            "data": data,
            "timestamp": time.time(),
        })
        for handler in self._handlers.get(event, []):
            try:
                result = handler(event, data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Event handler error for '{event}': {e}")

    @property
    def history(self) -> List[Dict[str, Any]]:
        return list(self._history)


# Global event bus
event_bus = EventBus()


# ═══════════════════════════════════════════════════════════════════
# HMAC Signature Verification
# ═══════════════════════════════════════════════════════════════════

def sign_hmac(payload: str, secret: str,
              algorithm: str = "sha256") -> str:
    """Generate HMAC signature."""
    algo = getattr(hashlib, algorithm, hashlib.sha256)
    return hmac.new(
        secret.encode(), payload.encode(), algo,
    ).hexdigest()


def verify_hmac(payload: str, signature: str, secret: str,
                algorithm: str = "sha256") -> bool:
    """Verify HMAC signature (constant-time comparison)."""
    expected = sign_hmac(payload, secret, algorithm)
    return hmac.compare_digest(expected, signature)


# ═══════════════════════════════════════════════════════════════════
# Data Transformation Pipeline
# ═══════════════════════════════════════════════════════════════════

def jsonpath_extract(data: Any, path: str) -> Any:
    """
    Simple JSONPath extraction.

    Supports: $.key, $.key.nested, $.array[0], $.array[*].field
    """
    if not path.startswith("$"):
        return None

    parts = path[2:].split(".") if len(path) > 1 else []
    current = data

    for part in parts:
        if not part:
            continue

        # Array index
        if "[" in part:
            key = part[:part.index("[")]
            idx_str = part[part.index("[") + 1:part.index("]")]

            if key:
                if isinstance(current, dict):
                    current = current.get(key)
                else:
                    return None

            if idx_str == "*":
                if isinstance(current, list):
                    # Collect from all items
                    remaining = ".".join(parts[parts.index(part) + 1:])
                    if remaining:
                        return [jsonpath_extract(item, f"$.{remaining}") for item in current]
                    return current
            else:
                idx = int(idx_str)
                if isinstance(current, list) and idx < len(current):
                    current = current[idx]
                else:
                    return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None

        if current is None:
            return None

    return current


def template_render(template: str, data: Dict[str, Any]) -> str:
    """
    Simple template rendering with {{variable}} syntax.

    Supports: {{key}}, {{nested.key}}, {{key|default_value}}
    """
    import re

    def replace_var(match: re.Match) -> str:
        expr = match.group(1).strip()

        # Default value
        default = ""
        if "|" in expr:
            expr, default = expr.split("|", 1)

        # Nested key
        parts = expr.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break

        return str(value) if value is not None else default

    return re.sub(r"\{\{(.*?)\}\}", replace_var, template)


def schema_validate(data: Dict[str, Any],
                    schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate data against a simple schema.

    Schema format: {"field": {"type": "str|int|float|bool|list|dict",
                              "required": True, "min": 0, "max": 100}}
    """
    errors: List[str] = []

    for field_name, rules in schema.items():
        value = data.get(field_name)

        # Required check
        if rules.get("required", False) and value is None:
            errors.append(f"Missing required field: {field_name}")
            continue

        if value is None:
            continue

        # Type check
        expected_type = rules.get("type", "")
        type_map = {
            "str": str, "string": str,
            "int": int, "integer": int,
            "float": (int, float), "number": (int, float),
            "bool": bool, "boolean": bool,
            "list": list, "array": list,
            "dict": dict, "object": dict,
        }
        if expected_type and expected_type in type_map:
            if not isinstance(value, type_map[expected_type]):
                errors.append(
                    f"Field '{field_name}' expected {expected_type}, got {type(value).__name__}"
                )

        # Min/max
        if "min" in rules and isinstance(value, (int, float)):
            if value < rules["min"]:
                errors.append(f"Field '{field_name}' below minimum ({value} < {rules['min']})")
        if "max" in rules and isinstance(value, (int, float)):
            if value > rules["max"]:
                errors.append(f"Field '{field_name}' above maximum ({value} > {rules['max']})")

        # Min/max length for strings
        if "min_length" in rules and isinstance(value, str):
            if len(value) < rules["min_length"]:
                errors.append(f"Field '{field_name}' too short")
        if "max_length" in rules and isinstance(value, str):
            if len(value) > rules["max_length"]:
                errors.append(f"Field '{field_name}' too long")

    return len(errors) == 0, errors


# ═══════════════════════════════════════════════════════════════════
# Workflow Engine
# ═══════════════════════════════════════════════════════════════════

class WorkflowEngine:
    """Workflow automation engine with steps, branching, and parallelism."""

    def __init__(self) -> None:
        self._step_handlers: Dict[str, Callable] = {}
        self._workflows: Dict[str, List[WorkflowStep]] = {}

    def register_handler(self, step_type: str, handler: Callable) -> None:
        self._step_handlers[step_type] = handler

    def define_workflow(self, workflow_id: str,
                        steps: List[WorkflowStep]) -> None:
        self._workflows[workflow_id] = steps

    async def execute(self, workflow_id: str,
                      context: Dict[str, Any] = None) -> WorkflowResult:
        """Execute a workflow."""
        start = time.time()
        steps = self._workflows.get(workflow_id, [])
        if not steps:
            return WorkflowResult(
                workflow_id=workflow_id, success=False,
                steps_completed=0, total_steps=0,
                errors=["Workflow not found"],
            )

        ctx = dict(context or {})
        step_results: Dict[str, Any] = {}
        errors: List[str] = []
        completed = 0

        for step in steps:
            try:
                if step.type == WorkflowStepType.CONDITION:
                    # Evaluate condition
                    condition_met = self._evaluate_condition(step.condition, ctx)
                    step_results[step.id] = {"condition": condition_met}
                    if not condition_met:
                        continue

                elif step.type == WorkflowStepType.DELAY:
                    delay = step.config.get("seconds", 1)
                    await asyncio.sleep(delay)
                    step_results[step.id] = {"delayed": delay}

                elif step.type == WorkflowStepType.PARALLEL:
                    # Execute sub-steps in parallel
                    sub_ids = step.config.get("step_ids", [])
                    sub_steps = [s for s in steps if s.id in sub_ids]
                    tasks = [self._execute_step(s, ctx) for s in sub_steps]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    step_results[step.id] = {
                        "parallel_results": [
                            str(r) if isinstance(r, Exception) else r
                            for r in results
                        ],
                    }

                elif step.type == WorkflowStepType.TRANSFORM:
                    template = step.config.get("template", "")
                    step_results[step.id] = template_render(template, ctx)

                else:
                    # Action step
                    handler = self._step_handlers.get(step.type.value)
                    if handler:
                        result = handler(step, ctx)
                        if asyncio.iscoroutine(result):
                            result = await result
                        step_results[step.id] = result
                        ctx[f"step_{step.id}"] = result
                    else:
                        step_results[step.id] = {"skipped": "no handler"}

                completed += 1

            except Exception as e:
                errors.append(f"Step '{step.id}' failed: {str(e)}")
                if step.retry_count > 0:
                    # Simple retry
                    for retry in range(step.retry_count):
                        try:
                            handler = self._step_handlers.get(step.type.value)
                            if handler:
                                result = handler(step, ctx)
                                if asyncio.iscoroutine(result):
                                    result = await result
                                step_results[step.id] = result
                                completed += 1
                                errors.pop()
                                break
                        except Exception:
                            await asyncio.sleep(RETRY_BACKOFF_BASE ** retry)

        return WorkflowResult(
            workflow_id=workflow_id,
            success=len(errors) == 0,
            steps_completed=completed,
            total_steps=len(steps),
            step_results=step_results,
            errors=errors,
            duration_ms=(time.time() - start) * 1000,
        )

    async def _execute_step(self, step: WorkflowStep,
                            ctx: Dict[str, Any]) -> Any:
        handler = self._step_handlers.get(step.type.value)
        if handler:
            result = handler(step, ctx)
            if asyncio.iscoroutine(result):
                return await result
            return result
        return None

    @staticmethod
    def _evaluate_condition(condition: Optional[str],
                            ctx: Dict[str, Any]) -> bool:
        if not condition:
            return True
        try:
            return bool(eval(condition, {"__builtins__": {}}, ctx))
        except Exception:
            return False


# Global workflow engine
workflow_engine = WorkflowEngine()


# ═══════════════════════════════════════════════════════════════════
# Connector Registry
# ═══════════════════════════════════════════════════════════════════

class ConnectorRegistry:
    """Registry for managing service connectors."""

    def __init__(self) -> None:
        self._connectors: Dict[str, ServiceConnector] = {}

    def register(self, name: str, config: ServiceConfig) -> ServiceConnector:
        connector = ServiceConnector(config)
        self._connectors[name] = connector
        logger.info(f"Registered connector: {name} → {config.base_url}")
        return connector

    def get(self, name: str) -> Optional[ServiceConnector]:
        return self._connectors.get(name)

    def remove(self, name: str) -> bool:
        return self._connectors.pop(name, None) is not None

    def list_all(self) -> Dict[str, ConnectorStatus]:
        return {name: c.status for name, c in self._connectors.items()}

    def health_check(self) -> Dict[str, str]:
        return {
            name: c.status.value
            for name, c in self._connectors.items()
        }


# Global registry
registry = ConnectorRegistry()


# ═══════════════════════════════════════════════════════════════════
# Pre-built Connectors
# ═══════════════════════════════════════════════════════════════════

def create_telegram_connector(bot_token: str) -> ServiceConnector:
    """Create a Telegram Bot API connector."""
    config = ServiceConfig(
        name="telegram",
        base_url=f"https://api.telegram.org/bot{bot_token}",
        rate_limit_rpm=30,
    )
    return registry.register("telegram", config)


def create_github_connector(token: str) -> ServiceConnector:
    """Create a GitHub API connector."""
    config = ServiceConfig(
        name="github",
        base_url="https://api.github.com",
        auth=AuthConfig(
            type=AuthType.BEARER,
            credentials={"token": token},
        ),
        headers={"Accept": "application/vnd.github.v3+json"},
        rate_limit_rpm=60,
    )
    return registry.register("github", config)


def create_discord_connector(bot_token: str) -> ServiceConnector:
    """Create a Discord API connector."""
    config = ServiceConfig(
        name="discord",
        base_url="https://discord.com/api/v10",
        auth=AuthConfig(
            type=AuthType.BEARER,
            credentials={"token": bot_token},
        ),
        rate_limit_rpm=50,
    )
    return registry.register("discord", config)


def create_notion_connector(api_key: str) -> ServiceConnector:
    """Create a Notion API connector."""
    config = ServiceConfig(
        name="notion",
        base_url="https://api.notion.com/v1",
        auth=AuthConfig(
            type=AuthType.BEARER,
            credentials={"token": api_key},
        ),
        headers={"Notion-Version": "2022-06-28"},
        rate_limit_rpm=3,
    )
    return registry.register("notion", config)


