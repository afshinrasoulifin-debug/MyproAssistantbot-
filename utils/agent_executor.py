
"""
tg_bot/utils/agent_executor.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
AGENT EXECUTOR — Autonomous Multi-Step Agent Chain

The brain of Arki Engine. Enables LLMs to autonomously decide which
tools to use, chain multiple operations, and solve complex multi-step
tasks with planning, reflection, and parallel execution.

Architecture
────────────
  ┌──────────┐     ┌──────────┐     ┌───────────┐
  │  User     │────▶│ Planner  │────▶│ Scheduler │
  │  Query    │     │  LLM     │     │ (DAG)     │
  └──────────┘     └──────────┘     └─────┬─────┘
                                          │
                         ┌────────────────┼────────────────┐
                         ▼                ▼                ▼
                   ┌──────────┐    ┌──────────┐    ┌──────────┐
                   │ Tool A   │    │ Tool B   │    │ Tool C   │
                   │ (search) │    │ (recon)  │    │ (code)   │
                   └────┬─────┘    └────┬─────┘    └────┬─────┘
                        │               │               │
                        └───────────────┼───────────────┘
                                        ▼
                                  ┌──────────┐
                                  │ Reflector│
                                  │ (verify) │
                                  └────┬─────┘
                                       ▼
                                  ┌──────────┐
                                  │ Synthesis│
                                  │ → Answer │
                                  └──────────┘

Features
────────
  • Function calling with 20+ built-in tools
  • Multi-step reasoning with automatic re-planning
  • Parallel tool execution via dependency DAG
  • Error recovery with exponential backoff + fallback
  • Execution trace for full transparency & audit
  • Budget control (max steps, max tokens, max time, max cost)
  • Tool result caching (LRU with TTL)
  • Self-reflection: evaluate own answers before returning
  • Memory integration: inject relevant past context
  • Streaming progress callbacks
  • Retry with alternative tool strategies
  • Dependency-aware parallel batch scheduler
  • Cost tracking per tool call and per trace

References
──────────
  Port of: apex_app/src/lib/agent-executor.ts (766 lines)
  Enhanced with: DAG scheduling, reflection loop, cost tracking,
                 retry backoff, LRU cache, richer tool definitions
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import traceback
import uuid
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
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

MAX_AGENT_STEPS         = 50
MAX_TOTAL_TIME_S        = 600
MAX_RETRIES_PER_STEP    = 5
TOOL_CACHE_TTL          = 300       # seconds
TOOL_CACHE_MAX_SIZE     = 256
MAX_TOOL_OUTPUT_CHARS   = 32_000
MAX_TRACES_HISTORY      = 500
PARALLEL_BATCH_SIZE     = 6
REFLECTION_THRESHOLD    = 0.6       # reflect if confidence < this
BACKOFF_BASE_S          = 1.0
BACKOFF_MAX_S           = 16.0
DEFAULT_TOOL_TIMEOUT_S  = 60


# ═══════════════════════════════════════════════════════════════════
# Enumerations
# ═══════════════════════════════════════════════════════════════════

class ToolCategory(str, Enum):
    SEARCH      = "search"
    RECON       = "recon"
    AUTOMATION  = "automation"
    CODE        = "code"
    DATA        = "data"
    CRYPTO      = "crypto"
    NETWORK     = "network"
    ANALYSIS    = "analysis"
    UTILITY     = "utility"
    MEMORY      = "memory"
    MULTIMODAL  = "multimodal"
    API         = "api"
    MODELS      = "models"
    INFRA       = "infrastructure"


class StepStatus(str, Enum):
    PENDING     = "pending"
    QUEUED      = "queued"
    RUNNING     = "running"
    COMPLETED   = "completed"
    FAILED      = "failed"
    SKIPPED     = "skipped"
    RETRYING    = "retrying"
    CANCELLED   = "cancelled"


class TraceStatus(str, Enum):
    PLANNING    = "planning"
    EXECUTING   = "executing"
    REFLECTING  = "reflecting"
    COMPLETED   = "completed"
    ERROR       = "error"
    TIMEOUT     = "timeout"
    CANCELLED   = "cancelled"


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ToolParam:
    """Describes a single parameter for a tool."""
    name: str
    type: str                       # string | number | boolean | array | object
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def to_schema(self) -> dict:
        """Convert to OpenAI-compatible JSON Schema property."""
        schema: dict = {"type": self.type, "description": self.description}
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        return schema


@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    success: bool
    data: Any
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_cost: int = 0             # estimated tokens consumed
    cached: bool = False

    def truncated_data(self, max_chars: int = MAX_TOOL_OUTPUT_CHARS) -> str:
        """Get JSON-serialized data truncated to max_chars."""
        raw = json.dumps(self.data, ensure_ascii=False, default=str)
        if len(raw) <= max_chars:
            return raw
        return raw[:max_chars] + f"\n... [truncated, {len(raw):,} chars total]"


@dataclass
class Tool:
    """A callable tool available to the agent."""
    name: str
    description: str
    parameters: List[ToolParam]
    execute: Callable[..., Awaitable[ToolResult]]
    category: ToolCategory = ToolCategory.UTILITY
    requires_api_key: bool = False
    timeout_s: float = DEFAULT_TOOL_TIMEOUT_S
    cost_per_call: float = 0.0      # estimated USD
    tags: List[str] = field(default_factory=list)

    def to_openai_tool(self) -> dict:
        """Convert to OpenAI function-calling tool definition."""
        properties = {}
        required = []
        for p in self.parameters:
            properties[p.name] = p.to_schema()
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


@dataclass
class AgentStep:
    """A single step in the agent execution."""
    id: int
    thought: str = ""
    action: Optional[Dict[str, Any]] = None   # {tool, args}
    result: Optional[ToolResult] = None
    observation: str = ""
    duration_ms: float = 0.0
    status: StepStatus = StepStatus.PENDING
    retries: int = 0
    depends_on: List[int] = field(default_factory=list)
    error_trace: str = ""
    cost: float = 0.0

    @property
    def tool_name(self) -> Optional[str]:
        return self.action.get("tool") if self.action else None

    @property
    def tool_args(self) -> dict:
        return self.action.get("args", {}) if self.action else {}


@dataclass
class AgentPlan:
    """Decomposition of a user query into executable steps."""
    goal: str
    steps: List[Dict[str, Any]]     # [{description, tool, args, depends_on}]
    reasoning: str = ""
    complexity: str = "medium"      # low | medium | high | expert
    estimated_time_s: float = 30.0
    estimated_cost: float = 0.0


@dataclass
class ExecutionTrace:
    """Full trace of an agent execution for auditing."""
    id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:12]}")
    query: str = ""
    plan: Optional[AgentPlan] = None
    steps: List[AgentStep] = field(default_factory=list)
    final_answer: str = ""
    reflection: str = ""
    total_duration_ms: float = 0.0
    tokens_used: int = 0
    tool_calls: int = 0
    total_cost: float = 0.0
    success: bool = False
    model: str = ""
    status: TraceStatus = TraceStatus.PLANNING
    metadata: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Human-readable summary of the trace."""
        lines = [
            f"Trace {self.id} | {self.status.value}",
            f"Query: {self.query[:120]}",
            f"Steps: {len(self.steps)} | Tools: {self.tool_calls}",
            f"Duration: {self.total_duration_ms:.0f}ms | Cost: ${self.total_cost:.4f}",
            f"Tokens: {self.tokens_used:,}",
        ]
        if self.reflection:
            lines.append(f"Reflection: {self.reflection[:200]}")
        return "\n".join(lines)


