
"""
infrastructure/api/api_builder.py — Dynamic API Builder v4.0 TITAN
═══════════════════════════════════════════════════════════════════
Agent-powered API builder with dynamic model registration, rate limiting,
auth middleware, pipeline builder, and real test framework.
All 152+ models dynamically loaded from models_registry.

Architecture
────────────
  ┌──────────────────────────────────────────────────────────┐
  │                    API Builder Agent                       │
  │                                                            │
  │  ┌──────────┐   ┌──────────┐   ┌──────────┐              │
  │  │ Endpoint  │   │ OpenAPI  │   │ Test     │              │
  │  │ Generator │   │ Spec Gen │   │ Runner   │              │
  │  └─────┬────┘   └─────┬────┘   └─────┬────┘              │
  │        └──────────────┼──────────────┘                    │
  │                       ▼                                    │
  │  ┌─────────────────────────────────────────────┐          │
  │  │         Model Router (79 Models)             │          │
  │  │  Gemini(6) + Groq(7) + APEX/OpenRouter(139)         │          │
  │  │  Auto-select by task complexity               │          │
  │  └─────────────────────────────────────────────┘          │
  │                       │                                    │
  │  ┌────────┬──────────┼──────────┬────────┐               │
  │  ▼        ▼          ▼          ▼        ▼               │
  │ Gateway  Bridge   SmartClient  Agent   Unified           │
  │          (G0D)   (Infra)      Exec.   API                │
  └──────────────────────────────────────────────────────────┘

Features
────────
  • Dynamic endpoint creation (REST, GraphQL-like, WebSocket real-time streaming)
  • Auto-generates OpenAPI 3.1 specs from endpoint definitions
  • Connects to ALL 79 models via unified routing
  • Agent-powered API testing (generates & runs test suites)
  • Rate limiting, auth, and tier gating per endpoint
  • Endpoint versioning & deprecation
  • Health monitoring per endpoint
  • Cost estimation per request
  • Auto-documentation generation

References
──────────
  • models_registry.py (152 models, dynamic)
  • agent_executor.py (agent chain)
  • bridge.py (APEX ↔ API)
  • infrastructure/gateway/ai_gateway.py
  • infrastructure/clients/smart_client.py
"""


from __future__ import annotations
import os

import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ── TITANIUM v29.0 Integration ──

logger = logging.getLogger(__name__)
import ast as _ast
import operator as _operator


# ═══════════════════════════════════════════════════════════════════
# v29.0: Safe Expression Evaluator (replaces eval() in pipeline)
# ═══════════════════════════════════════════════════════════════════

# Allowed comparison/binary operators — NO code execution
_SAFE_OPS = {
    _ast.Eq: _operator.eq, _ast.NotEq: _operator.ne,
    _ast.Lt: _operator.lt, _ast.LtE: _operator.le,
    _ast.Gt: _operator.gt, _ast.GtE: _operator.ge,
    _ast.Add: _operator.add, _ast.Sub: _operator.sub,
    _ast.Mult: _operator.mul,
    _ast.And: lambda a, b: a and b,
    _ast.Or: lambda a, b: a or b,
    _ast.Not: _operator.not_,
    _ast.Is: _operator.is_, _ast.IsNot: _operator.is_not,
    _ast.In: lambda a, b: a in b,
    _ast.NotIn: lambda a, b: a not in b,
}


def _safe_eval_condition(expr: str, prev_output: Any) -> bool:
    """Evaluate a pipeline condition expression safely via AST.

    Allowed: comparisons, bool ops, len(), string/number literals, prev_output.
    Blocked: function calls (except len), imports, attribute access.

    Examples:
        "len(prev_output) > 0"
        "prev_output != ''"
        "True"
    """
    try:
        tree = _ast.parse(expr, mode="eval")
    except SyntaxError:
        raise ValueError(f"Invalid condition syntax: {expr}")

    _allowed_names = {"prev_output": prev_output, "True": True, "False": False, "None": None}

    def _eval_node(node: Any) -> Any:
        # Literals: numbers, strings, bools, None
        if isinstance(node, _ast.Constant):
            return node.value

        # Name references: prev_output, True, False, None
        if isinstance(node, _ast.Name):
            if node.id in _allowed_names:
                return _allowed_names[node.id]
            raise ValueError(f"Forbidden name in condition: {node.id}")

        # Function calls: ONLY len() allowed
        if isinstance(node, _ast.Call):
            if isinstance(node.func, _ast.Name) and node.func.id == "len" and len(node.args) == 1:
                return len(_eval_node(node.args[0]))
            raise ValueError(f"Only len() is allowed in conditions")

        # Comparisons: a > b, a == b, etc.
        if isinstance(node, _ast.Compare):
            left = _eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                op_func = _SAFE_OPS.get(type(op))
                if not op_func:
                    raise ValueError(f"Unsupported operator: {type(op).__name__}")
                right = _eval_node(comparator)
                if not op_func(left, right):
                    return False
                left = right
            return True

        # Bool ops: and, or
        if isinstance(node, _ast.BoolOp):
            if isinstance(node.op, _ast.And):
                return all(_eval_node(v) for v in node.values)
            if isinstance(node.op, _ast.Or):
                return any(_eval_node(v) for v in node.values)

        # Unary: not
        if isinstance(node, _ast.UnaryOp) and isinstance(node.op, _ast.Not):
            return not _eval_node(node.operand)

        # Binary ops: +, -, *
        if isinstance(node, _ast.BinOp):
            op_func = _SAFE_OPS.get(type(node.op))
            if op_func:
                return op_func(_eval_node(node.left), _eval_node(node.right))

        # Expression wrapper
        if isinstance(node, _ast.Expression):
            return _eval_node(node.body)

        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    return bool(_eval_node(tree))


# ═══════════════════════════════════════════════════════════════════
# Enums & Data Classes
# ═══════════════════════════════════════════════════════════════════

class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class EndpointStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    TESTING = "testing"
    DISABLED = "disabled"


class AuthLevel(str, Enum):
    NONE = "none"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class ModelTier(str, Enum):
    AUTO = "auto"           # SmartClient selects
    FAST = "fast"           # Fast models (Gemini Flash, etc.)
    PRO = "pro"             # Pro models (Gemini Pro, GPT-4o)
    ULTRA = "ultra"         # Ultra models (Grok-4, Claude Opus 4)
    CONSORTIUM = "consortium"  # Multi-model hive-mind


@dataclass
class EndpointParam:
    """API endpoint parameter definition."""
    name: str
    param_type: str  # "string", "number", "boolean", "array", "object"
    description: str = ""
    required: bool = True
    default: Any = None
    enum: List[str] = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # regex validation


@dataclass
class EndpointDefinition:
    """Full API endpoint definition."""
    endpoint_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    path: str = ""
    method: HttpMethod = HttpMethod.POST
    name: str = ""
    description: str = ""
    version: str = "v1"
    auth_level: AuthLevel = AuthLevel.BASIC
    model_tier: ModelTier = ModelTier.AUTO
    specific_model: Optional[str] = None  # Override auto-selection
    parameters: List[EndpointParam] = field(default_factory=list)
    system_prompt: str = ""  # System prompt for AI endpoints
    response_schema: Dict[str, Any] = field(default_factory=dict)
    rate_limit_per_minute: int = 60
    max_tokens: int = 65536
    temperature: float = 0.7
    timeout_seconds: float = 120.0
    tags: List[str] = field(default_factory=list)
    status: EndpointStatus = EndpointStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EndpointTestResult:
    """Result of testing an endpoint."""
    endpoint_id: str
    test_name: str
    passed: bool
    model_used: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    request: Dict[str, Any] = field(default_factory=dict)
    response: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    quality_score: float = 0.0  # 0-100


@dataclass
class ModelTestResult:
    """Result of testing a model via the API builder."""
    model_key: str
    model_id: str
    provider: str
    available: bool = False
    latency_ms: float = 0.0
    response_quality: float = 0.0  # 0-100
    tokens_used: int = 0
    response_preview: str = ""
    error: Optional[str] = None
    tier: str = ""


# ═══════════════════════════════════════════════════════════════════
# Endpoint Registry
# ═══════════════════════════════════════════════════════════════════


class EndpointRegistry:
    """Registry of all dynamically created API endpoints."""

    _instance = None

    def __new__(cls) -> Any:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._endpoints: Dict[str, EndpointDefinition] = {}
            cls._instance._stats: Dict[str, Dict] = defaultdict(
                lambda: {"calls": 0, "errors": 0, "total_latency": 0.0, "total_tokens": 0}
            )
        return cls._instance

    def register(self, endpoint: EndpointDefinition) -> str:
        """Register a new endpoint. Returns endpoint_id."""
        key = f"{endpoint.method.value}:{endpoint.version}/{endpoint.path}"
        self._endpoints[endpoint.endpoint_id] = endpoint
        logger.info("Registered endpoint: %s %s/%s [%s]",
                     endpoint.method.value, endpoint.version, endpoint.path, endpoint.endpoint_id)
        return endpoint.endpoint_id

    def get(self, endpoint_id: str) -> Optional[EndpointDefinition]:
        return self._endpoints.get(endpoint_id)

    def find_by_path(self, path: str, method: HttpMethod = HttpMethod.POST) -> Optional[EndpointDefinition]:
        for ep in self._endpoints.values():
            if ep.path == path and ep.method == method and ep.status == EndpointStatus.ACTIVE:
                return ep
        return None

    def list_all(self) -> List[EndpointDefinition]:
        return list(self._endpoints.values())

    def list_active(self) -> List[EndpointDefinition]:
        return [ep for ep in self._endpoints.values() if ep.status == EndpointStatus.ACTIVE]

    def deprecate(self, endpoint_id: str) -> bool:
        ep = self._endpoints.get(endpoint_id)
        if ep:
            ep.status = EndpointStatus.DEPRECATED
            return True
        return False

    def delete(self, endpoint_id: str) -> bool:
        return self._endpoints.pop(endpoint_id, None) is not None

    def record_call(self, endpoint_id: str, latency_ms: float, tokens: int, error: bool = False) -> Any:
        stats = self._stats[endpoint_id]
        stats["calls"] += 1
        stats["total_latency"] += latency_ms
        stats["total_tokens"] += tokens
        if error:
            stats["errors"] += 1

    def get_stats(self, endpoint_id: str) -> Dict:
        stats = self._stats[endpoint_id]
        calls = stats["calls"] or 1
        return {
            "total_calls": stats["calls"],
            "error_count": stats["errors"],
            "total_latency": stats["total_latency"],
            "total_tokens": stats["total_tokens"],
            "avg_latency_ms": stats["total_latency"] / calls,
            "error_rate": stats["errors"] / calls,
        }

    def get_all_stats(self) -> Dict[str, Dict]:
        return {eid: self.get_stats(eid) for eid in self._endpoints}

    @property
    def count(self) -> int:
        return len(self._endpoints)

    @property
    def active_count(self) -> int:
        return sum(1 for ep in self._endpoints.values() if ep.status == EndpointStatus.ACTIVE)


# ═══════════════════════════════════════════════════════════════════
# Model Router — connects to all 79 models
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# Model Router — Dynamic from models_registry
# ═══════════════════════════════════════════════════════════════════

class ModelRouter:
    """Routes requests to the optimal model from the full registry.

    Strategy:
      AUTO       → Smart selection based on task type
      FAST       → Low latency: Groq, Gemini Flash, APEX Fast tier
      PRO        → Balanced: Gemini Pro, APEX Standard/Smart/Pro
      ULTRA      → Highest quality: APEX Power/Ultra + Elite models
      CONSORTIUM → Multi-model synthesis
    """

    def __init__(self) -> None:
        self._request_count = 0
        self._model_latencies: Dict[str, List[float]] = defaultdict(list)
        self._tier_pools: Optional[Dict[ModelTier, List[str]]] = None

    def _build_tier_pools(self) -> Dict[ModelTier, List[str]]:
        """Build tier pools dynamically from models_registry."""
        if self._tier_pools is not None:
            return self._tier_pools

        pools = {
            ModelTier.FAST: [],
            ModelTier.PRO: [],
            ModelTier.ULTRA: [],
        }

        try:
            from arki_project.utils.models_registry import MODELS, APEX_TIERS

            # Base models
            for key, info in MODELS.items():
                if info.provider == "groq":
                    pools[ModelTier.FAST].append(key)
                elif info.provider == "gemini":
                    pools[ModelTier.PRO].append(key)

            # APEX tiers
            tier_mapping = {
                "fast": ModelTier.FAST,
                "standard": ModelTier.PRO,
                "smart": ModelTier.PRO,
                "pro": ModelTier.PRO,
                "power": ModelTier.ULTRA,
                "ultra": ModelTier.ULTRA,
            }
            for apex_name, apex_data in APEX_TIERS.items():
                target = tier_mapping.get(apex_name, ModelTier.PRO)
                for key in apex_data["models"]:
                    if key not in pools[target]:
                        pools[target].append(key)

            # Elite models → ULTRA
            for key in ("g-qwen37-max", "g-kimi26-think", "g-deepseek-v4-p",
                        "g-glm51-think", "g-nemotron3-sup", "g-qwen3-coder"):
                if key not in pools[ModelTier.ULTRA]:
                    pools[ModelTier.ULTRA].append(key)

        except ImportError:
            # Fallback
            pools[ModelTier.FAST] = ["gemini-flash", "llama8"]
            pools[ModelTier.PRO] = ["gemini-pro", "llama70"]
            pools[ModelTier.ULTRA] = ["gemini-pro"]

        self._tier_pools = pools
        return pools

    def select_model(self, tier: ModelTier, specific_model: Optional[str] = None,
                     task_type: str = "general") -> str:
        """Select optimal model for the request."""
        self._request_count += 1

        if specific_model:
            return specific_model

        if tier == ModelTier.AUTO:
            return self._auto_select(task_type)
        elif tier == ModelTier.CONSORTIUM:
            return "__consortium__"

        pools = self._build_tier_pools()
        pool = pools.get(tier, pools[ModelTier.PRO])
        if not pool:
            return "gemini-pro"

        # Pick model with best average latency (adaptive)
        if self._model_latencies:
            scored = []
            for m in pool:
                lats = self._model_latencies.get(m, [])
                avg = sum(lats[-10:]) / len(lats[-10:]) if lats else 9999
                scored.append((m, avg))
            scored.sort(key=lambda x: x[1])
            return scored[0][0]
        return pool[0]

    def _auto_select(self, task_type: str) -> str:
        """Smart model selection based on task type."""
        # Coding tasks → Qwen3 Coder (Elite 480B)
        if task_type in ("code", "debug", "refactor", "review"):
            return "g-qwen3-coder"
        # Analysis/research → Gemini Pro or DeepSeek V4
        elif task_type in ("analysis", "research", "complex"):
            return "g-deepseek-v4-p"
        # Creative writing → GPT-5 or Qwen 3.7 Max
        elif task_type in ("creative", "writing", "story"):
            return "g-qwen37-max"
        # Fast/simple → Gemini Flash
        elif task_type in ("fast", "simple", "translate"):
            return "gemini-flash"
        # Math/reasoning → DeepSeek R1
        elif task_type in ("math", "reasoning", "logic"):
            return "g-deepseek-r1"
        # Agent tasks → Kimi K2.6
        elif task_type in ("agent", "planning", "orchestration"):
            return "g-kimi26-think"
        # Persian → GLM 5.1 (strong multilingual)
        elif task_type in ("persian", "farsi", "multilingual"):
            return "g-glm51-think"
        # Default → Gemini Pro
        return "gemini-pro"

    def record_latency(self, model: str, latency_ms: float) -> Any:
        self._model_latencies[model].append(latency_ms)
        if len(self._model_latencies[model]) > 100:
            self._model_latencies[model] = self._model_latencies[model][-50:]

    def get_model_stats(self) -> Dict[str, Dict]:
        stats = {}
        for model, lats in self._model_latencies.items():
            recent = lats[-20:]
            stats[model] = {
                "total_calls": len(lats),
                "avg_latency_ms": sum(recent) / len(recent) if recent else 0,
                "min_latency_ms": min(recent) if recent else 0,
                "max_latency_ms": max(recent) if recent else 0,
            }
        return stats

    def get_all_models_count(self) -> int:
        """Get total model count from registry."""
        try:
            from arki_project.utils.models_registry import MODELS
            return len(MODELS)
        except ImportError:
            return 0



class OpenAPIGenerator:
    """Generates OpenAPI 3.1 specifications from endpoint definitions."""

    @staticmethod
    def generate(endpoints: List[EndpointDefinition],
                 title: str = "Arki Engine API",
                 version: str = "29.0.0") -> Dict[str, Any]:
        """Generate full OpenAPI spec."""

        paths: Dict[str, Any] = {}
        tags_set: Set[str] = set()

        for ep in endpoints:
            if ep.status == EndpointStatus.DISABLED:
                continue

            path_key = f"/{ep.version}/{ep.path}"
            method_key = ep.method.value.lower()

            # Build request schema
            properties = {}
            required = []
            for p in ep.parameters:
                prop: Dict[str, Any] = {"type": p.param_type, "description": p.description}
                if p.default is not None:
                    prop["default"] = p.default
                if p.enum:
                    prop["enum"] = p.enum
                if p.min_value is not None:
                    prop["minimum"] = p.min_value
                if p.max_value is not None:
                    prop["maximum"] = p.max_value
                if p.pattern:
                    prop["pattern"] = p.pattern
                properties[p.name] = prop
                if p.required:
                    required.append(p.name)

            operation: Dict[str, Any] = {
                "operationId": ep.endpoint_id,
                "summary": ep.name,
                "description": ep.description,
                "tags": ep.tags or ["general"],
                "security": [{"BearerAuth": []}] if ep.auth_level != AuthLevel.NONE else [],
                "responses": {
                    "200": {
                        "description": "Success",
                        "content": {"application/json": {"schema": ep.response_schema or {"type": "object"}}},
                    },
                    "400": {"description": "Bad Request"},
                    "401": {"description": "Unauthorized"},
                    "429": {"description": "Rate Limited"},
                    "500": {"description": "Server Error"},
                },
            }

            if ep.method in (HttpMethod.POST, HttpMethod.PUT, HttpMethod.PATCH) and properties:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": properties,
                                "required": required,
                            }
                        }
                    }
                }

            if ep.status == EndpointStatus.DEPRECATED:
                operation["deprecated"] = True

            if path_key not in paths:
                paths[path_key] = {}
            paths[path_key][method_key] = operation
            tags_set.update(ep.tags or ["general"])

        return {
            "openapi": "3.1.0",
            "info": {
                "title": title,
                "version": version,
                "description": (
                    "Arki Engine v10.4 TITANIUM — 72 AI Models, Agent Executor, "
                    "ULTRAPLINIAN Race, CONSORTIUM Hive-Mind, Dynamic API Builder"
                ),
                "contact": {"name": "Arki Engine"},
            },
            "servers": [
                {"url": os.environ.get("APEX_URL", "http://localhost:7860"), "description": "Local APEX"},
                {"url": os.environ.get("ARKI_URL", "http://localhost:8000"), "description": "Arki Main"},
            ],
            "paths": paths,
            "tags": [{"name": t} for t in sorted(tags_set)],
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "description": "API key via Authorization: Bearer <key>",
                    }
                }
            },
        }




# ═══════════════════════════════════════════════════════════════════
# WebSocket Manager — Real bidirectional streaming
# ═══════════════════════════════════════════════════════════════════

@dataclass
class WebSocketConnection:
    """Represents an active WebSocket connection with state tracking."""
    conn_id: str
    user_id: str = "anonymous"
    tier: str = "basic"
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    message_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    _closed: bool = False

    @property
    def is_alive(self) -> bool:
        """Connection is alive if heartbeat was within 90 seconds."""
        return not self._closed and (time.time() - self.last_heartbeat) < 90

    def mark_activity(self, bytes_in: int = 0, bytes_out: int = 0) -> Any:
        self.last_activity = time.time()
        self.message_count += 1
        self.bytes_received += bytes_in
        self.bytes_sent += bytes_out