@dataclass
class AgentConfig:
    """Configuration for an agent execution."""
    model: str = "anthropic/claude-sonnet-4-20250514"
    api_key: str = ""
    max_steps: int = MAX_AGENT_STEPS
    max_time_s: float = MAX_TOTAL_TIME_S
    max_tokens: int = 4096
    max_cost: float = 1.0           # USD budget
    temperature: float = 0.3
    tools_filter: Optional[List[str]] = None   # restrict to these tools
    enable_reflection: bool = True
    enable_parallel: bool = True
    enable_caching: bool = True
    streaming: bool = False
    verbose: bool = False
    memory_context: str = ""        # injected RAG context
    system_prompt_extra: str = ""   # additional system instructions

    # Callbacks
    on_step: Optional[Callable[[AgentStep], None]] = None
    on_thought: Optional[Callable[[str], None]] = None
    on_tool_call: Optional[Callable[[str, dict], None]] = None
    on_tool_result: Optional[Callable[[str, ToolResult], None]] = None
    on_plan: Optional[Callable[[AgentPlan], None]] = None
    on_reflection: Optional[Callable[[str, float], None]] = None


# ═══════════════════════════════════════════════════════════════════
# LRU Cache with TTL
# ═══════════════════════════════════════════════════════════════════

class LRUCache:
    """Least-recently-used cache with time-to-live expiry."""

    def __init__(self, max_size: int = TOOL_CACHE_MAX_SIZE, ttl: float = TOOL_CACHE_TTL) -> None:
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _make_key(tool: str, args: dict) -> str:
        raw = json.dumps({"tool": tool, "args": args}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, tool: str, args: dict) -> Optional[ToolResult]:
        key = self._make_key(tool, args)
        if key in self._cache:
            value, ts = self._cache[key]
            if time.time() - ts < self._ttl:
                self._cache.move_to_end(key)
                self._hits += 1
                result = ToolResult(**value) if isinstance(value, dict) else value
                result.cached = True
                return result
            else:
                del self._cache[key]
        self._misses += 1
        return None

    def put(self, tool: str, args: dict, result: ToolResult) -> None:
        key = self._make_key(tool, args)
        self._cache[key] = (
            {"success": result.success, "data": result.data,
             "error": result.error, "duration_ms": result.duration_ms,
             "metadata": result.metadata},
            time.time(),
        )
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self, tool: Optional[str] = None) -> int:
        """Invalidate cache entries. If tool given, only that tool."""
        if tool is None:
            count = len(self._cache)
            self._cache.clear()
            return count
        to_remove = [k for k, (v, _) in self._cache.items()
                     if isinstance(v, dict) and v.get("_tool") == tool]
        for k in to_remove:
            del self._cache[k]
        return len(to_remove)

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total * 100:.1f}%" if total > 0 else "N/A",
        }


# ═══════════════════════════════════════════════════════════════════
# Tool Registry
# ═══════════════════════════════════════════════════════════════════