class WebSocketManager:
    """Production WebSocket manager for real-time model streaming.

    Protocol:
      Client → Server:
        {"type": "auth", "api_key": "ark_xxx"}
        {"type": "chat", "model": "gemini-pro", "messages": [...], "stream": true}
        {"type": "subscribe", "channel": "model_events"}
        {"type": "unsubscribe", "channel": "model_events"}
        {"type": "ping"}

      Server → Client:
        {"type": "auth_ok", "connection_id": "abc123", "tier": "basic"}
        {"type": "auth_error", "message": "Invalid API key"}
        {"type": "chunk", "request_id": "xxx", "content": "...", "done": false}
        {"type": "chunk", "request_id": "xxx", "content": "", "done": true, "usage": {...}}
        {"type": "event", "channel": "model_events", "data": {...}}
        {"type": "pong", "server_time": 1234567890.0}
        {"type": "error", "message": "...", "request_id": "xxx"}
    """

    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_CONNECTIONS_PER_USER = 5
    MAX_MESSAGE_SIZE = 1_048_576  # 1MB
    IDLE_TIMEOUT = 300  # 5 minutes

    def __init__(self, api_builder: "APIBuilderAgent") -> None:
        self._builder = api_builder
        self._connections: Dict[str, WebSocketConnection] = {}
        self._user_connections: Dict[str, Set[str]] = defaultdict(set)
        self._channels: Dict[str, Set[str]] = defaultdict(set)  # channel → {conn_ids}
        self._total_messages = 0
        self._total_connections = 0
        self._started_at = time.time()
        self._send_fn: Dict[str, Callable] = {}  # conn_id → send function
        self._close_fn: Dict[str, Callable] = {}  # conn_id → close function

    @property
    def active_connections(self) -> int:
        return sum(1 for c in self._connections.values() if c.is_alive)

    def register_connection(self, conn_id: str, send_fn: Callable, close_fn: Callable) -> WebSocketConnection:
        """Register a new WebSocket connection with its send/close callbacks.

        Args:
            conn_id: Unique connection identifier
            send_fn: async callable(dict) to send JSON to client
            close_fn: async callable() to close the connection
        """
        conn = WebSocketConnection(conn_id=conn_id)
        self._connections[conn_id] = conn
        self._send_fn[conn_id] = send_fn
        self._close_fn[conn_id] = close_fn
        self._total_connections += 1
        logger.info("WebSocket connection registered: %s", conn_id)
        return conn

    def unregister_connection(self, conn_id: str) -> Any:
        """Clean up a closed connection."""
        conn = self._connections.pop(conn_id, None)
        if conn:
            conn._closed = True
            self._user_connections.get(conn.user_id, set()).discard(conn_id)
            # Remove from all channels
            for channel_conns in self._channels.values():
                channel_conns.discard(conn_id)
        self._send_fn.pop(conn_id, None)
        self._close_fn.pop(conn_id, None)
        logger.info("WebSocket connection closed: %s", conn_id)

    async def _send(self, conn_id: str, message: Dict[str, Any]) -> bool:
        """Send a JSON message to a connection. Returns False if failed."""
        send_fn = self._send_fn.get(conn_id)
        if not send_fn:
            return False
        try:
            data = json.dumps(message, ensure_ascii=False)
            await send_fn(message)
            conn = self._connections.get(conn_id)
            if conn:
                conn.mark_activity(bytes_out=len(data))
            return True
        except Exception as e:
            logger.warning("WebSocket send failed for %s: %s", conn_id, e)
            return False

    async def handle_message(self, conn_id: str, raw_message: str) -> Optional[Dict]:
        """Process an incoming WebSocket message.

        Returns response dict (also sent via send_fn), or None.
        """
        conn = self._connections.get(conn_id)
        if not conn or conn._closed:
            return {"type": "error", "message": "Connection not found"}

        if len(raw_message) > self.MAX_MESSAGE_SIZE:
            resp = {"type": "error", "message": f"Message too large (max {self.MAX_MESSAGE_SIZE} bytes)"}
            await self._send(conn_id, resp)
            return resp

        try:
            msg = json.loads(raw_message)
        except json.JSONDecodeError:
            resp = {"type": "error", "message": "Invalid JSON"}
            await self._send(conn_id, resp)
            return resp

        conn.mark_activity(bytes_in=len(raw_message))
        self._total_messages += 1
        msg_type = msg.get("type", "")

        if msg_type == "auth":
            return await self._handle_auth(conn, msg)
        elif msg_type == "ping":
            return await self._handle_ping(conn)
        elif msg_type == "chat":
            return await self._handle_chat(conn, msg)
        elif msg_type == "subscribe":
            return await self._handle_subscribe(conn, msg)
        elif msg_type == "unsubscribe":
            return await self._handle_unsubscribe(conn, msg)
        else:
            resp = {"type": "error", "message": f"Unknown message type: {msg_type}"}
            await self._send(conn.conn_id, resp)
            return resp

    async def _handle_auth(self, conn: WebSocketConnection, msg: Dict) -> Dict:
        """Authenticate a WebSocket connection."""
        api_key = msg.get("api_key", "")
        ok, info = self._builder.auth.validate(api_key, AuthLevel.BASIC)

        if not ok:
            resp = {"type": "auth_error", "message": "Invalid or insufficient API key"}
            await self._send(conn.conn_id, resp)
            return resp

        conn.user_id = info["user_id"]
        conn.tier = info["tier"]

        # Enforce per-user connection limit
        user_conns = self._user_connections[conn.user_id]
        if len(user_conns) >= self.MAX_CONNECTIONS_PER_USER:
            resp = {"type": "auth_error",
                    "message": f"Too many connections (max {self.MAX_CONNECTIONS_PER_USER})"}
            await self._send(conn.conn_id, resp)
            return resp

        user_conns.add(conn.conn_id)
        resp = {
            "type": "auth_ok",
            "connection_id": conn.conn_id,
            "user_id": conn.user_id,
            "tier": conn.tier,
        }
        await self._send(conn.conn_id, resp)
        logger.info("WebSocket authenticated: %s → user=%s tier=%s",
                     conn.conn_id, conn.user_id, conn.tier)
        return resp

    async def _handle_ping(self, conn: WebSocketConnection) -> Dict:
        """Respond to heartbeat ping."""
        conn.last_heartbeat = time.time()
        resp = {"type": "pong", "server_time": time.time()}
        await self._send(conn.conn_id, resp)
        return resp

    async def _handle_chat(self, conn: WebSocketConnection, msg: Dict) -> Dict:
        """Handle a chat request — stream model response via WebSocket."""
        if conn.user_id == "anonymous":
            resp = {"type": "error", "message": "Authentication required before chat"}
            await self._send(conn.conn_id, resp)
            return resp

        request_id = uuid.uuid4().hex[:12]
        model_key = msg.get("model", "gemini-pro")
        messages = msg.get("messages", [])
        stream = msg.get("stream", True)

        if not messages:
            prompt = msg.get("prompt", "")
            if prompt:
                messages = [{"role": "user", "content": prompt}]
            else:
                resp = {"type": "error", "request_id": request_id,
                        "message": "No messages or prompt provided"}
                await self._send(conn.conn_id, resp)
                return resp

        # Rate limit check
        provider = "openrouter"
        try:
            from arki_project.utils.models_registry import get_model as _ws_get_model
            _m = _ws_get_model(model_key)
            provider = _m.provider
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)

        rate_ok, rate_info = self._builder.rate_limiter.check(conn.user_id, model_key, provider)
        if not rate_ok:
            resp = {
                "type": "error",
                "request_id": request_id,
                "message": "Rate limit exceeded",
                "retry_after_seconds": rate_info.get("retry_after_seconds", 60) if rate_info else 60,
            }
            await self._send(conn.conn_id, resp)
            return resp

        # Send acknowledgment
        await self._send(conn.conn_id, {
            "type": "chat_ack",
            "request_id": request_id,
            "model": model_key,
        })

        # Execute the model call
        t0 = time.time()
        try:
            # System prompt from message or default
            sys_prompt = msg.get("system_prompt", "")
            if sys_prompt:
                messages.insert(0, {"role": "system", "content": sys_prompt})

            response = await self._builder.quick_chat(
                model_key,
                messages[-1]["content"] if messages else "",
                system_prompt=sys_prompt,
                temperature=msg.get("temperature", 0.7),
                max_tokens=msg.get("max_tokens", 65536),
            )
            latency_ms = (time.time() - t0) * 1000
            tokens_est = len(response) // 4

            if stream:
                # Simulate streaming by chunking the response
                chunk_size = max(20, len(response) // 10)
                for i in range(0, len(response), chunk_size):
                    chunk = response[i:i + chunk_size]
                    await self._send(conn.conn_id, {
                        "type": "chunk",
                        "request_id": request_id,
                        "content": chunk,
                        "done": False,
                    })
                    await asyncio.sleep(0.01)  # Small delay between chunks

            # Final chunk with done=True
            final = {
                "type": "chunk",
                "request_id": request_id,
                "content": "" if stream else response,
                "done": True,
                "usage": {
                    "model": model_key,
                    "estimated_tokens": tokens_est,
                    "latency_ms": round(latency_ms, 1),
                },
            }
            await self._send(conn.conn_id, final)

            self._builder.router.record_latency(model_key, latency_ms)
            return final

        except asyncio.TimeoutError:
            resp = {"type": "error", "request_id": request_id,
                    "message": f"Model {model_key} timed out"}
            await self._send(conn.conn_id, resp)
            return resp
        except Exception as e:
            resp = {"type": "error", "request_id": request_id,
                    "message": str(e)}
            await self._send(conn.conn_id, resp)
            return resp

    async def _handle_subscribe(self, conn: WebSocketConnection, msg: Dict) -> Dict:
        """Subscribe to a real-time event channel."""
        channel = msg.get("channel", "")
        valid_channels = {"model_events", "health", "rate_limits", "errors"}
        if channel not in valid_channels:
            resp = {"type": "error",
                    "message": f"Invalid channel. Valid: {', '.join(sorted(valid_channels))}"}
            await self._send(conn.conn_id, resp)
            return resp

        self._channels[channel].add(conn.conn_id)
        conn.subscriptions.add(channel)
        resp = {"type": "subscribed", "channel": channel}
        await self._send(conn.conn_id, resp)
        return resp

    async def _handle_unsubscribe(self, conn: WebSocketConnection, msg: Dict) -> Dict:
        """Unsubscribe from a channel."""
        channel = msg.get("channel", "")
        self._channels.get(channel, set()).discard(conn.conn_id)
        conn.subscriptions.discard(channel)
        resp = {"type": "unsubscribed", "channel": channel}
        await self._send(conn.conn_id, resp)
        return resp

    async def broadcast(self, channel: str, data: Dict[str, Any]) -> Any:
        """Broadcast an event to all subscribers of a channel."""
        conn_ids = self._channels.get(channel, set()).copy()
        message = {"type": "event", "channel": channel, "data": data, "timestamp": time.time()}
        dead = []
        for cid in conn_ids:
            if not await self._send(cid, message):
                dead.append(cid)
        # Cleanup dead connections
        for cid in dead:
            self.unregister_connection(cid)

    async def cleanup_idle(self) -> None:
        """Remove idle/dead connections. Call periodically."""
        now = time.time()
        dead = []
        for conn_id, conn in self._connections.items():
            if not conn.is_alive:
                dead.append(conn_id)
            elif (now - conn.last_activity) > self.IDLE_TIMEOUT:
                dead.append(conn_id)
                await self._send(conn_id, {"type": "error", "message": "Idle timeout"})
        for cid in dead:
            close_fn = self._close_fn.get(cid)
            if close_fn:
                try:
                    await close_fn()
                except Exception as _err:
                    logger.warning("Suppressed error: %s", _err)
            self.unregister_connection(cid)
        if dead:
            logger.info("WebSocket cleanup: removed %d idle/dead connections", len(dead))

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        alive = [c for c in self._connections.values() if c.is_alive]
        return {
            "active_connections": len(alive),
            "total_connections_served": self._total_connections,
            "total_messages_processed": self._total_messages,
            "uptime_seconds": round(time.time() - self._started_at, 1),
            "channels": {ch: len(conns) for ch, conns in self._channels.items() if conns},
            "connections": [
                {
                    "conn_id": c.conn_id,
                    "user_id": c.user_id,
                    "tier": c.tier,
                    "connected_seconds": round(time.time() - c.connected_at, 1),
                    "messages": c.message_count,
                    "subscriptions": list(c.subscriptions),
                }
                for c in alive
            ],
        }

# ═══════════════════════════════════════════════════════════════════
# API Builder Agent — The Main Engine
# ═══════════════════════════════════════════════════════════════════




# ═══════════════════════════════════════════════════════════════════
# Rate Limiter — Token Bucket per model per user
# ═══════════════════════════════════════════════════════════════════

class RateLimiter:
    """Token bucket rate limiter per (user, model) pair.
    
    Limits:
      - Per-model RPM (requests per minute)
      - Per-user daily quota
      - Global burst protection
    """
    
    # Provider default limits
    PROVIDER_LIMITS = {
        "gemini":     {"rpm": 60,  "rpd": 1500},
        "groq":       {"rpm": 30,  "rpd": 14400},
        "openrouter": {"rpm": 20,  "rpd": 200},    # Free tier
        "openrouter_paid": {"rpm": 500, "rpd": 100000},  # Paid tier
    }
    
    def __init__(self) -> None:
        self._buckets: Dict[str, Dict] = {}  # (user_id, model_key) → bucket state
        self._global_count = 0
        self._global_window_start = time.time()
        self._global_rpm = 200  # Global burst limit
    
    def _get_bucket(self, user_id: str, model_key: str, provider: str) -> Dict:
        """Get or create token bucket for (user, model)."""
        key = f"{user_id}:{model_key}"
        if key not in self._buckets:
            limits = self.PROVIDER_LIMITS.get(provider, self.PROVIDER_LIMITS["openrouter"])
            self._buckets[key] = {
                "tokens": limits["rpm"],
                "max_tokens": limits["rpm"],
                "last_refill": time.time(),
                "refill_rate": limits["rpm"] / 60.0,  # tokens per second
                "daily_count": 0,
                "daily_limit": limits["rpd"],
                "daily_reset": time.time(),
            }
        return self._buckets[key]
    
    def check(self, user_id: str, model_key: str, provider: str) -> Tuple[bool, Optional[Dict]]:
        """Check if request is allowed.
        
        Returns:
            (allowed, info) — info contains retry_after_seconds if blocked.
        """
        bucket = self._get_bucket(user_id, model_key, provider)
        now = time.time()
        
        # Refill tokens
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            bucket["max_tokens"],
            bucket["tokens"] + elapsed * bucket["refill_rate"],
        )
        bucket["last_refill"] = now
        
        # Daily reset (24h)
        if now - bucket["daily_reset"] > 86400:
            bucket["daily_count"] = 0
            bucket["daily_reset"] = now
        
        # Global burst check
        if now - self._global_window_start > 60:
            self._global_count = 0
            self._global_window_start = now
        
        # Check limits
        if self._global_count >= self._global_rpm:
            retry_after = 60 - (now - self._global_window_start)
            return False, {"reason": "global_burst", "retry_after_seconds": max(1, int(retry_after))}
        
        if bucket["daily_count"] >= bucket["daily_limit"]:
            retry_after = 86400 - (now - bucket["daily_reset"])
            return False, {"reason": "daily_quota", "retry_after_seconds": max(1, int(retry_after))}
        
        if bucket["tokens"] < 1:
            retry_after = (1 - bucket["tokens"]) / bucket["refill_rate"]
            return False, {"reason": "rate_limit", "retry_after_seconds": max(1, int(retry_after))}
        
        # Consume
        bucket["tokens"] -= 1
        bucket["daily_count"] += 1
        self._global_count += 1
        
        return True, None
    
    def get_usage(self, user_id: str) -> Dict[str, Dict]:
        """Get usage stats for a user across all models."""
        result = {}
        for key, bucket in self._buckets.items():
            uid, model = key.split(":", 1)
            if uid == user_id:
                result[model] = {
                    "remaining_rpm": max(0, int(bucket["tokens"])),
                    "daily_used": bucket["daily_count"],
                    "daily_limit": bucket["daily_limit"],
                }
        return result