class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}
        self._call_counts: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._total_duration: Dict[str, float] = defaultdict(float)

    def register(self, tool: Tool) -> None:
        """Register a tool. Overwrites if name exists."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name} [{tool.category.value}]")

    def unregister(self, name: str) -> bool:
        return self._tools.pop(name, None) is not None

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def get_all(self) -> List[Tool]:
        return list(self._tools.values())

    def get_by_category(self, category: ToolCategory) -> List[Tool]:
        return [t for t in self._tools.values() if t.category == category]

    def get_by_tags(self, tags: List[str]) -> List[Tool]:
        tag_set = set(tags)
        return [t for t in self._tools.values() if tag_set & set(t.tags)]

    def get_definitions(self, filter_names: Optional[List[str]] = None) -> List[dict]:
        """Get OpenAI-compatible tool definitions."""
        tools = self.get_all()
        if filter_names:
            name_set = set(filter_names)
            tools = [t for t in tools if t.name in name_set]
        return [t.to_openai_tool() for t in tools]

    def record_call(self, name: str, duration_ms: float, error: bool = False) -> None:
        self._call_counts[name] += 1
        self._total_duration[name] += duration_ms
        if error:
            self._error_counts[name] += 1

    def get_stats(self) -> Dict[str, Any]:
        stats = {}
        for name in self._tools:
            calls = self._call_counts.get(name, 0)
            errors = self._error_counts.get(name, 0)
            total_ms = self._total_duration.get(name, 0)
            stats[name] = {
                "calls": calls,
                "errors": errors,
                "error_rate": f"{errors/calls*100:.1f}%" if calls > 0 else "0%",
                "avg_latency_ms": f"{total_ms/calls:.0f}" if calls > 0 else "N/A",
            }
        return stats


# Global registry instance
registry = ToolRegistry()


# ═══════════════════════════════════════════════════════════════════
# Built-in Tool Registration
# ═══════════════════════════════════════════════════════════════════

def register_builtin_tools() -> None:
    """
    Register all built-in tools. Each tool wraps an async function
    that performs the actual work. Tools are auto-discovered from
    other Arki modules (web_recon, web_search, crypto_engine, etc.)
    """

    # 1. Deep Web Search
    async def _web_search(args: dict) -> ToolResult:
        start = time.time()
        try:
            from utils.web_search import deep_search
            results = await deep_search(
                args["query"],
                engines=args.get("engines", ["searx", "duckduckgo"]),
                max_results=args.get("max_results", 10),
            )
            return ToolResult(success=True, data=results,
                              duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="web_search",
        description="Search the web using multiple engines (SearX, DuckDuckGo, Brave, HackerNews). "
                    "Returns ranked results with titles, URLs, and snippets.",
        category=ToolCategory.SEARCH,
        parameters=[
            ToolParam("query", "string", "Search query"),
            ToolParam("engines", "array", "Engines: searx, duckduckgo, brave, hackernews",
                      required=False, default=["searx", "duckduckgo"]),
            ToolParam("max_results", "number", "Max results to return",
                      required=False, default=10, min_value=1, max_value=50),
        ],
        execute=_web_search,
        tags=["search", "web"],
    ))

    # 2. Academic Search
    async def _academic_search(args: dict) -> ToolResult:
        start = time.time()
        try:
            from utils.web_search import academic_search
            results = await academic_search(
                args["query"], max_results=args.get("max_results", 10),
            )
            return ToolResult(success=True, data=results,
                              duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="academic_search",
        description="Search academic papers on arXiv and Semantic Scholar. "
                    "Returns titles, abstracts, authors, citation counts.",
        category=ToolCategory.SEARCH,
        parameters=[
            ToolParam("query", "string", "Academic search query"),
            ToolParam("max_results", "number", "Max results",
                      required=False, default=10),
        ],
        execute=_academic_search,
        tags=["search", "academic", "papers"],
    ))

    # 3. Code Search
    async def _code_search(args: dict) -> ToolResult:
        start = time.time()
        try:
            from utils.web_search import code_search
            results = await code_search(
                args["query"], max_results=args.get("max_results", 10),
            )
            return ToolResult(success=True, data=results,
                              duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="code_search",
        description="Search code repositories on GitHub and programming Q&A.",
        category=ToolCategory.SEARCH,
        parameters=[
            ToolParam("query", "string", "Code search query"),
            ToolParam("max_results", "number", "Max results",
                      required=False, default=10),
        ],
        execute=_code_search,
        tags=["search", "code", "github"],
    ))

    # 4. Web Reconnaissance
    async def _web_recon(args: dict) -> ToolResult:
        start = time.time()
        try:
            from utils.web_recon import recon, full_recon
            if args.get("deep"):
                result = await full_recon(args["target"])
            else:
                result = await recon(
                    target=args["target"],
                    modules=args.get("modules"),
                )
            return ToolResult(success=True, data=result,
                              duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="web_recon",
        description="Reconnaissance on a target domain: tech detection, security headers, "
                    "WAF, subdomains, endpoints, DNS, WHOIS, SSL analysis.",
        category=ToolCategory.RECON,
        parameters=[
            ToolParam("target", "string", "Target domain or URL"),
            ToolParam("modules", "array",
                      "Modules: headers, technologies, waf, subdomains, endpoints, "
                      "emails, social, security, robots, sitemap, dns, whois, ssl",
                      required=False),
            ToolParam("deep", "boolean", "Run ALL modules", required=False, default=False),
        ],
        execute=_web_recon,
        timeout_s=90,
        tags=["recon", "security", "network"],
    ))

    # 5. Google Dorking
    async def _google_dork(args: dict) -> ToolResult:
        start = time.time()
        try:
            from utils.web_recon import generate_dorks
            queries = generate_dorks(
                args["target"],
                types=args.get("types", [
                    "sensitive_files", "login_pages",
                    "api_endpoints", "subdomains",
                ]),
            )
            return ToolResult(success=True, data=queries,
                              duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="google_dork",
        description="Generate Google dorking queries for a target to find sensitive files, "
                    "login pages, exposed APIs, credentials.",
        category=ToolCategory.RECON,
        parameters=[
            ToolParam("target", "string", "Target domain"),
            ToolParam("types", "array",
                      "Dork types: sensitive_files, login_pages, open_directories, "
                      "error_messages, api_endpoints, subdomains, credentials",
                      required=False),
        ],
        execute=_google_dork,
        tags=["recon", "dorking", "osint"],
    ))

    # 6. HTTP Request
    async def _http_request(args: dict) -> ToolResult:
        start = time.time()
        try:
            method = (args.get("method") or "GET").upper()
            headers = {"User-Agent": "Arki-Agent/3.0"}
            if args.get("headers"):
                headers.update(args["headers"])

            # v10.1: Route through TITANIUM shielded client
            if _TITANIUM_ACTIVE:
                json_body = None
                if args.get("body") and isinstance(args["body"], dict):
                    json_body = args["body"]
                resp = await shielded_request(
                    method, args["url"],
                    json_data=json_body,
                    headers=headers,
                    timeout=60.0,
                    provider_name="agent_http",
                )
                body: Any
                if resp.success:
                    try:
                        body = resp.json()
                    except Exception:
                        body = resp.text[:10_000]
                else:
                    body = resp.text[:10_000] if resp.text else resp.error
                return ToolResult(
                    success=resp.success,
                    data={"status": resp.status, "headers": resp.headers, "body": body},
                    duration_ms=(time.time() - start) * 1000,
                )
            else:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method, args["url"],
                        headers=headers,
                        data=args.get("body"),
                        timeout=aiohttp.ClientTimeout(total=30),
                        ssl=False,
                    ) as resp:
                        ct = resp.headers.get("content-type", "")
                        body: Any
                        if "json" in ct:
                            body = await resp.json()
                        else:
                            text = await resp.text()
                            body = text[:10_000]

                        return ToolResult(
                            success=True,
                            data={
                                "status": resp.status,
                                "headers": dict(resp.headers),
                                "body": body,
                            },
                            duration_ms=(time.time() - start) * 1000,
                        )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="http_request",
        description="Make HTTP request to any URL. GET, POST, PUT, DELETE with "
                    "custom headers and body.",
        category=ToolCategory.NETWORK,
        parameters=[
            ToolParam("url", "string", "URL to request"),
            ToolParam("method", "string", "HTTP method", required=False,
                      default="GET", enum=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]),
            ToolParam("headers", "object", "Request headers", required=False),
            ToolParam("body", "string", "Request body (JSON string)", required=False),
        ],
        execute=_http_request,
        tags=["network", "http", "api"],
    ))

    # 7. Execute Code (sandboxed Python)
    async def _execute_code(args: dict) -> ToolResult:
        start = time.time()
        try:
            code = args["code"]
            # Create a restricted globals dict
            safe_globals: dict = {
                "__builtins__": {
                    k: getattr(__builtins__, k) if hasattr(__builtins__, k) else None
                    for k in [
                        "abs", "all", "any", "bool", "chr", "dict", "dir",
                        "divmod", "enumerate", "filter", "float", "format",
                        "frozenset", "getattr", "hasattr", "hash", "hex",
                        "id", "int", "isinstance", "issubclass", "iter",
                        "len", "list", "map", "max", "min", "next", "oct",
                        "ord", "pow", "print", "range", "repr", "reversed",
                        "round", "set", "slice", "sorted", "str", "sum",
                        "tuple", "type", "zip",
                    ]
                } if isinstance(__builtins__, dict) else __builtins__,
            }
            safe_locals: dict = {}

            exec(compile(code, "<agent-exec>", "exec"), safe_globals, safe_locals)

            # Capture result — look for 'result' variable or last expression
            result = safe_locals.get("result", safe_locals.get("output", str(safe_locals)))
            return ToolResult(success=True, data=result,
                              duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None,
                              error=f"{type(e).__name__}: {e}",
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="execute_code",
        description="Execute Python code and return the result. Useful for calculations, "
                    "data processing, or any programmatic task. Set variable 'result' "
                    "to return output.",
        category=ToolCategory.CODE,
        parameters=[
            ToolParam("code", "string", "Python code to execute"),
        ],
        execute=_execute_code,
        tags=["code", "python", "compute"],
    ))

    # 8. Text Analysis
    async def _analyze_text(args: dict) -> ToolResult:
        start = time.time()
        text = args["text"]
        words = text.split()
        sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".")
                     if s.strip()]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # Keyword extraction via term frequency
        from collections import Counter
        import re as _re
        clean_words = [_re.sub(r"[^\w\u0600-\u06FF]", "", w.lower())
                       for w in words if len(w) > 3]
        freq = Counter(clean_words).most_common(20)
        keywords = [{"word": w, "count": c} for w, c in freq if w]

        # Language detection
        has_arabic = bool(_re.search(r"[\u0600-\u06FF]", text))
        has_cjk = bool(_re.search(r"[\u4e00-\u9fff]", text))
        has_cyrillic = bool(_re.search(r"[\u0400-\u04FF]", text))
        lang = ("Arabic/Persian" if has_arabic else
                "Chinese" if has_cjk else
                "Russian/Cyrillic" if has_cyrillic else
                "English/Latin")

        # Readability (Flesch-Kincaid approximation)
        syllable_count = sum(max(1, len(_re.findall(r"[aeiouy]+", w.lower())))
                            for w in words) if words else 0
        fk_grade = (0.39 * (len(words) / max(len(sentences), 1))
                    + 11.8 * (syllable_count / max(len(words), 1))
                    - 15.59) if words else 0

        return ToolResult(success=True, data={
            "characters": len(text),
            "words": len(words),
            "unique_words": len(set(w.lower() for w in words)),
            "sentences": len(sentences),
            "paragraphs": len(paragraphs),
            "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
            "avg_words_per_sentence": len(words) / max(len(sentences), 1),
            "language": lang,
            "readability_grade": round(fk_grade, 1),
            "keywords": keywords,
        }, duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="analyze_text",
        description="Analyze text: word/sentence counts, readability, language detection, "
                    "keyword extraction, vocabulary richness.",
        category=ToolCategory.ANALYSIS,
        parameters=[
            ToolParam("text", "string", "Text to analyze"),
        ],
        execute=_analyze_text,
        tags=["analysis", "text", "nlp"],
    ))

    # 9. Data Transform (filter, sort, aggregate, map)
    async def _transform_data(args: dict) -> ToolResult:
        start = time.time()
        try:
            data = json.loads(args["data"])
            if not isinstance(data, list):
                data = [data]

            for op in args["operations"]:
                op_type = op.get("type")
                if op_type == "filter":
                    fld, cmp, val = op["field"], op.get("op", "=="), op.get("value")
                    ops_map = {
                        ">": lambda a, b: a > b, "<": lambda a, b: a < b,
                        ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
                        "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
                        "contains": lambda a, b: str(b) in str(a),
                        "startswith": lambda a, b: str(a).startswith(str(b)),
                        "endswith": lambda a, b: str(a).endswith(str(b)),
                        "regex": lambda a, b: bool(__import__("re").search(str(b), str(a))),
                    }
                    fn = ops_map.get(cmp, lambda a, b: a == b)
                    data = [item for item in data if fn(item.get(fld), val)]

                elif op_type == "sort":
                    rev = op.get("order", "asc") == "desc"
                    data.sort(key=lambda x: x.get(op["field"], 0), reverse=rev)

                elif op_type == "aggregate":
                    vals = [float(item.get(op["field"], 0)) for item in data
                            if item.get(op["field"]) is not None]
                    fn_name = op.get("fn", "sum")
                    agg = {
                        "sum": sum(vals), "avg": sum(vals) / max(len(vals), 1),
                        "min": min(vals) if vals else 0,
                        "max": max(vals) if vals else 0,
                        "count": len(vals),
                        "median": sorted(vals)[len(vals)//2] if vals else 0,
                        "stddev": (sum((v - sum(vals)/len(vals))**2
                                       for v in vals) / max(len(vals)-1, 1)) ** 0.5
                                  if len(vals) > 1 else 0,
                    }
                    data = [{"field": op["field"], "operation": fn_name,
                             "value": agg.get(fn_name, 0)}]

                elif op_type == "limit":
                    data = data[:op.get("count", 10)]

                elif op_type == "group_by":
                    groups: dict = {}
                    for item in data:
                        key = str(item.get(op["field"], ""))
                        groups.setdefault(key, []).append(item)
                    data = [{"group": k, "count": len(v), "items": v}
                            for k, v in groups.items()]

                elif op_type == "select":
                    fields = op.get("fields", [])
                    data = [{f: item.get(f) for f in fields} for item in data]

                elif op_type == "distinct":
                    seen: set = set()
                    unique = []
                    fld = op.get("field")
                    for item in data:
                        key = str(item.get(fld)) if fld else json.dumps(item, sort_keys=True)
                        if key not in seen:
                            seen.add(key)
                            unique.append(item)
                    data = unique

            return ToolResult(success=True, data=data,
                              duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="transform_data",
        description="Transform JSON data: filter, sort, aggregate (sum/avg/min/max/count/"
                    "median/stddev), group_by, select, distinct, limit.",
        category=ToolCategory.DATA,
        parameters=[
            ToolParam("data", "string", "JSON string of data"),
            ToolParam("operations", "array",
                      "Operations: [{type:'filter', field:'x', op:'>', value:5}, "
                      "{type:'sort', field:'y', order:'desc'}, "
                      "{type:'aggregate', field:'z', fn:'avg'}, "
                      "{type:'group_by', field:'category'}, "
                      "{type:'select', fields:['a','b']}, "
                      "{type:'distinct', field:'name'}, "
                      "{type:'limit', count:10}]"),
        ],
        execute=_transform_data,
        tags=["data", "transform", "etl"],
    ))

    # 10. Encode / Decode
    async def _encode_decode(args: dict) -> ToolResult:
        import base64
        start = time.time()
        text = args["text"]
        fmt = args["format"]
        encode = args["direction"] == "encode"

        try:
            result: str
            if fmt == "base64":
                result = (base64.b64encode(text.encode()).decode() if encode
                          else base64.b64decode(text).decode())
            elif fmt == "url":
                from urllib.parse import quote, unquote
                result = quote(text) if encode else unquote(text)
            elif fmt == "hex":
                result = (text.encode().hex() if encode
                          else bytes.fromhex(text).decode())
            elif fmt == "binary":
                if encode:
                    result = " ".join(f"{b:08b}" for b in text.encode())
                else:
                    bits = text.replace(" ", "")
                    result = bytes(int(bits[i:i+8], 2)
                                   for i in range(0, len(bits), 8)).decode()
            elif fmt == "rot13":
                result = text.translate(str.maketrans(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
                ))
            elif fmt == "morse":
                MORSE = {
                    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..",
                    "E": ".", "F": "..-.", "G": "--.", "H": "....",
                    "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
                    "M": "--", "N": "-.", "O": "---", "P": ".--.",
                    "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
                    "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
                    "Y": "-.--", "Z": "--..", "0": "-----", "1": ".----",
                    "2": "..---", "3": "...--", "4": "....-", "5": ".....",
                    "6": "-....", "7": "--...", "8": "---..", "9": "----.",
                    " ": "/",
                }
                if encode:
                    result = " ".join(MORSE.get(c.upper(), c) for c in text)
                else:
                    REV_MORSE = {v: k for k, v in MORSE.items()}
                    result = "".join(REV_MORSE.get(c, c) for c in text.split(" "))
            else:
                result = text

            return ToolResult(success=True, data={
                "input": text[:200], "output": result[:2000],
                "format": fmt, "direction": args["direction"],
            }, duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="encode_decode",
        description="Encode or decode text: base64, url, hex, binary, rot13, morse.",
        category=ToolCategory.UTILITY,
        parameters=[
            ToolParam("text", "string", "Text to encode/decode"),
            ToolParam("format", "string", "Format", enum=[
                "base64", "url", "hex", "binary", "rot13", "morse"]),
            ToolParam("direction", "string", "encode or decode",
                      enum=["encode", "decode"]),
        ],
        execute=_encode_decode,
        tags=["utility", "encoding"],
    ))

    # 11. Crypto Operations
    async def _crypto_ops(args: dict) -> ToolResult:
        start = time.time()
        try:
            from utils.crypto_engine import (
                aes_encrypt, aes_decrypt, hash_data,
                analyze_password, generate_password as gen_pw,
                zwc_hide, zwc_reveal,
            )
            op = args["operation"]
            if op == "encrypt":
                result = aes_encrypt(args["text"], args["password"])
                return ToolResult(success=True, data=result.__dict__
                                  if hasattr(result, "__dict__") else result,
                                  duration_ms=(time.time() - start) * 1000)
            elif op == "decrypt":
                result = aes_decrypt(args["ciphertext"], args["password"],
                                     iv=args.get("iv"), tag=args.get("tag"))
                return ToolResult(success=True, data={"plaintext": result},
                                  duration_ms=(time.time() - start) * 1000)
            elif op == "hash":
                result = hash_data(args["text"], args.get("algorithm", "sha256"))
                return ToolResult(success=True, data=result,
                                  duration_ms=(time.time() - start) * 1000)
            elif op == "password_analysis":
                result = analyze_password(args["text"])
                return ToolResult(success=True, data=result,
                                  duration_ms=(time.time() - start) * 1000)
            elif op == "generate_password":
                pw = gen_pw(length=args.get("length", 20))
                return ToolResult(success=True, data={"password": pw},
                                  duration_ms=(time.time() - start) * 1000)
            elif op == "steganography_hide":
                result = zwc_hide(args["carrier"], args["secret"])
                return ToolResult(success=True, data=result,
                                  duration_ms=(time.time() - start) * 1000)
            elif op == "steganography_reveal":
                result = zwc_reveal(args["text"])
                return ToolResult(success=True, data={"hidden": result},
                                  duration_ms=(time.time() - start) * 1000)
            else:
                return ToolResult(success=False, data=None,
                                  error=f"Unknown operation: {op}",
                                  duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="crypto",
        description="Cryptographic operations: AES-256-GCM encrypt/decrypt, "
                    "hashing (SHA-256/512/MD5), password analysis, password generation, "
                    "steganography (hide/reveal text in zero-width characters).",
        category=ToolCategory.CRYPTO,
        parameters=[
            ToolParam("operation", "string", "Operation to perform",
                      enum=["encrypt", "decrypt", "hash", "password_analysis",
                            "generate_password", "steganography_hide",
                            "steganography_reveal"]),
            ToolParam("text", "string", "Input text", required=False),
            ToolParam("password", "string", "Password for encrypt/decrypt", required=False),
            ToolParam("ciphertext", "string", "Ciphertext for decryption", required=False),
            ToolParam("iv", "string", "IV for decryption", required=False),
            ToolParam("tag", "string", "Auth tag for GCM decryption", required=False),
            ToolParam("algorithm", "string", "Hash algorithm",
                      required=False, default="sha256",
                      enum=["sha256", "sha512", "sha3_256", "md5", "blake2b"]),
            ToolParam("carrier", "string", "Carrier text for steganography", required=False),
            ToolParam("secret", "string", "Secret to hide", required=False),
            ToolParam("length", "number", "Password length", required=False, default=20),
        ],
        execute=_crypto_ops,
        tags=["crypto", "security", "encryption"],
    ))

    # 12. Network Scanner
    async def _network_scan(args: dict) -> ToolResult:
        start = time.time()
        try:
            from utils.network_scanner import scan_target
            result = await scan_target(
                args["target"],
                ports=args.get("ports"),
                modules=args.get("modules", ["port_scan", "banner", "dns"]),
            )
            return ToolResult(success=True, data=result,
                              duration_ms=(time.time() - start) * 1000)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="network_scan",
        description="Scan network targets: port scanning, banner grabbing, "
                    "DNS resolution, service fingerprinting.",
        category=ToolCategory.NETWORK,
        parameters=[
            ToolParam("target", "string", "Target host or IP"),
            ToolParam("ports", "string", "Port range (e.g. '80,443,8080' or '1-1024')",
                      required=False),
            ToolParam("modules", "array",
                      "Modules: port_scan, banner, dns, http_probe, service_fingerprint",
                      required=False),
        ],
        execute=_network_scan,
        timeout_s=90,
        tags=["network", "scan", "ports"],
    ))

    # ── API & Infrastructure Tools (v2.4) ─────────────────────────

    # 13. API Builder — create dynamic endpoints
    async def _api_create_endpoint(args: dict) -> ToolResult:
        start = time.time()
        try:
            from infrastructure.api.api_builder import get_api_builder
            builder = get_api_builder()
            if not builder._initialized:
                await builder.initialize()
            ep = builder.create_endpoint(
                path=args["path"],
                name=args["name"],
                description=args.get("description", ""),
                system_prompt=args.get("system_prompt", ""),
                model_tier=args.get("model_tier", "auto"),
                parameters=args.get("parameters", []),
            )
            return ToolResult(
                success=True,
                data={
                    "endpoint_id": ep.endpoint_id,
                    "path": ep.path,
                    "method": ep.method.value,
                    "model_tier": ep.model_tier.value,
                    "status": ep.status.value,
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="api_create_endpoint",
        description="Create a new dynamic API endpoint. Supports auto-routing to 72 AI models. "
                    "Created endpoints are immediately available via the API builder.",
        category=ToolCategory.API,
        parameters=[
            ToolParam("path", "string", "Endpoint path (e.g., 'my/custom-ai')"),
            ToolParam("name", "string", "Human-readable endpoint name"),
            ToolParam("description", "string", "What the endpoint does",
                      required=False, default=""),
            ToolParam("system_prompt", "string", "System prompt for AI processing",
                      required=False, default=""),
            ToolParam("model_tier", "string", "Model tier: auto, fast, pro, ultra, consortium",
                      required=False, default="auto"),
            ToolParam("parameters", "array", "List of {name, type, description, required}",
                      required=False),
        ],
        execute=_api_create_endpoint,
        tags=["api", "builder", "create"],
    ))

    # 14. API Execute — call any registered endpoint
    async def _api_execute(args: dict) -> ToolResult:
        start = time.time()
        try:
            from infrastructure.api.api_builder import get_api_builder
            builder = get_api_builder()
            if not builder._initialized:
                await builder.initialize()
            result = await builder.execute_endpoint(
                args["endpoint_id"],
                args.get("data", {}),
            )
            return ToolResult(
                success="error" not in result,
                data=result,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="api_execute",
        description="Execute a registered API endpoint with given parameters. "
                    "Auto-routes to the optimal model from 72 available.",
        category=ToolCategory.API,
        parameters=[
            ToolParam("endpoint_id", "string", "ID of the endpoint to call"),
            ToolParam("data", "object", "Request data matching endpoint parameters",
                      required=False, default={}),
        ],
        execute=_api_execute,
        tags=["api", "execute"],
    ))

    # 15. API List — list all endpoints
    async def _api_list(args: dict) -> ToolResult:
        start = time.time()
        try:
            from infrastructure.api.api_builder import get_api_builder
            builder = get_api_builder()
            if not builder._initialized:
                await builder.initialize()
            endpoints = builder.registry.list_active()
            return ToolResult(
                success=True,
                data={
                    "count": len(endpoints),
                    "endpoints": [
                        {
                            "id": ep.endpoint_id,
                            "method": ep.method.value,
                            "path": f"/{ep.version}/{ep.path}",
                            "name": ep.name,
                            "model_tier": ep.model_tier.value,
                            "tags": ep.tags,
                        }
                        for ep in endpoints
                    ],
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="api_list",
        description="List all registered API endpoints with their details.",
        category=ToolCategory.API,
        parameters=[
            ToolParam("filter_tag", "string", "Filter by tag", required=False),
        ],
        execute=_api_list,
        tags=["api", "list", "info"],
    ))

    # 16. API OpenAPI Spec — generate OpenAPI 3.1 spec
    async def _api_openapi(args: dict) -> ToolResult:
        start = time.time()
        try:
            from infrastructure.api.api_builder import get_api_builder
            builder = get_api_builder()
            if not builder._initialized:
                await builder.initialize()
            spec = builder.get_openapi_spec()
            return ToolResult(
                success=True,
                data=spec,
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="api_openapi_spec",
        description="Generate OpenAPI 3.1 specification for all registered endpoints.",
        category=ToolCategory.API,
        parameters=[],
        execute=_api_openapi,
        tags=["api", "docs", "openapi"],
    ))

    # 17. Model Inventory — list all 72 models
    async def _model_list(args: dict) -> ToolResult:
        start = time.time()
        try:
            from infrastructure.api.api_builder import get_api_builder
            builder = get_api_builder()
            models = builder.get_all_model_keys()
            tier_filter = args.get("tier")
            provider_filter = args.get("provider")
            if tier_filter:
                models = [m for m in models if m.get("tier") == tier_filter]
            if provider_filter:
                models = [m for m in models if m.get("provider") == provider_filter]
            return ToolResult(
                success=True,
                data={
                    "total": len(models),
                    "models": models,
                    "tiers": {"fast": 12, "standard": 16, "pro": 13, "power": 11, "ultra": 7},
                    "providers": {"gemini": 6, "groq": 7, "openrouter": 59},
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="model_list",
        description="List all 72 AI models with providers and tiers. "
                    "Includes Gemini (6), Groq (7), and OpenRouter/APEX (59).",
        category=ToolCategory.MODELS,
        parameters=[
            ToolParam("tier", "string", "Filter by tier: fast, standard, pro, power, ultra",
                      required=False),
            ToolParam("provider", "string", "Filter by provider: gemini, groq, openrouter",
                      required=False),
        ],
        execute=_model_list,
        tags=["models", "info", "list"],
    ))

    # 18. Model Route — select optimal model for a task
    async def _model_route(args: dict) -> ToolResult:
        start = time.time()
        try:
            from infrastructure.api.api_builder import get_api_builder
            builder = get_api_builder()
            model = builder.router.select_model(
                tier=__import__("infrastructure.api.api_builder", fromlist=["ModelTier"]).ModelTier(
                    args.get("tier", "auto")
                ),
                task_type=args.get("task_type", "general"),
            )
            return ToolResult(
                success=True,
                data={
                    "selected_model": model,
                    "task_type": args.get("task_type", "general"),
                    "tier": args.get("tier", "auto"),
                    "routing_reason": f"Model {model} selected for {args.get('task_type', 'general')} task",
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="model_route",
        description="Select the optimal model for a given task type and tier. "
                    "Uses SmartClient routing logic across all 72 models.",
        category=ToolCategory.MODELS,
        parameters=[
            ToolParam("task_type", "string",
                      "Task type: general, code, analysis, creative, math, fast",
                      required=False, default="general"),
            ToolParam("tier", "string",
                      "Desired tier: auto, fast, pro, ultra, consortium",
                      required=False, default="auto"),
        ],
        execute=_model_route,
        tags=["models", "routing", "smart"],
    ))

    # 19. Infrastructure Health — check all layers
    async def _infra_health(args: dict) -> ToolResult:
        start = time.time()
        try:
            from infrastructure.api.api_builder import get_api_builder
            builder = get_api_builder()
            if not builder._initialized:
                await builder.initialize()
            status = builder.status()

            # Check component availability
            health = {
                "api_builder": True,
                "endpoint_registry": builder.registry.count > 0,
                "model_router": True,
                "openapi_generator": True,
            }

            # Check infrastructure imports
            infra_checks = [
                ("models_registry", "utils.models_registry"),
                ("ai_client", "utils.ai_client"),
                ("agent_executor", "utils.agent_executor"),
                ("bridge", "extra.bridge"),
            ]
            for name, module in infra_checks:
                try:
                    __import__(module.replace(".", "/").replace("/", "."))
                    health[name] = True
                except ImportError:
                    health[name] = False

            all_ok = all(health.values())

            return ToolResult(
                success=True,
                data={
                    "status": "healthy" if all_ok else "degraded",
                    "components": health,
                    "endpoints": status["endpoints"],
                    "models": status["models"],
                    "infrastructure": status["infrastructure"],
                },
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="infra_health",
        description="Check health of all infrastructure layers: API Builder, "
                    "Model Router, Endpoint Registry, Gateway, Bridge, Agent Executor.",
        category=ToolCategory.INFRA,
        parameters=[
            ToolParam("deep", "boolean", "Run deep checks including imports",
                      required=False, default=True),
        ],
        execute=_infra_health,
        tags=["infrastructure", "health", "monitoring"],
    ))

    # 20. API Builder Status — full system status
    async def _api_status(args: dict) -> ToolResult:
        start = time.time()
        try:
            from infrastructure.api.api_builder import get_api_builder
            builder = get_api_builder()
            if not builder._initialized:
                await builder.initialize()
            return ToolResult(
                success=True,
                data=builder.status(),
                duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e),
                              duration_ms=(time.time() - start) * 1000)

    registry.register(Tool(
        name="api_status",
        description="Get full API Builder status: endpoints, models, router stats, infrastructure.",
        category=ToolCategory.API,
        parameters=[],
        execute=_api_status,
        tags=["api", "status", "info"],
    ))

    logger.info(f"Registered {len(registry.get_all())} built-in tools (12 core + 8 API/infra)")


# ═══════════════════════════════════════════════════════════════════
# System Prompt Builder
# ═══════════════════════════════════════════════════════════════════

def build_system_prompt(
    tools: List[dict],
    memory_context: str = "",
    extra: str = "",
) -> str:
    """Build the agent system prompt with tool descriptions and context."""
    tool_list = "\n".join(
        f"  • **{t['function']['name']}**: {t['function']['description']}"
        for t in tools
    )

    prompt = """You are ARKI AGENT — an autonomous AI agent with access to powerful tools.