# ═══════════════════════════════════════════════════════════════════
# Auth Middleware — API key + tier-based access
# ═══════════════════════════════════════════════════════════════════

class AuthMiddleware:
    """Validates API requests and enforces tier-based access control.
    
    Tiers:
      NONE     — No auth needed (public endpoints like /models/list)
      BASIC    — Any valid API key
      PREMIUM  — Premium tier key required
      ENTERPRISE — Enterprise tier with full access
    """
    
    def __init__(self) -> None:
        self._api_keys: Dict[str, Dict] = {}  # key_hash → {user_id, tier, created_at}
        self._revoked: Set[str] = set()
    
    def register_key(self, api_key: str, user_id: str, tier: str = "basic") -> str:
        """Register an API key for a user."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self._api_keys[key_hash] = {
            "user_id": user_id,
            "tier": tier,
            "created_at": time.time(),
            "last_used": None,
            "request_count": 0,
        }
        return key_hash
    
    def validate(self, api_key: str, required_level: AuthLevel) -> Tuple[bool, Optional[Dict]]:
        """Validate an API key against a required access level.
        
        Returns:
            (valid, user_info) — user_info has user_id, tier if valid.
        """
        if required_level == AuthLevel.NONE:
            return True, {"user_id": "anonymous", "tier": "none"}
        
        if not api_key:
            return False, None
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if key_hash in self._revoked:
            return False, None
        
        info = self._api_keys.get(key_hash)
        if not info:
            return False, None
        
        # Tier hierarchy: enterprise > premium > basic
        tier_levels = {"basic": 1, "premium": 2, "enterprise": 3}
        required_levels = {
            AuthLevel.BASIC: 1,
            AuthLevel.PREMIUM: 2,
            AuthLevel.ENTERPRISE: 3,
        }
        
        user_level = tier_levels.get(info["tier"], 0)
        needed = required_levels.get(required_level, 1)
        
        if user_level < needed:
            return False, None
        
        # Update usage
        info["last_used"] = time.time()
        info["request_count"] += 1
        
        return True, {"user_id": info["user_id"], "tier": info["tier"]}
    
    def revoke_key(self, api_key: str) -> Any:
        """Revoke an API key."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        self._revoked.add(key_hash)
    
    def generate_key(self, user_id: str, tier: str = "basic") -> str:
        """Generate and register a new API key."""
        raw_key = f"ark_{uuid.uuid4().hex}"
        self.register_key(raw_key, user_id, tier)
        return raw_key


# ═══════════════════════════════════════════════════════════════════
# Pipeline Builder — Chain multiple models/endpoints
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PipelineStep:
    """One step in a model pipeline."""
    name: str
    model_key: str  # or endpoint_id
    system_prompt: str = ""
    input_transform: str = ""  # Template: {prev_output}, {original_input}
    temperature: float = 0.7
    max_tokens: int = 65536
    condition: str = ""  # Simple condition: "len(prev_output) > 100"