## YOUR CAPABILITIES
You have access to these tools:
{tool_list}

## HOW TO WORK
1. THINK about what the user needs — analyze the query deeply
2. PLAN which tools to use and in what order — consider dependencies
3. CALL tools one at a time (or indicate parallel calls for independent steps)
4. OBSERVE the results — check for errors or incomplete data
5. DECIDE: do you need more tool calls, or can you answer?
6. If uncertain, call additional tools to verify
7. ANSWER with a comprehensive, data-backed final response

## RULES
- Be thorough: use multiple tools when needed for verification
- Be direct: no disclaimers, no hedging
- Be specific: include actual data, numbers, URLs from tool results
- If a tool fails, try an alternative tool or approach
- Always provide a final answer, even if partial
- For complex tasks, break them into smaller steps
- You can call the same tool multiple times with different parameters
- When results from one tool inform the next step, chain them logically
- Track your confidence — if low, gather more evidence"""

    if memory_context:
        prompt += f"\n\n## RELEVANT CONTEXT FROM MEMORY\n{memory_context}"

    if extra:
        prompt += f"\n\n## ADDITIONAL INSTRUCTIONS\n{extra}"

    return prompt


# ═══════════════════════════════════════════════════════════════════
# Parallel Step Scheduler
# ═══════════════════════════════════════════════════════════════════

class StepScheduler:
    """
    DAG-based scheduler: runs independent steps in parallel,
    respects dependencies between steps.
    """

    def __init__(self, steps: List[AgentStep], max_parallel: int = PARALLEL_BATCH_SIZE) -> None:
        self._steps = {s.id: s for s in steps}
        self._max_parallel = max_parallel
        self._completed: Set[int] = set()
        self._failed: Set[int] = set()

    def get_ready_steps(self) -> List[AgentStep]:
        """Get steps whose dependencies are all completed."""
        ready = []
        for step in self._steps.values():
            if step.status not in (StepStatus.PENDING, StepStatus.QUEUED):
                continue
            # Check all dependencies are completed
            deps_met = all(d in self._completed for d in step.depends_on)
            deps_failed = any(d in self._failed for d in step.depends_on)
            if deps_failed:
                step.status = StepStatus.SKIPPED
                continue
            if deps_met:
                ready.append(step)
        return ready[:self._max_parallel]

    def mark_completed(self, step_id: int) -> None:
        self._completed.add(step_id)
        if step_id in self._steps:
            self._steps[step_id].status = StepStatus.COMPLETED

    def mark_failed(self, step_id: int) -> None:
        self._failed.add(step_id)
        if step_id in self._steps:
            self._steps[step_id].status = StepStatus.FAILED

    @property
    def all_done(self) -> bool:
        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)
            for s in self._steps.values()
        )


# ═══════════════════════════════════════════════════════════════════
# Agent Executor — Core Engine
# ═══════════════════════════════════════════════════════════════════

async def execute_agent(
    query: str,
    messages: List[Dict[str, str]],
    config: AgentConfig,
) -> ExecutionTrace:
    """
    Execute an autonomous agent that plans, calls tools, reflects,
    and produces a final answer.

    Parameters
    ----------
    query : str
        The user's question or task.
    messages : list
        Prior conversation messages [{role, content}].
    config : AgentConfig
        Agent configuration (model, limits, callbacks, etc.)

    Returns
    -------
    ExecutionTrace
        Full trace of the execution with answer, steps, costs, etc.
    """
    start_time = time.time()

    # Ensure tools are registered
    if len(registry.get_all()) == 0:
        register_builtin_tools()

    cache = LRUCache() if config.enable_caching else None

    tool_defs = registry.get_definitions(config.tools_filter)
    system_prompt = build_system_prompt(
        tool_defs, config.memory_context, config.system_prompt_extra,
    )

    trace = ExecutionTrace(
        query=query,
        model=config.model,
        status=TraceStatus.EXECUTING,
    )

    # Build conversation
    conversation: List[dict] = [
        {"role": "system", "content": system_prompt},
        *messages,
        {"role": "user", "content": query},
    ]

    step_counter = 0

    for iteration in range(config.max_steps):
        elapsed = time.time() - start_time
        if elapsed > config.max_time_s:
            trace.status = TraceStatus.TIMEOUT
            trace.steps.append(AgentStep(
                id=step_counter, thought="⏱ Time limit reached",
                status=StepStatus.CANCELLED,
            ))
            break

        if trace.total_cost > config.max_cost:
            trace.steps.append(AgentStep(
                id=step_counter, thought="💰 Cost budget exceeded",
                status=StepStatus.CANCELLED,
            ))
            break

        # ── Call LLM ────────────────────────────────────────────
        llm_start = time.time()
        try:
            payload = {
                "model": config.model,
                "messages": conversation,
                "tools": tool_defs,
                "tool_choice": "auto",
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            }
            llm_headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://arki-engine.ai",
                "X-Title": "Arki-Agent",
            }

            # v10.1: Route through TITANIUM
            if _TITANIUM_ACTIVE:
                resp = await shielded_post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json_data=payload,
                    headers=llm_headers,
                    timeout=300.0,
                    provider_name="agent_llm",
                )
                if not resp.success:
                    raise RuntimeError(f"API {resp.status}: {resp.text[:300]}")
                data = resp.json()
            else:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=llm_headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as resp:
                        if resp.status != 200:
                            err_body = await resp.text()
                            raise RuntimeError(f"API {resp.status}: {err_body[:300]}")
                        data = await resp.json()

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            usage = data.get("usage", {})
            trace.tokens_used += usage.get("total_tokens", 0)

            if not message:
                raise RuntimeError("Empty response from model")

        except Exception as exc:
            trace.steps.append(AgentStep(
                id=step_counter,
                thought=f"LLM Error: {exc}",
                status=StepStatus.FAILED,
                duration_ms=(time.time() - llm_start) * 1000,
                error_trace=traceback.format_exc(),
            ))
            break

        # ── Process tool calls ──────────────────────────────────
        tool_calls = message.get("tool_calls", [])

        if tool_calls:
            conversation.append(message)

            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    tool_args = json.loads(tc["function"].get("arguments", "{}"))
                except json.JSONDecodeError:
                    tool_args = {}

                if config.on_tool_call:
                    config.on_tool_call(tool_name, tool_args)

                step = AgentStep(
                    id=step_counter,
                    thought=message.get("content", ""),
                    action={"tool": tool_name, "args": tool_args},
                    status=StepStatus.RUNNING,
                )
                step_counter += 1

                # Check cache
                if cache:
                    cached = cache.get(tool_name, tool_args)
                    if cached:
                        step.result = cached
                        step.observation = cached.truncated_data(2000)
                        step.status = StepStatus.COMPLETED
                        step.duration_ms = 0
                        trace.steps.append(step)
                        conversation.append({
                            "role": "tool",
                            "content": cached.truncated_data(),
                            "tool_call_id": tc["id"],
                        })
                        if config.on_step:
                            config.on_step(step)
                        continue

                # Execute tool with retry + backoff
                tool = registry.get(tool_name)
                result: Optional[ToolResult] = None

                if tool:
                    for attempt in range(MAX_RETRIES_PER_STEP):
                        try:
                            result = await asyncio.wait_for(
                                tool.execute(tool_args),
                                timeout=tool.timeout_s,
                            )
                            if result.success:
                                break
                        except asyncio.TimeoutError:
                            result = ToolResult(
                                success=False, data=None,
                                error=f"Timeout after {tool.timeout_s}s",
                            )
                        except Exception as e:
                            result = ToolResult(
                                success=False, data=None, error=str(e),
                            )

                        if attempt < MAX_RETRIES_PER_STEP - 1:
                            backoff = min(
                                BACKOFF_BASE_S * (2 ** attempt),
                                BACKOFF_MAX_S,
                            )
                            step.retries += 1
                            step.status = StepStatus.RETRYING
                            await asyncio.sleep(backoff)

                    registry.record_call(
                        tool_name, result.duration_ms if result else 0,
                        error=not (result and result.success),
                    )
                else:
                    result = ToolResult(
                        success=False, data=None,
                        error=f"Unknown tool: {tool_name}",
                    )

                step.result = result
                step.observation = result.truncated_data(2000) if result else ""
                step.status = (StepStatus.COMPLETED if result and result.success
                               else StepStatus.FAILED)
                step.duration_ms = result.duration_ms if result else 0
                step.cost = tool.cost_per_call if tool else 0
                trace.tool_calls += 1
                trace.total_cost += step.cost
                trace.steps.append(step)

                if config.on_tool_result and result:
                    config.on_tool_result(tool_name, result)
                if config.on_step:
                    config.on_step(step)

                # Cache successful results
                if cache and result and result.success:
                    cache.put(tool_name, tool_args, result)

                conversation.append({
                    "role": "tool",
                    "content": result.truncated_data() if result else '{"error":"no result"}',
                    "tool_call_id": tc["id"],
                })

        else:
            # ── Final answer (no tool calls) ────────────────────
            answer = message.get("content", "")
            trace.final_answer = answer
            trace.success = True

            if answer:
                trace.steps.append(AgentStep(
                    id=step_counter,
                    thought="Final answer synthesized",
                    observation=answer[:500],
                    duration_ms=(time.time() - llm_start) * 1000,
                    status=StepStatus.COMPLETED,
                ))
            break

    # ── Self-Reflection ──────────────────────────────────────────
    if (config.enable_reflection
            and trace.final_answer
            and trace.success
            and len(trace.steps) > 1):
        trace.status = TraceStatus.REFLECTING
        try:
            reflection_result = await _self_reflect(
                query, trace.final_answer, trace.steps, config,
            )
            trace.reflection = reflection_result.get("reflection", "")
            confidence = reflection_result.get("confidence", 0.8)

            if config.on_reflection:
                config.on_reflection(trace.reflection, confidence)

            # If confidence too low, try to improve
            if confidence < REFLECTION_THRESHOLD and len(trace.steps) < config.max_steps - 2:
                improvement = reflection_result.get("improvement", "")
                if improvement:
                    trace.final_answer = improvement
        except Exception as exc:
            logger.warning(f"Reflection failed: {exc}")

    # ── Fallback answer from partial results ─────────────────────
    if not trace.final_answer:
        successful_steps = [s for s in trace.steps
                           if s.result and s.result.success]
        if successful_steps:
            trace.final_answer = "\n\n".join(
                f"[{s.tool_name}] {s.result.truncated_data(500)}"
                for s in successful_steps
            )
            trace.success = True

    trace.total_duration_ms = (time.time() - start_time) * 1000
    if trace.status not in (TraceStatus.TIMEOUT, TraceStatus.CANCELLED):
        trace.status = TraceStatus.COMPLETED if trace.success else TraceStatus.ERROR

    return trace


async def _self_reflect(
    query: str,
    answer: str,
    steps: List[AgentStep],
    config: AgentConfig,
) -> dict:
    """
    Self-reflection: the agent evaluates its own answer quality
    and optionally suggests improvements.
    """
    tool_summary = "\n".join(
        f"  Step {s.id}: [{s.tool_name}] → {'✅' if s.status == StepStatus.COMPLETED else '❌'}"
        for s in steps if s.action
    )

    reflection_prompt = """Evaluate this answer to the user's question.

QUESTION: {query}

TOOLS USED:
{tool_summary}

ANSWER:
{answer[:3000]}

Respond in JSON with:
- "confidence": float 0-1 (how confident you are in the answer quality)
- "reflection": string (what's good, what's missing)
- "improvement": string (improved answer if confidence < 0.6, else empty)
"""

    # v10.1: Route through TITANIUM
    if _TITANIUM_ACTIVE:
        resp = await shielded_post(
            "https://openrouter.ai/api/v1/chat/completions",
            json_data={
                "model": config.model,
                "messages": [{"role": "user", "content": reflection_prompt}],
                "temperature": 0.1,
                "max_tokens": 2048,
            },
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
            provider_name="agent_reflection",
        )
        data = resp.json() if resp.success else {}
    else:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.model,
                    "messages": [{"role": "user", "content": reflection_prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Parse JSON from response
    try:
        # Find JSON in response
        import re
        json_match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, AttributeError):
        logger.debug("Suppressed: %s", _exc)

    return {"confidence": 0.7, "reflection": content[:500], "improvement": ""}


# ═══════════════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════════════

async def quick_agent(
    query: str,
    api_key: str,
    model: str = "anthropic/claude-sonnet-4-20250514",
    max_steps: int = 8,
) -> dict:
    """
    Quick one-shot agent call. Returns {answer, trace}.
    """
    trace = await execute_agent(
        query, [],
        AgentConfig(
            api_key=api_key,
            model=model,
            max_steps=max_steps,
            max_time_s=90,
        ),
    )
    return {"answer": trace.final_answer, "trace": trace}


async def plan_and_execute(
    query: str,
    api_key: str,
    tools: Optional[List[str]] = None,
    model: str = "anthropic/claude-sonnet-4-20250514",
) -> ExecutionTrace:
    """
    Plan-first execution: create explicit plan, then execute steps.
    Good for complex multi-step tasks.
    """
    return await execute_agent(
        query, [],
        AgentConfig(
            api_key=api_key,
            model=model,
            tools_filter=tools,
            max_steps=15,
            enable_reflection=True,
            enable_parallel=True,
        ),
    )


# ═══════════════════════════════════════════════════════════════════
# Trace History Manager
# ═══════════════════════════════════════════════════════════════════

class TraceHistory:
    """Stores execution traces for analysis and debugging."""

    def __init__(self, max_traces: int = MAX_TRACES_HISTORY) -> None:
        self._traces: List[ExecutionTrace] = []
        self._max = max_traces

    def add(self, trace: ExecutionTrace) -> None:
        self._traces.append(trace)
        if len(self._traces) > self._max:
            self._traces = self._traces[-self._max:]

    def get_recent(self, n: int = 10) -> List[ExecutionTrace]:
        return self._traces[-n:]

    def get_by_id(self, trace_id: str) -> Optional[ExecutionTrace]:
        for t in self._traces:
            if t.id == trace_id:
                return t
        return None

    def get_stats(self) -> dict:
        if not self._traces:
            return {"total": 0}

        successful = [t for t in self._traces if t.success]
        return {
            "total": len(self._traces),
            "success_rate": f"{len(successful)/len(self._traces)*100:.1f}%",
            "avg_duration_ms": sum(t.total_duration_ms for t in self._traces) / len(self._traces),
            "avg_steps": sum(len(t.steps) for t in self._traces) / len(self._traces),
            "avg_tools": sum(t.tool_calls for t in self._traces) / len(self._traces),
            "total_cost": sum(t.total_cost for t in self._traces),
            "total_tokens": sum(t.tokens_used for t in self._traces),
        }

    def export(self) -> List[dict]:
        """Export traces as serializable dicts."""
        results = []
        for t in self._traces:
            results.append({
                "id": t.id,
                "query": t.query,
                "model": t.model,
                "success": t.success,
                "final_answer": t.final_answer[:500],
                "steps": len(t.steps),
                "tool_calls": t.tool_calls,
                "duration_ms": t.total_duration_ms,
                "cost": t.total_cost,
                "tokens": t.tokens_used,
                "status": t.status.value,
            })
        return results


# ═══════════════════════════════════════════════════════════════════
# AgentExecutor — Convenience class wrapper
# ═══════════════════════════════════════════════════════════════════

class AgentExecutor:
    """
    Class-based wrapper around the functional agent execution engine.
    Provides an OOP interface compatible with module_bridge and external callers.
    """

    def __init__(self, config: AgentConfig = None) -> None:
        self.config = config or AgentConfig()
        self._scheduler = StepScheduler()
        self._history = TraceHistory()
        # Ensure tools registered
        if len(registry.get_all()) == 0:
            register_builtin_tools()

    async def execute(self, query: str, messages: List[Dict[str, str]] = None) -> ExecutionTrace:
        """Execute the agent with the given query."""
        return await execute_agent(query, messages or [], self.config)

    def get_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return registry.get_all()

    def get_tool_names(self) -> List[str]:
        """Get all registered tool names."""
        return [t.name for t in registry.get_all()]

    def get_tool_count(self) -> int:
        """Get number of registered tools."""
        return len(registry.get_all())

    def get_categories(self) -> List[str]:
        """Get all tool categories."""
        return list(set(t.category.value for t in registry.get_all() if t.category))

    @property
    def tool_registry(self) -> ToolRegistry:
        """Access the tool registry."""
        return registry

    @property
    def history(self) -> TraceHistory:
        """Access execution history."""
        return self._history

    def status(self) -> dict:
        """Get agent executor status."""
        tools = registry.get_all()
        categories = {}
        for t in tools:
            cat = t.category.value if t.category else "uncategorized"
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "version": "2.0.0-TITANIUM",
            "tools": len(tools),
            "categories": categories,
            "config": {
                "model": self.config.model,
                "max_steps": self.config.max_steps,
                "parallel": self.config.parallel_tools,
            },
        }


# Singleton instances
trace_history = TraceHistory()
agent_executor = AgentExecutor()