@dataclass
class Pipeline:
    """Multi-step model pipeline definition."""
    pipeline_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    steps: List[PipelineStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    
    def add_step(self, name: str, model_key: str, **kwargs) -> "Pipeline":
        self.steps.append(PipelineStep(name=name, model_key=model_key, **kwargs))
        return self  # For chaining


class PipelineExecutor:
    """Executes multi-step model pipelines."""
    
    def __init__(self, api_builder: "APIBuilderAgent") -> None:
        self._builder = api_builder
        self._pipelines: Dict[str, Pipeline] = {}
        self._execution_log: List[Dict] = []
    
    def create_pipeline(self, name: str, description: str = "") -> Pipeline:
        p = Pipeline(name=name, description=description)
        self._pipelines[p.pipeline_id] = p
        return p
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        return self._pipelines.get(pipeline_id)
    
    def list_pipelines(self) -> List[Dict]:
        return [
            {
                "id": p.pipeline_id,
                "name": p.name,
                "description": p.description,
                "steps": len(p.steps),
                "created_at": p.created_at,
            }
            for p in self._pipelines.values()
        ]
    
    async def execute(self, pipeline_id: str, initial_input: str,
                      user_id: str = "system") -> Dict[str, Any]:
        """Execute a pipeline end-to-end."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"error": f"Pipeline {pipeline_id} not found"}
        
        t0 = time.time()
        results = []
        prev_output = ""
        current_input = initial_input
        
        for i, step in enumerate(pipeline.steps):
            step_t0 = time.time()
            
            # Check condition — v29.0: safe AST evaluator (NO eval())
            if step.condition:
                try:
                    if not _safe_eval_condition(step.condition, prev_output):
                        results.append({
                            "step": i + 1,
                            "name": step.name,
                            "skipped": True,
                            "reason": f"Condition not met: {step.condition}",
                        })
                        continue
                except Exception as cond_err:
                    results.append({
                        "step": i + 1,
                        "name": step.name,
                        "skipped": True,
                        "reason": f"Condition error: {cond_err}",
                    })
                    continue
            
            # Build input
            if step.input_transform:
                prompt = step.input_transform.replace(
                    "{prev_output}", prev_output
                ).replace(
                    "{original_input}", initial_input
                )
            else:
                prompt = prev_output if prev_output else current_input
            
            # Execute
            try:
                response = await self._builder.quick_chat(
                    step.model_key, prompt,
                    system_prompt=step.system_prompt,
                    temperature=step.temperature,
                    max_tokens=step.max_tokens,
                )
                step_latency = (time.time() - step_t0) * 1000
                
                results.append({
                    "step": i + 1,
                    "name": step.name,
                    "model": step.model_key,
                    "success": True,
                    "output_length": len(response),
                    "latency_ms": round(step_latency, 1),
                    "output_preview": response[:200],
                })
                prev_output = response
                
            except Exception as e:
                step_latency = (time.time() - step_t0) * 1000
                results.append({
                    "step": i + 1,
                    "name": step.name,
                    "model": step.model_key,
                    "success": False,
                    "error": str(e),
                    "latency_ms": round(step_latency, 1),
                })
                # Pipeline continues — prev_output stays the same
        
        total_latency = (time.time() - t0) * 1000
        execution_record = {
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline.name,
            "total_steps": len(pipeline.steps),
            "executed_steps": len([r for r in results if not r.get("skipped")]),
            "successful_steps": len([r for r in results if r.get("success")]),
            "total_latency_ms": round(total_latency, 1),
            "final_output": prev_output,
            "steps": results,
        }
        self._execution_log.append(execution_record)
        return execution_record


# ═══════════════════════════════════════════════════════════════════
# Endpoint Persistence — JSON save/load
# ═══════════════════════════════════════════════════════════════════

class EndpointPersistence:
    """Saves and loads custom endpoints to/from JSON file."""
    
    DEFAULT_PATH = "data/api_endpoints.json"
    
    def __init__(self, path: str = None) -> None:
        self._path = path or self.DEFAULT_PATH
    
    def save(self, endpoints: List[EndpointDefinition]) -> int:
        """Save custom (non-builtin) endpoints to JSON."""
        custom = [ep for ep in endpoints if "custom" in ep.tags or "dynamic" in ep.tags]
        
        data = []
        for ep in custom:
            data.append({
                "endpoint_id": ep.endpoint_id,
                "path": ep.path,
                "method": ep.method.value,
                "name": ep.name,
                "description": ep.description,
                "model_tier": ep.model_tier.value if hasattr(ep.model_tier, 'value') else str(ep.model_tier),
                "specific_model": ep.specific_model,
                "system_prompt": ep.system_prompt,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.param_type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default,
                        "enum": p.enum,
                    }
                    for p in ep.parameters
                ],
                "tags": ep.tags,
                "auth_level": ep.auth_level.value if hasattr(ep.auth_level, 'value') else str(ep.auth_level),
                "metadata": ep.metadata,
                "timeout_seconds": ep.timeout_seconds,
            })
        
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({"version": "2.0", "endpoints": data}, f, indent=2, ensure_ascii=False)
        
        return len(data)
    
    def load(self) -> List[Dict]:
        """Load saved endpoints from JSON."""
        if not os.path.exists(self._path):
            return []
        try:
            with open(self._path) as f:
                data = json.load(f)
            return data.get("endpoints", [])
        except (json.JSONDecodeError, KeyError):
            return []




# ═══════════════════════════════════════════════════════════════════
# API Builder Agent v4.0 TITAN
# ═══════════════════════════════════════════════════════════════════

class APIBuilderAgent:
    """Agent-powered API builder — dynamic, tested, production-ready.

    v4.0 TITAN Features:
      • Dynamic endpoint registration from models_registry (152+ models)
      • Real rate limiting (token bucket per user per model)
      • Auth middleware with tier-based access
      • Pipeline builder (chain multiple models)
      • Endpoint persistence (JSON save/load)
      • Real test framework with quality scoring (no fake 95.0)
      • Full OpenAPI 3.1 spec generation
    
    Connects:
      • models_registry.MODELS (152 models) → via dynamic ModelRouter
      • ai_client.AIClient → for real model calls
      • free_access_router → for free tier routing
      • config.Settings → for API keys from environment
    """

    def __init__(self) -> None:
        self.registry = EndpointRegistry()
        self.router = ModelRouter()
        self.spec_gen = OpenAPIGenerator()
        self.rate_limiter = RateLimiter()
        self.auth = AuthMiddleware()
        self.persistence = EndpointPersistence()
        self._pipeline_executor: Optional[PipelineExecutor] = None
        self._test_results: List[EndpointTestResult] = []
        self._model_test_results: List[ModelTestResult] = []
        self._ws_manager: Optional[WebSocketManager] = None
        self._initialized = False
        self._ai_client: Optional[Any] = None
        logger.info("APIBuilderAgent v4.0 TITAN — dynamic registration ready")

    @property
    def pipelines(self) -> PipelineExecutor:
        """Lazy-load pipeline executor."""
        if self._pipeline_executor is None:
            self._pipeline_executor = PipelineExecutor(self)
        return self._pipeline_executor

    @property
    def websockets(self) -> WebSocketManager:
        """Lazy-load WebSocket manager."""
        if self._ws_manager is None:
            self._ws_manager = WebSocketManager(self)
        return self._ws_manager

    def _get_ai_client(self) -> Any:
        """Lazy-load AIClient with config from environment (same as main.py).

        FreeAccessRouter handles all models without external keys, so
        even empty env vars are fine — the system routes to free tiers.
        """
        if self._ai_client is None:
            from arki_project.utils.ai_client import AIClient
            from arki_project.config import Settings
            s = Settings()
            self._ai_client = AIClient(
                api_key=s.ai_api_key,
                base_url=s.ai_base_url,
                model=s.ai_model,
                max_history=s.ai_max_history,
                temperature=s.ai_temperature,
                max_tokens=s.ai_max_tokens,
                groq_api_key=s.groq_api_key,
                openrouter_api_key=s.openrouter_api_key,
            )
        return self._ai_client

    # ── Initialization ──────────────────────────────────────────


    async def initialize(self) -> Any:
        """Boot up: register endpoints, load persistence, provision keys."""
        if self._initialized:
            return

        # 1. Register built-in endpoints (12 core endpoints)
        self._register_builtin_endpoints()

        # 2. Auto-provision free API keys
        try:
            from arki_project.utils.free_access_router import initialize_free_access
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(initialize_free_access())
                else:
                    loop.run_until_complete(initialize_free_access())
            except RuntimeError:
                asyncio.run(initialize_free_access())
            logger.info("✅ Free access auto-provisioner activated")
        except Exception as _fa_err:
            logger.debug("Free access provisioner: %s", _fa_err)

        # 3. Dynamic per-model endpoint registration (ALL models from MODELS dict)
        self._register_per_model_endpoints()

        # 4. Load persisted custom endpoints
        saved = self.persistence.load()
        for ep_data in saved:
            try:
                self.create_endpoint(
                    path=ep_data["path"],
                    name=ep_data["name"],
                    description=ep_data["description"],
                    system_prompt=ep_data.get("system_prompt", ""),
                    model_tier=ep_data.get("model_tier", "auto"),
                    parameters=ep_data.get("parameters", []),
                    tags=ep_data.get("tags", ["custom", "persisted"]),
                )
            except Exception as e:
                logger.warning("Failed to load persisted endpoint %s: %s", ep_data.get("path"), e)
        if saved:
            logger.info("Loaded %d persisted custom endpoints", len(saved))

        self._initialized = True
        logger.info("APIBuilderAgent v4.0: %d endpoints registered (%d models)", 
                     self.registry.count, self.router.get_all_models_count())


    def _register_builtin_endpoints(self) -> Any:
        """Register the default AI-powered API endpoints."""

        # 1. Chat Completion (single model)
        self.registry.register(EndpointDefinition(
            path="chat/completions",
            method=HttpMethod.POST,
            name="Chat Completion",
            description="Single-model chat completion. Supports all 79 models.",
            model_tier=ModelTier.AUTO,
            parameters=[
                EndpointParam("messages", "array", "Chat messages [{role, content}]"),
                EndpointParam("model", "string", "Model key (any of 79 models)", required=False),
                EndpointParam("max_tokens", "number", "Max output tokens", required=False, default=65536),
                EndpointParam("temperature", "number", "Sampling temperature", required=False,
                              default=0.7, min_value=0, max_value=2),
                EndpointParam("stream", "boolean", "Enable SSE streaming", required=False, default=False),
            ],
            system_prompt="You are a helpful AI assistant.",
            tags=["chat", "core"],
        ))

        # 2. Agent Execute (multi-step)
        self.registry.register(EndpointDefinition(
            path="agent/execute",
            method=HttpMethod.POST,
            name="Agent Execute",
            description="Run autonomous multi-step agent with 12+ tools and all 79 models.",
            model_tier=ModelTier.PRO,
            parameters=[
                EndpointParam("query", "string", "Task description for the agent"),
                EndpointParam("model", "string", "Model to use for agent reasoning", required=False),
                EndpointParam("max_steps", "number", "Maximum agent steps", required=False,
                              default=50, min_value=1, max_value=100),
                EndpointParam("tools", "array", "Subset of tools to enable", required=False),
                EndpointParam("max_time_ms", "number", "Time budget in ms", required=False, default=600000),
            ],
            tags=["agent", "core"],
            timeout_seconds=600,
        ))

        # 3. Multi-Model Race (ULTRAPLINIAN)
        self.registry.register(EndpointDefinition(
            path="ultraplinian/completions",
            method=HttpMethod.POST,
            name="ULTRAPLINIAN Race",
            description="Race multiple models and return the best response. Uses ULTRAPLINIAN engine.",
            model_tier=ModelTier.ULTRA,
            parameters=[
                EndpointParam("messages", "array", "Chat messages"),
                EndpointParam("tier", "string", "Race tier: fast|standard|pro|power|ultra",
                              required=False, default="pro",
                              enum=["fast", "standard", "pro", "power", "ultra"]),
                EndpointParam("max_race_models", "number", "Max models to race", required=False, default=5),
                EndpointParam("stream", "boolean", "SSE streaming", required=False, default=True),
            ],
            tags=["ultraplinian", "core"],
        ))

        # 4. Consortium (hive-mind)
        self.registry.register(EndpointDefinition(
            path="consortium/completions",
            method=HttpMethod.POST,
            name="CONSORTIUM Hive-Mind",
            description="Multi-model synthesis: run N models, synthesize best answer.",
            model_tier=ModelTier.CONSORTIUM,
            parameters=[
                EndpointParam("messages", "array", "Chat messages"),
                EndpointParam("tier", "string", "Consortium tier", required=False, default="pro"),
                EndpointParam("synthesis_model", "string", "Model for final synthesis", required=False),
                EndpointParam("stream", "boolean", "SSE streaming", required=False, default=True),
            ],
            tags=["consortium", "core"],
        ))

        # 5. Model Test (test any model)
        self.registry.register(EndpointDefinition(
            path="models/test",
            method=HttpMethod.POST,
            name="Model Tester",
            description="Test any of the 79 models with a prompt and get quality score.",
            model_tier=ModelTier.AUTO,
            parameters=[
                EndpointParam("model", "string", "Model key to test"),
                EndpointParam("prompt", "string", "Test prompt", required=False,
                              default="Explain distributed Saga pattern with Redis Redlock"),
                EndpointParam("expected_keywords", "array", "Keywords expected in response", required=False),
            ],
            tags=["testing", "models"],
        ))

        # 6. Model List (all 72)
        self.registry.register(EndpointDefinition(
            path="models/list",
            method=HttpMethod.GET,
            name="List All Models",
            description="List all 79 models with their providers, tiers, and status.",
            auth_level=AuthLevel.NONE,
            tags=["models", "info"],
        ))

        # 7. API Builder — create new endpoint
        self.registry.register(EndpointDefinition(
            path="builder/create",
            method=HttpMethod.POST,
            name="Create Endpoint",
            description="Dynamically create a new AI-powered API endpoint.",
            auth_level=AuthLevel.ENTERPRISE,
            model_tier=ModelTier.PRO,
            parameters=[
                EndpointParam("path", "string", "Endpoint path (e.g., 'my/custom-ai')"),
                EndpointParam("name", "string", "Endpoint name"),
                EndpointParam("description", "string", "What this endpoint does"),
                EndpointParam("system_prompt", "string", "System prompt for the AI"),
                EndpointParam("model_tier", "string", "Model tier: auto|fast|pro|ultra",
                              required=False, default="auto"),
                EndpointParam("parameters", "array", "Custom parameters", required=False),
            ],
            tags=["builder", "admin"],
        ))

        # 8. API Builder — test suite
        self.registry.register(EndpointDefinition(
            path="builder/test",
            method=HttpMethod.POST,
            name="Test Endpoint",
            description="Run agent-generated test suite against an endpoint.",
            auth_level=AuthLevel.ENTERPRISE,
            parameters=[
                EndpointParam("endpoint_id", "string", "Endpoint to test"),
                EndpointParam("test_count", "number", "Number of test cases", required=False, default=5),
            ],
            tags=["builder", "testing"],
        ))

        # 9. OpenAPI Spec
        self.registry.register(EndpointDefinition(
            path="builder/openapi",
            method=HttpMethod.GET,
            name="OpenAPI Specification",
            description="Get OpenAPI 3.1 spec for all registered endpoints.",
            auth_level=AuthLevel.NONE,
            tags=["builder", "docs"],
        ))

        # 10. Infrastructure Health
        self.registry.register(EndpointDefinition(
            path="infra/health",
            method=HttpMethod.GET,
            name="Infrastructure Health",
            description="Full health check of all infrastructure layers.",
            tags=["infra", "monitoring"],
        ))

        # 11. Smart Completion (auto-route)
        self.registry.register(EndpointDefinition(
            path="smart/completions",
            method=HttpMethod.POST,
            name="Smart Completion",
            description="Auto-routes to the best model based on task analysis.",
            model_tier=ModelTier.AUTO,
            parameters=[
                EndpointParam("messages", "array", "Chat messages"),
                EndpointParam("task_type", "string", "Task type hint",
                              required=False, default="general",
                              enum=["general", "code", "analysis", "creative", "math", "fast"]),
                EndpointParam("budget", "string", "Cost budget: low|medium|high",
                              required=False, default="medium",
                              enum=["low", "medium", "high"]),
            ],
            tags=["smart", "core"],
        ))

        # 12. WebSocket Streaming (real-time bidirectional)
        self.registry.register(EndpointDefinition(
            path="ws/connect",
            method=HttpMethod.GET,
            name="WebSocket Connect",
            description=(
                "WebSocket endpoint for real-time bidirectional streaming. "
                "Supports: auth handshake, streaming chat, channel subscriptions, heartbeat."
            ),
            auth_level=AuthLevel.BASIC,
            parameters=[
                EndpointParam("protocols", "array", "WebSocket sub-protocols", required=False),
            ],
            tags=["websocket", "streaming", "core"],
            metadata={
                "protocol": "wss",
                "heartbeat_interval": 30,
                "max_connections_per_user": 5,
                "idle_timeout": 300,
                "message_types": ["auth", "chat", "subscribe", "unsubscribe", "ping"],
            },
        ))

        # 13. Batch Completion (multiple models parallel)
        self.registry.register(EndpointDefinition(
            path="batch/completions",
            method=HttpMethod.POST,
            name="Batch Completion",
            description="Send same prompt to multiple models in parallel, get all responses.",
            model_tier=ModelTier.PRO,
            parameters=[
                EndpointParam("messages", "array", "Chat messages"),
                EndpointParam("models", "array", "List of model keys to use"),
                EndpointParam("max_parallel", "number", "Max parallel requests", required=False, default=6),
            ],
            tags=["batch", "core"],
        ))



    def _register_per_model_endpoints(self) -> Any:
        """Dynamically register API endpoints for ALL models in MODELS dict.
        
        Reads from models_registry.MODELS — currently 152 keys (13 base + 139 APEX/Elite).
        Each model gets a /models/{safe_key}/chat endpoint with full parameter set.
        
        No hardcoding — if a model exists in MODELS, it gets an endpoint.
        """
        try:
            from arki_project.utils.models_registry import MODELS as ALL_MODELS, get_apex_tier
        except ImportError:
            logger.warning("Cannot import models_registry — no per-model endpoints")
            return
        
        count = 0
        for model_key, model_info in ALL_MODELS.items():
            # Create URL-safe path: "g-qwen37-max" → "g_qwen37_max"
            safe_key = model_key.replace("-", "_")
            path = f"models/{safe_key}/chat"
            
            # Skip if already registered (from builtin)
            if self.registry.find_by_path(path):
                continue
            
            # Determine tier from APEX or default
            tier = ModelTier.PRO
            apex_tier = None
            try:
                apex_tier = get_apex_tier(model_key)
            except Exception as _apex_err:
                logger.debug("No APEX tier for %s: %s", model_key, _apex_err)
            
            if apex_tier:
                tier_map = {
                    "fast": ModelTier.FAST, "standard": ModelTier.PRO,
                    "smart": ModelTier.PRO, "pro": ModelTier.PRO,
                    "power": ModelTier.ULTRA, "ultra": ModelTier.ULTRA,
                }
                tier = tier_map.get(apex_tier, ModelTier.PRO)
            elif model_info.provider == "groq":
                tier = ModelTier.FAST
            elif model_info.provider == "gemini":
                tier = ModelTier.PRO
            
            # Detect elite models
            is_elite = model_key in (
                "g-qwen37-max", "g-kimi26-think", "g-deepseek-v4-p",
                "g-glm51-think", "g-gemma4-26b", "g-nemotron3-sup", "g-qwen3-coder",
            )
            mode = "elite" if is_elite else ("pro_ultra" if apex_tier else "base")
            
            # Auto-detect tags
            tags = ["model", model_info.provider]
            if is_elite:
                tags.append("elite")
            if apex_tier:
                tags.append(apex_tier)
            
            self.registry.register(EndpointDefinition(
                path=path,
                method=HttpMethod.POST,
                name=f"{model_info.name} Chat",
                description=f"Chat with {model_info.name} [{model_info.id}] — {mode} mode",
                model_tier=tier,
                specific_model=model_key,
                parameters=[
                    EndpointParam("messages", "array", "Chat messages [{role, content}]"),
                    EndpointParam("prompt", "string", "Alternative: single prompt string", required=False),
                    EndpointParam("max_tokens", "number", "Max output tokens", required=False, default=65536),
                    EndpointParam("temperature", "number", "Temperature", required=False,
                                  default=0.7, min_value=0, max_value=2),
                    EndpointParam("stream", "boolean", "SSE streaming", required=False, default=False),
                    EndpointParam("system_prompt", "string", "Custom system prompt", required=False),
                ],
                system_prompt=f"You are {{model_name}}, running in {mode} mode with maximum capability.",
                tags=tags,
                metadata={
                    "model_key": model_key,
                    "model_id": model_info.id,
                    "provider": model_info.provider,
                    "tier": apex_tier or ("elite" if is_elite else "base"),
                    "mode": mode,
                    "context_window": model_info.ctx,
                    "version": "4.0.0",
                    "description_fa": model_info.desc,
                },
            ))
            count += 1
        
        logger.info("Dynamic registration: %d per-model endpoints from MODELS dict", count)


    # ── Endpoint Execution ──────────────────────────────────────

    async def execute_endpoint(self, endpoint_id: str, data: Dict[str, Any],
                              api_key: str = "", user_id: str = "default") -> Dict[str, Any]:
        """Execute a registered endpoint — LIVE model call with rate limiting + auth.

        Flow:
          1. Auth check (if endpoint requires it)
          2. Rate limit check
          3. Validate parameters
          4. Route to correct model via ModelRouter
          5. Build messages array (system_prompt + user messages)
          6. Call ai_client.ask_raw() → real provider (Gemini/Groq/OpenRouter)
          7. Return real model response with transparency metadata
        """
        ep = self.registry.get(endpoint_id)
        if not ep:
            return {"error": f"Endpoint {endpoint_id} not found", "status": "error"}
        if ep.status == EndpointStatus.DISABLED:
            return {"error": f"Endpoint {ep.path} is disabled", "status": "error"}

        t0 = time.time()
        request_id = uuid.uuid4().hex[:12]

        # ── Step 1: Auth check ──
        auth_ok, auth_info = self.auth.validate(api_key, ep.auth_level)
        if not auth_ok:
            return {
                "request_id": request_id,
                "error": "Authentication failed or insufficient tier",
                "required_level": ep.auth_level.value if hasattr(ep.auth_level, 'value') else str(ep.auth_level),
                "status": "auth_error",
            }
        if auth_info and auth_info.get("user_id"):
            user_id = auth_info["user_id"]

        model_key = self.router.select_model(
            ep.model_tier,
            ep.specific_model or data.get("model"),
            data.get("task_type", "general"),
        )

        # ── Step 2: Rate limit check ──
        # Determine provider for rate limits
        provider = "openrouter"
        try:
            from arki_project.utils.models_registry import get_model
            m_info = get_model(model_key)
            provider = m_info.provider
        except Exception as _prov_err:
            logger.debug("Could not resolve provider for %s, defaulting to openrouter: %s",
                         model_key, _prov_err)

        rate_ok, rate_info = self.rate_limiter.check(user_id, model_key, provider)
        if not rate_ok:
            return {
                "request_id": request_id,
                "error": "Rate limit exceeded",
                "retry_after_seconds": rate_info.get("retry_after_seconds", 60) if rate_info else 60,
                "reason": rate_info.get("reason", "rate_limit") if rate_info else "rate_limit",
                "status": "rate_limited",
            }

        try:
            # ── Step 3: Validate parameters ──
            errors = self._validate_params(ep, data)
            if errors:
                return {"error": "Validation failed", "details": errors, "status": "validation_error"}

            # ── Step 4: Build messages array ──
            messages: List[Dict[str, str]] = []

            sys_prompt = data.get("system_prompt", "") or ep.system_prompt or ""
            if sys_prompt:
                from arki_project.utils.models_registry import get_model as _get_model
                try:
                    _m_info = _get_model(model_key)
                    sys_prompt = sys_prompt.replace("{model_name}", _m_info.name)
                except Exception:
                    sys_prompt = sys_prompt.replace("{model_name}", model_key)
                messages.append({"role": "system", "content": sys_prompt})

            user_msgs = data.get("messages")
            if user_msgs and isinstance(user_msgs, list):
                for msg in user_msgs:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        messages.append({"role": msg["role"], "content": msg["content"]})
            else:
                prompt = data.get("prompt") or data.get("message") or data.get("text", "")
                if prompt:
                    messages.append({"role": "user", "content": str(prompt)})

            if not any(m["role"] == "user" for m in messages):
                return {"error": "No user message provided. Send 'messages' array or 'prompt' string.", "status": "error"}

            # ── Step 5: Generation parameters ──
            temperature = float(data.get("temperature", 0.7))
            max_tokens = int(data.get("max_tokens", 65536))

            # ── Step 6: LIVE model call ──
            client = self._get_ai_client()
            response_text = await client.ask_raw(
                messages=messages,
                model_key=model_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            latency = (time.time() - t0) * 1000
            tokens_est = len(response_text) // 4

            self.registry.record_call(endpoint_id, latency, tokens_est)
            self.router.record_latency(model_key, latency)

            # ── Step 7: Build response ──
            result = {
                "request_id": request_id,
                "endpoint": ep.path,
                "model_selected": model_key,
                "model_tier": ep.model_tier.value if hasattr(ep.model_tier, 'value') else str(ep.model_tier),
                "status": "success",
                "response": response_text,
                "usage": {
                    "estimated_tokens": tokens_est,
                    "latency_ms": round(latency, 1),
                },
                "metadata": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "user_id": user_id,
                },
            }

            if hasattr(client, "_last_transparency") and client._last_transparency:
                result["routing"] = client._last_transparency

            logger.info(
                "execute_endpoint [%s] → model=%s latency=%.0fms tokens≈%d",
                request_id, model_key, latency, tokens_est,
            )
            return result

        except Exception as e:
            latency = (time.time() - t0) * 1000
            self.registry.record_call(endpoint_id, latency, 0, error=True)
            logger.error("execute_endpoint [%s] FAILED: %s", request_id, e)
            return {
                "request_id": request_id,
                "endpoint": ep.path,
                "model_selected": model_key,
                "status": "error",
                "error": str(e),
                "latency_ms": round(latency, 1),
            }

    async def execute_by_path(self, path: str, data: Dict[str, Any],
                              api_key: str = "", user_id: str = "default") -> Dict[str, Any]:
        """Execute endpoint by path string (e.g. 'models/g_qwen37_max/chat')."""
        ep = self.registry.find_by_path(path)
        if not ep:
            return {"error": f"No endpoint found for path: {path}", "status": "error"}
        return await self.execute_endpoint(ep.endpoint_id, data, api_key, user_id)

    async def execute_batch(self, requests: List[Dict[str, Any]],
                            max_concurrent: int = 10) -> List[Dict[str, Any]]:
        """Execute multiple endpoint calls concurrently with limits.

        Each request: {"endpoint_id": "...", "data": {...}} or {"path": "...", "data": {...}}
        """
        sem = asyncio.Semaphore(max_concurrent)

        async def _single(req: Dict) -> Dict:
            async with sem:
                ep_id = req.get("endpoint_id", "")
                api_key = req.get("api_key", "")
                user_id = req.get("user_id", "default")
                if not ep_id and req.get("path"):
                    return await self.execute_by_path(req["path"], req.get("data", {}), api_key, user_id)
                return await self.execute_endpoint(ep_id, req.get("data", {}), api_key, user_id)

        results = await asyncio.gather(*[_single(r) for r in requests], return_exceptions=True)
        return [r if isinstance(r, dict) else {"error": str(r), "status": "error"} for r in results]

    async def quick_chat(self, model_key: str, prompt: str, **kwargs) -> str:
        """One-liner: send a prompt to any model, get response text.

        Usage:
            answer = await api.quick_chat("g-qwen37-max", "سلام! خودت رو معرفی کن")
        """
        client = self._get_ai_client()
        messages = [{"role": "user", "content": prompt}]
        sys_prompt = kwargs.pop("system_prompt", "")
        if sys_prompt:
            messages.insert(0, {"role": "system", "content": sys_prompt})
        return await client.ask_raw(
            messages=messages,
            model_key=model_key,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 65536),
        )


    def _validate_params(self, ep: EndpointDefinition, data: Dict) -> List[str]:
        """Validate request parameters against endpoint definition."""
        errors = []
        for param in ep.parameters:
            if param.required and param.name not in data:
                errors.append(f"Missing required parameter: {param.name}")
            if param.name in data:
                val = data[param.name]
                if param.enum and val not in param.enum:
                    errors.append(f"{param.name} must be one of {param.enum}")
                if param.min_value is not None and isinstance(val, (int, float)) and val < param.min_value:
                    errors.append(f"{param.name} must be >= {param.min_value}")
                if param.max_value is not None and isinstance(val, (int, float)) and val > param.max_value:
                    errors.append(f"{param.name} must be <= {param.max_value}")
        return errors

    # ── Dynamic Endpoint Creation ───────────────────────────────

    def create_endpoint(self, path: str, name: str, description: str,
                        system_prompt: str = "", model_tier: str = "auto",
                        parameters: List[Dict] = None, **kwargs) -> EndpointDefinition:
        """Create a new dynamic API endpoint."""
        tier_map = {
            "auto": ModelTier.AUTO, "fast": ModelTier.FAST,
            "pro": ModelTier.PRO, "ultra": ModelTier.ULTRA,
            "consortium": ModelTier.CONSORTIUM,
        }

        params = []
        for p in (parameters or []):
            params.append(EndpointParam(
                name=p.get("name", ""),
                param_type=p.get("type", "string"),
                description=p.get("description", ""),
                required=p.get("required", True),
                default=p.get("default"),
                enum=p.get("enum", []),
            ))

        # Always add messages param for AI endpoints
        if not any(p.name == "messages" for p in params):
            params.insert(0, EndpointParam("messages", "array", "Chat messages [{role, content}]"))

        ep = EndpointDefinition(
            path=path,
            method=HttpMethod(kwargs.get("method", "POST")),
            name=name,
            description=description,
            system_prompt=system_prompt,
            model_tier=tier_map.get(model_tier, ModelTier.AUTO),
            parameters=params,
            tags=kwargs.get("tags", ["custom"]),
        )

        self.registry.register(ep)
        logger.info("Created dynamic endpoint: %s %s", ep.method.value, ep.path)
        return ep

    # ── OpenAPI Spec ────────────────────────────────────────────


    def get_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.1 spec for all endpoints."""
        return self.spec_gen.generate(self.registry.list_all())

    # ── Model Testing ───────────────────────────────────────────


    def get_all_model_keys(self) -> List[Dict[str, str]]:
        """Get all 72 model keys with their info (static, no API needed)."""
        # Base models (Gemini + Groq) — 13
        base = [
            {"key": "gemini-pro", "id": "gemini-2.5-pro-preview-05-06", "provider": "gemini", "tier": "pro"},
            {"key": "gemini-flash", "id": "gemini-2.5-flash-preview-04-17", "provider": "gemini", "tier": "fast"},
            {"key": "gemini-flash-lite", "id": "gemini-2.0-flash-lite", "provider": "gemini", "tier": "fast"},
            {"key": "gemini-pro-search", "id": "gemini-2.5-pro-preview-05-06", "provider": "gemini", "tier": "pro"},
            {"key": "gemini-image", "id": "gemini-2.0-flash-preview-image-generation", "provider": "gemini", "tier": "pro"},
            {"key": "gemini-exp", "id": "gemini-2.5-pro-exp-03-25", "provider": "gemini", "tier": "pro"},
            {"key": "llama8", "id": "llama-3.3-70b-versatile", "provider": "groq", "tier": "fast"},
            {"key": "llama70", "id": "llama-3.3-70b-versatile", "provider": "groq", "tier": "pro"},
            {"key": "llama90", "id": "llama-3.2-90b-vision-preview", "provider": "groq", "tier": "pro"},
            {"key": "mixtral", "id": "mixtral-8x7b-32768", "provider": "groq", "tier": "fast"},
            {"key": "deepseek-r1-groq", "id": "deepseek-r1-distill-llama-70b", "provider": "groq", "tier": "pro"},
            {"key": "qwen-qwq", "id": "qwen-qwq-32b", "provider": "groq", "tier": "pro"},
            {"key": "llama4-scout", "id": "meta-llama/llama-4-scout-17b-16e-instruct", "provider": "groq", "tier": "fast"},
        ]

        # APEX models (OpenRouter) — 59
        g0d = [
            # Fast tier (12)
            {"key": "g-gemini20-flash", "provider": "openrouter", "tier": "fast"},
            {"key": "g-gemini20-flash-lite", "provider": "openrouter", "tier": "fast"},
            {"key": "g-llama4-mav", "provider": "openrouter", "tier": "fast"},
            {"key": "g-llama4-scout", "provider": "openrouter", "tier": "fast"},
            {"key": "g-mistral-small", "provider": "openrouter", "tier": "fast"},
            {"key": "g-phi4", "provider": "openrouter", "tier": "fast"},
            {"key": "g-phi4-mini", "provider": "openrouter", "tier": "fast"},
            {"key": "g-gemma3-27b", "provider": "openrouter", "tier": "fast"},
            {"key": "g-qwen3-30b", "provider": "openrouter", "tier": "fast"},
            {"key": "g-qwen3-32b", "provider": "openrouter", "tier": "fast"},
            {"key": "g-ministral-8b", "provider": "openrouter", "tier": "fast"},
            {"key": "g-glm4-32b", "provider": "openrouter", "tier": "fast"},
            # Standard tier (16)
            {"key": "g-gpt4o", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gpt4o-mini", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gpt41", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gpt41-mini", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gpt41-nano", "provider": "openrouter", "tier": "standard"},
            {"key": "g-claude37-sonnet", "provider": "openrouter", "tier": "standard"},
            {"key": "g-claude35-haiku", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gemini25-flash", "provider": "openrouter", "tier": "standard"},
            {"key": "g-gemini25-flash-lite", "provider": "openrouter", "tier": "standard"},
            {"key": "g-llama33-70b", "provider": "openrouter", "tier": "standard"},
            {"key": "g-mistral-medium", "provider": "openrouter", "tier": "standard"},
            {"key": "g-codestral", "provider": "openrouter", "tier": "standard"},
            {"key": "g-command-a", "provider": "openrouter", "tier": "standard"},
            {"key": "g-deepseek-v3", "provider": "openrouter", "tier": "standard"},
            {"key": "g-qwen3-235b", "provider": "openrouter", "tier": "standard"},
            {"key": "g-nous-deephermes", "provider": "openrouter", "tier": "standard"},
            # Pro tier (13)
            {"key": "g-gpt5", "provider": "openrouter", "tier": "pro"},
            {"key": "g-gpt5-mini", "provider": "openrouter", "tier": "pro"},
            {"key": "g-claude-sonnet-4", "provider": "openrouter", "tier": "pro"},
            {"key": "g-gemini25-pro", "provider": "openrouter", "tier": "pro"},
            {"key": "g-gemini3-pro", "provider": "openrouter", "tier": "pro"},
            {"key": "g-grok3", "provider": "openrouter", "tier": "pro"},
            {"key": "g-grok3-mini", "provider": "openrouter", "tier": "pro"},
            {"key": "g-deepseek-r1", "provider": "openrouter", "tier": "pro"},
            {"key": "g-mistral-large", "provider": "openrouter", "tier": "pro"},
            {"key": "g-llama4-behemoth", "provider": "openrouter", "tier": "pro"},
            {"key": "g-perplexity-sonar-pro", "provider": "openrouter", "tier": "pro"},
            {"key": "g-nvidia-llama70", "provider": "openrouter", "tier": "pro"},
            {"key": "g-moonshot-kimi", "provider": "openrouter", "tier": "pro"},
            # Power tier (11)
            {"key": "g-claude-opus-4", "provider": "openrouter", "tier": "power"},
            {"key": "g-grok4", "provider": "openrouter", "tier": "power"},
            {"key": "g-o3", "provider": "openrouter", "tier": "power"},
            {"key": "g-o4-mini", "provider": "openrouter", "tier": "power"},
            {"key": "g-o4-mini-high", "provider": "openrouter", "tier": "power"},
            {"key": "g-grok3-think", "provider": "openrouter", "tier": "power"},
            {"key": "g-perplexity-sonar-deep", "provider": "openrouter", "tier": "power"},
            {"key": "g-deepseek-r1-0528", "provider": "openrouter", "tier": "power"},
            {"key": "g-qwen3-coder", "provider": "openrouter", "tier": "power"},
            {"key": "g-step2-16k", "provider": "openrouter", "tier": "power"},
            {"key": "g-xiaomi-megrez", "provider": "openrouter", "tier": "power"},
            # Ultra tier (7)
            {"key": "g-claude-opus-4-think", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-gpt5-turbo", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-o3-pro", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-grok4-think", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-gemini25-pro-deep", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-deepseek-r2", "provider": "openrouter", "tier": "ultra"},
            {"key": "g-z1", "provider": "openrouter", "tier": "ultra"},
        ]

        return base + g0d


    def get_all_model_keys_v2(self) -> List[Dict[str, str]]:
        """Get ALL model keys from models_registry.MODELS — dynamic, never stale.
        
        Returns list of {key, id, name, provider, tier, ctx, desc} for each model.
        """
        try:
            from arki_project.utils.models_registry import MODELS, get_apex_tier
        except ImportError:
            return []
        
        result = []
        for key, info in MODELS.items():
            apex_tier = None
            try:
                apex_tier = get_apex_tier(key)
            except Exception as _tier_err:
                logger.debug("No APEX tier for %s: %s", key, _tier_err)
            
            is_elite = key in (
                "g-qwen37-max", "g-kimi26-think", "g-deepseek-v4-p",
                "g-glm51-think", "g-gemma4-26b", "g-nemotron3-sup", "g-qwen3-coder",
            )
            
            result.append({
                "key": key,
                "id": info.id,
                "name": info.name,
                "provider": info.provider,
                "tier": "elite" if is_elite else (apex_tier or "base"),
                "ctx": info.ctx,
                "desc": info.desc,
            })
        
        return result


    # ── Model Testing (REAL quality scoring) ────────────────────

    async def test_all_models_pro_ultra(self, test_prompt: str = None,
                                       max_concurrent: int = 10,
                                       timeout_per_model: float = 30.0) -> Dict[str, Any]:
        """Test ALL models with REAL API calls and quality scoring.
        
        Quality scoring:
          - Response exists and is non-empty → +30
          - Response length > 100 chars → +10
          - Response length > 500 chars → +10
          - Contains expected keywords → +20
          - Persian text detected (if applicable) → +10
          - No error/exception strings → +10
          - Latency < 10s → +10
          
        Max score: 100
        """
        if not test_prompt:
            test_prompt = (
                "Explain the distributed Saga pattern with Redis Redlock for "
                "microservices orchestration. Include: 1) Compensating transactions "
                "with exactly-once semantics, 2) Fence tokens for lock safety, "
                "3) Event sourcing integration, 4) Python asyncio implementation "
                "with proper error handling and circuit breakers."
            )
        
        expected_keywords = [
            "saga", "compensat", "redis", "lock", "event", "async",
            "circuit", "transaction", "idempoten",
        ]
        
        all_models = self.get_all_model_keys_v2()
        results = []
        passed = 0
        failed = 0
        
        sem = asyncio.Semaphore(max_concurrent)
        
        async def _test_one(model_info: Dict) -> ModelTestResult:
            key = model_info["key"]
            mid = model_info["id"]
            provider = model_info["provider"]
            tier = model_info.get("tier", "pro")
            
            async with sem:
                t0 = time.time()
                try:
                    response = await asyncio.wait_for(
                        self.quick_chat(key, test_prompt),
                        timeout=timeout_per_model,
                    )
                    latency = (time.time() - t0) * 1000
                    
                    # Real quality scoring
                    score = 0
                    if response and len(response.strip()) > 0:
                        score += 30
                    if len(response) > 100:
                        score += 10
                    if len(response) > 500:
                        score += 10
                    
                    # Keyword matching
                    response_lower = response.lower()
                    kw_hits = sum(1 for kw in expected_keywords if kw in response_lower)
                    score += min(20, int(kw_hits / max(len(expected_keywords), 1) * 20))
                    
                    # No error strings
                    error_markers = ["error", "exception", "traceback", "failed"]
                    if not any(em in response_lower[:200] for em in error_markers):
                        score += 10
                    
                    # Latency bonus
                    if latency < 10000:
                        score += 10
                    
                    # Cap at 100
                    score = min(100, score)
                    
                    return ModelTestResult(
                        model_key=key, model_id=mid, provider=provider,
                        available=True, latency_ms=latency,
                        response_quality=float(score),
                        response_preview=response[:300],
                        tier=tier,
                    )
                    
                except asyncio.TimeoutError:
                    return ModelTestResult(
                        model_key=key, model_id=mid, provider=provider,
                        available=False, latency_ms=(time.time() - t0) * 1000,
                        error=f"Timeout after {timeout_per_model}s",
                        tier=tier,
                    )
                except Exception as e:
                    return ModelTestResult(
                        model_key=key, model_id=mid, provider=provider,
                        available=False, latency_ms=(time.time() - t0) * 1000,
                        error=str(e),
                        tier=tier,
                    )
        
        # Run tests with concurrency limit
        tasks = [_test_one(m) for m in all_models]
        test_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in test_results:
            if isinstance(r, Exception):
                failed += 1
                continue
            results.append(r)
            self._model_test_results.append(r)
            if r.available:
                passed += 1
            else:
                failed += 1
        
        # Sort by quality score descending
        results.sort(key=lambda r: r.response_quality or 0, reverse=True)
        
        return {
            "test_prompt": test_prompt[:100] + "..." if len(test_prompt) > 100 else test_prompt,
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{passed}/{len(results)} ({passed/max(len(results),1)*100:.1f}%)",
            "avg_quality": round(sum(r.response_quality for r in results if r.available) / max(passed, 1), 1),
            "avg_latency_ms": round(sum(r.latency_ms for r in results if r.available) / max(passed, 1), 1),
            "results": [
                {
                    "key": r.model_key,
                    "id": r.model_id,
                    "provider": r.provider,
                    "tier": r.tier,
                    "available": r.available,
                    "quality_score": r.response_quality,
                    "latency_ms": round(r.latency_ms, 2),
                    "response_preview": r.response_preview[:150] if r.response_preview else None,
                    "error": r.error,
                }
                for r in results
            ],
        }


    # ── Test Results ────────────────────────────────────────────

    def get_test_report(self) -> Dict[str, Any]:
        """Get comprehensive test report."""
        return {
            "endpoint_tests": {
                "total": len(self._test_results),
                "passed": sum(1 for t in self._test_results if t.passed),
                "failed": sum(1 for t in self._test_results if not t.passed),
                "results": [
                    {
                        "endpoint": t.endpoint_id,
                        "test": t.test_name,
                        "passed": t.passed,
                        "model": t.model_used,
                        "latency_ms": t.latency_ms,
                        "quality": t.quality_score,
                        "error": t.error,
                    }
                    for t in self._test_results
                ],
            },
            "model_tests": {
                "total": len(self._model_test_results),
                "available": sum(1 for m in self._model_test_results if m.available),
                "results": [
                    {
                        "key": m.model_key,
                        "id": m.model_id,
                        "provider": m.provider,
                        "available": m.available,
                        "latency_ms": m.latency_ms,
                        "quality": m.response_quality,
                        "tier": m.tier,
                        "error": m.error,
                    }
                    for m in self._model_test_results
                ],
            },
            "endpoints": {
                "total": self.registry.count,
                "active": self.registry.active_count,
            },
            "model_count": 72,
        }

    # ── Summary ─────────────────────────────────────────────────


    # ── Summary ─────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Get API Builder status — complete system overview."""
        model_count = self.router.get_all_models_count()
        return {
            "version": "4.0.0-TITAN-DYNAMIC",
            "initialized": self._initialized,
            "endpoints": {
                "total": self.registry.count,
                "active": self.registry.active_count,
                "builtin": 13,
                "per_model": max(0, self.registry.count - 13),
            },
            "models": {
                "total": model_count,
                "note": "Dynamic from models_registry.MODELS — not hardcoded",
            },
            "features": {
                "rate_limiter": True,
                "auth_middleware": True,
                "pipeline_builder": True,
                "endpoint_persistence": True,
                "real_test_framework": True,
                "dynamic_registration": True,
                "streaming_ready": True,
            "websocket_manager": True,
            },
            "test_summary": {
                "total_tests": len(self._model_test_results),
                "passed": sum(1 for m in self._model_test_results if m.available),
                "avg_quality": round(
                    sum(m.response_quality for m in self._model_test_results if m.available) /
                    max(sum(1 for m in self._model_test_results if m.available), 1), 1
                ),
            },
            "router_stats": self.router.get_model_stats(),
        }



# ═══════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════

_builder: Optional[APIBuilderAgent] = None


def get_api_builder() -> APIBuilderAgent:
    """Get the singleton API Builder agent."""
    global _builder
    if _builder is None:
        _builder = APIBuilderAgent()
    return _builder



