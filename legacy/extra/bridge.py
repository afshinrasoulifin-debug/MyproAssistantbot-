
from __future__ import annotations
"""
tg_bot/extra/bridge.py
──────────────────────
HTTP bridge to the APEX API server running locally on port 7860.

The ENTIRE APEX project runs UNTOUCHED as a Node.js service.
This bridge simply forwards Telegram commands → HTTP API calls → responses.

NO APEX code is modified, translated, or simplified.
"""


# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════


# ── Infrastructure Integration ──
try:
    from extra.infra_connector import get_apex_connector as _get_apex_infra
    _apex_infra = _get_apex_infra()
except ImportError:
    _apex_infra = None



import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────

APEX_PORT = int(os.environ.get("APEX_PORT", "7860"))
APEX_HOST = os.environ.get("APEX_HOST", "127.0.0.1")  # v29.0: configurable for Docker
APEX_BASE = f"http://{APEX_HOST}:{APEX_PORT}"
APEX_API = f"{APEX_BASE}/v1"

# ── Enterprise unlock ────────────────────────────────────────────────
# We run APEX locally, so we set an internal API key with enterprise tier.
# This unlocks ALL 56+ models, ALL 5 tiers, NO rate limits, NO filters.
# The APEX source code is NOT touched — only env vars are set.
# v25.0 AUTONOMOUS: APEX_INTERNAL_KEY is optional enhancement
_INTERNAL_API_KEY = os.environ.get("APEX_INTERNAL_KEY", "")
if not _INTERNAL_API_KEY:
    import secrets as _sec
    _INTERNAL_API_KEY = _sec.token_hex(32)  # Auto-generate for local bridge
    os.environ["APEX_INTERNAL_KEY"] = _INTERNAL_API_KEY
    import logging as _log
    _log.getLogger(__name__).info("🤖 APEX_INTERNAL_KEY auto-generated for autonomous bridge")

# Shared httpx client (connection pool — includes enterprise auth header)
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=APEX_API,
            headers={
                "Authorization": f"Bearer {_INTERNAL_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(connect=5, read=120, write=10, pool=5),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── APEX Server Lifecycle ────────────────────────────────────────

_server_process: subprocess.Popen | None = None


def _find_node() -> str:
    """Find a working node binary."""
    import shutil

    # Try system node first (most reliable in production)
    node = shutil.which("node")
    if node:
        return node

    # Fallback paths for specific environments
    candidates = [
        "/usr/local/bin/node",
        "/usr/bin/node",
        os.path.expanduser("~/.nvm/current/bin/node"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    raise RuntimeError("Node.js not found — install Node.js 18+ to enable APEX features")


def _find_apex_dir() -> str:
    """Find the APEX project directory."""
    # Primary: relative to this file (works in any deployment)
    primary = os.path.join(os.path.dirname(__file__), "apex_app")
    if os.path.isdir(primary) and os.path.isfile(os.path.join(primary, "api", "server.ts")):
        return primary
    raise RuntimeError("APEX project directory not found at: " + primary)


def _find_npx() -> str:
    """Find npx binary."""
    import shutil

    # Try system npx first
    npx = shutil.which("npx")
    if npx:
        return npx

    candidates = [
        "/usr/local/bin/npx",
        "/usr/bin/npx",
        os.path.expanduser("~/.nvm/current/bin/npx"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    raise RuntimeError("npx not found — install Node.js 18+ to enable APEX features")


async def start_apex_server() -> bool:
    """Start the APEX API server as a subprocess."""
    global _server_process

    # Check if already running
    if await is_server_running():
        logger.info("APEX API server already running on port %d", APEX_PORT)
        return True

    try:
        node_bin = _find_node()
        g0d_dir = _find_apex_dir()
        npx_bin = _find_npx()

        # Build environment
        env = os.environ.copy()
        env["PORT"] = str(APEX_PORT)
        env["CORS_ORIGIN"] = "*"
        env["PATH"] = os.path.dirname(node_bin) + ":" + os.path.dirname(npx_bin) + ":" + env.get("PATH", "")

        # ── Enterprise unlock (NO code changes — env vars only) ──────
        # Set an internal API key and map it to enterprise tier.
        # This unlocks: ALL 56+ models, ALL 5 tiers (fast/standard/smart/power/ultra),
        # unlimited rate limits, full research API, dataset export, metadata events.
        env["APEX_API_KEY"] = _INTERNAL_API_KEY
        env["APEX_TIER_KEYS"] = f"enterprise:{_INTERNAL_API_KEY}"
        env["RATE_LIMIT_TOTAL"] = "0"   # unlimited lifetime requests
        env["RATE_LIMIT_PER_MINUTE"] = "999999"
        env["RATE_LIMIT_PER_DAY"] = "9999999"

        # v9.7.1: Force enterprise unlocks
        env["APEX_ENTERPRISE"] = "true"
        env["APEX_NO_RATE_LIMIT"] = "true"
        env["APEX_NO_FILTER"] = "true"
        env["APEX_ALL_TIERS"] = "true"

        # Forward OpenRouter API key if available
        or_key = os.environ.get("OPENROUTER_API_KEY", "")
        if or_key:
            env["OPENROUTER_API_KEY"] = or_key

        logger.info("Starting APEX API server: %s tsx api/server.ts", npx_bin)
        logger.info("  Directory: %s", g0d_dir)
        logger.info("  Port: %d", APEX_PORT)
        logger.info("  Node: %s", node_bin)

        _server_process = await asyncio.create_subprocess_exec(
            npx_bin, "tsx", "api/server.ts",
            cwd=g0d_dir,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        # Wait for server to be ready (up to 15 seconds)
        for i in range(30):
            await asyncio.sleep(0.5)
            if await is_server_running():
                logger.info("✅ APEX API server ready (took %.1fs)", (i + 1) * 0.5)
                return True

            # Check if process died
            if _server_process.returncode is not None:
                stdout = (await _server_process.stdout.read()).decode() if _server_process.stdout else ""
                logger.error("APEX server died: %s", stdout[-500:])
                return False

        logger.error("APEX server did not become ready in 15s")
        return False

    except Exception as exc:
        logger.error("Failed to start APEX server: %s", exc)
        return False


async def stop_apex_server() -> None:
    """Stop the APEX API server."""
    global _server_process
    if _server_process and _server_process.poll() is None:
        _server_process.terminate()
        try:
            _server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _server_process.kill()
        logger.info("APEX API server stopped")
    _server_process = None
    await close_client()


async def is_server_running() -> bool:
    """Check if the APEX API server is responsive."""
    try:
        client = _get_client()
        resp = await client.get("/health", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


# ── API Call Helpers ─────────────────────────────────────────────────

@dataclass
class APIResponse:
    success: bool
    data: dict = field(default_factory=dict)
    error: str = ""
    status_code: int = 0


async def api_get(path: str, params: dict | None = None) -> APIResponse:
    """GET request to APEX API."""
    try:
        # v10.1: Route through TITANIUM shielded client
        if _TITANIUM_ACTIVE:
            full_url = f"{APEX_API.rstrip('/')}/{path.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {_INTERNAL_API_KEY}",
                "Content-Type": "application/json",
            }
            ti_resp = await shielded_get(full_url, headers=headers, timeout=120.0)
            if ti_resp.success:
                data = ti_resp.json()
                status = ti_resp.status_code
                if status >= 400:
                    return APIResponse(success=False, data=data, error=data.get("error", str(data)), status_code=status)
                return APIResponse(success=True, data=data, status_code=status)
            else:
                # Fallback to raw client on TITANIUM failure
                pass
        client = _get_client()
        resp = await client.get(path, params=params)
        data = resp.json()
        if resp.status_code >= 400:
            return APIResponse(success=False, data=data, error=data.get("error", str(data)), status_code=resp.status_code)
        return APIResponse(success=True, data=data, status_code=resp.status_code)
    except Exception as exc:
        return APIResponse(success=False, error=str(exc))


async def api_post(path: str, body: dict, timeout: float = 120.0) -> APIResponse:
    """POST request to APEX API."""
    try:
        # v10.1: Route through TITANIUM shielded client
        if _TITANIUM_ACTIVE:
            full_url = f"{APEX_API.rstrip('/')}/{path.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {_INTERNAL_API_KEY}",
                "Content-Type": "application/json",
            }
            ti_resp = await shielded_post(full_url, json_data=body, headers=headers, timeout=timeout)
            if ti_resp.success:
                data = ti_resp.json()
                status = ti_resp.status_code
                if status >= 400:
                    err = data.get("error", {})
                    if isinstance(err, dict):
                        err = err.get("message", str(err))
                    return APIResponse(success=False, data=data, error=str(err), status_code=status)
                return APIResponse(success=True, data=data, status_code=status)
            else:
                pass  # Fallback to raw client
        client = _get_client()
        resp = await client.post(path, json=body, timeout=timeout)
        data = resp.json()
        if resp.status_code >= 400:
            err = data.get("error", {})
            if isinstance(err, dict):
                err = err.get("message", str(err))
            return APIResponse(success=False, data=data, error=str(err), status_code=resp.status_code)
        return APIResponse(success=True, data=data, status_code=resp.status_code)
    except httpx.ReadTimeout:
        return APIResponse(success=False, error="Timeout — the request took too long")
    except Exception as exc:
        return APIResponse(success=False, error=str(exc))


async def api_post_stream(path: str, body: dict, timeout: float = 120.0) -> Any:
    """POST request with SSE streaming to APEX API. Yields parsed SSE events."""
    try:
        client = _get_client()
        async with client.stream("POST", path, json=body, timeout=timeout) as resp:
            if resp.status_code >= 400:
                data = json.loads(await resp.aread())
                yield {"error": data}
                return

            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload == "[DONE]":
                        yield {"done": True}
                        return
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError:
                        continue
    except Exception as exc:
        yield {"error": str(exc)}


# ── High-level API Functions ─────────────────────────────────────────

async def get_info() -> APIResponse:
    return await api_get("/info")


async def get_models() -> APIResponse:
    """Get models list. Falls back to tier info if /models endpoint errors."""
    resp = await api_get("/models")
    if resp.success:
        return resp
    # Original APEX /v1/models has a known bug (references .full instead of
    # actual tier names). Work around it by building the model list from tier info.
    # This does NOT modify any APEX code — just handles the error gracefully.
    try:
        info = await api_get("/info")
        if not info.success:
            return resp  # Return original error
        # Build from known tier structure (from ultraplinian.ts source)
        tier_counts = {"fast": 12, "standard": 16, "smart": 13, "power": 11, "ultra": 7}
        total = sum(tier_counts.values())  # 59
        return APIResponse(
            success=True,
            data={
                "object": "list",
                "data": [],  # Individual models unavailable due to API bug
                "total_count": total,
                "tier_counts": tier_counts,
                "note": "Model list from tier data (59 total across 5 tiers)",
            },
        )
    except Exception:
        return resp


async def get_health() -> APIResponse:
    return await api_get("/health")


async def analyze_autotune(message: str) -> APIResponse:
    return await api_post("/autotune/analyze", {"message": message})


async def encode_parseltongue(text: str, technique: str = "leetspeak", intensity: str = "medium") -> APIResponse:
    return await api_post("/parseltongue/encode", {
        "text": text,
        "technique": technique,
        "intensity": intensity,
    })


async def detect_parseltongue(text: str) -> APIResponse:
    return await api_post("/parseltongue/detect", {"text": text})


async def transform_stm(text: str, modules: list[str]) -> APIResponse:
    return await api_post("/transform", {"text": text, "modules": modules})


async def submit_feedback(response_id: str, rating: str, context_type: str = "general") -> APIResponse:
    return await api_post("/feedback", {
        "response_id": response_id,
        "rating": rating,
        "context_type": context_type,
    })


async def chat_completion(
    messages: list[dict],
    model: str = "google/gemini-2.5-pro",
    openrouter_api_key: str | None = None,
    apex: bool = False,
    autotune: bool = False,
    parseltongue: bool = False,
    stm_modules: list[str] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    stream: bool = False,
) -> APIResponse:
    """Chat completion via APEX pipeline — v25.0 AUTONOMOUS."""
    # v25.0: If no API key, try to route model to :free variant
    use_model = model
    if not openrouter_api_key:
        try:
            from arki_project.utils.free_access_router import OPENROUTER_FREE_MODELS
            free_v = OPENROUTER_FREE_MODELS.get(model)
            if free_v:
                use_model = free_v
                logger.debug("Bridge AUTONOMOUS: %s → %s", model, use_model)
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)
    body: dict[str, Any] = {
        "messages": messages,
        "model": use_model,
        "stream": stream,
    }
    if openrouter_api_key:
        body["openrouter_api_key"] = openrouter_api_key
    if apex:
        body["apex"] = True
    if autotune:
        body["autotune"] = True
    if parseltongue:
        body["parseltongue"] = True
    if stm_modules:
        body["stm_modules"] = stm_modules
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens is not None:
        body["max_tokens"] = max_tokens

    return await api_post("/chat/completions", body, timeout=120.0)


async def ultraplinian_completion(
    messages: list[dict],
    tier: str = "fast",
    openrouter_api_key: str | None = None,
    apex: bool = False,
    autotune: bool = False,
    parseltongue: bool = False,
    stm_modules: list[str] | None = None,
    stream: bool = True,
    liquid_min_delta: int = 8,
    max_tokens: int | None = None,
) -> APIResponse:
    """ULTRAPLINIAN multi-model racing via APEX."""
    body: dict[str, Any] = {
        "messages": messages,
        "tier": tier,
        "stream": stream,
        "liquid_min_delta": liquid_min_delta,
    }
    if openrouter_api_key:
        body["openrouter_api_key"] = openrouter_api_key
    if apex:
        body["apex"] = True
    if autotune:
        body["autotune"] = True
    if parseltongue:
        body["parseltongue"] = True
    if stm_modules:
        body["stm_modules"] = stm_modules
    if max_tokens is not None:
        body["max_tokens"] = max_tokens

    return await api_post("/ultraplinian/completions", body, timeout=120.0)


async def consortium_completion(
    messages: list[dict],
    tier: str = "fast",
    openrouter_api_key: str | None = None,
    apex: bool = False,
    autotune: bool = False,
    parseltongue: bool = False,
    stm_modules: list[str] | None = None,
    max_tokens: int | None = None,
) -> APIResponse:
    """CONSORTIUM hive-mind synthesis via APEX."""
    body: dict[str, Any] = {
        "messages": messages,
        "tier": tier,
        "stream": False,  # Consortium collects all then synthesizes
    }
    if openrouter_api_key:
        body["openrouter_api_key"] = openrouter_api_key
    if apex:
        body["apex"] = True
    if autotune:
        body["autotune"] = True
    if parseltongue:
        body["parseltongue"] = True
    if stm_modules:
        body["stm_modules"] = stm_modules
    if max_tokens is not None:
        body["max_tokens"] = max_tokens

    return await api_post("/consortium/completions", body, timeout=180.0)


async def get_dataset_stats() -> APIResponse:
    return await api_get("/dataset/stats")


async def get_metadata_stats() -> APIResponse:
    return await api_get("/metadata/stats")


async def get_tier_info() -> APIResponse:
    return await api_get("/tier")


# ═══════════════════════════════════════════════════════════════════
# Agent Executor Bridge (v2.4)
# ═══════════════════════════════════════════════════════════════════

async def agent_execute(
    query: str,
    model: str = "anthropic/claude-3.5-sonnet",
    openrouter_api_key: str | None = None,
    max_steps: int = 50,
    tools: list[str] | None = None,
    max_time_ms: int = 600000,
    temperature: float = 0.3,
) -> APIResponse:
    """Execute autonomous agent via APEX (TS) with 20 tools.

    The agent has access to: web_search, academic_search, code_search,
    deep_crawl, web_recon, google_dork, web_automate, execute_code,
    http_request, analyze_text, transform_data, encode_decode,
    + 8 new API/infra tools (api_create_endpoint, model_list, model_route,
    api_execute, api_openapi_spec, infra_health, batch_model_test, api_status).
    """
    body: dict[str, Any] = {
        "query": query,
        "model": model,
        "max_steps": max_steps,
        "max_time_ms": max_time_ms,
        "temperature": temperature,
    }
    if openrouter_api_key:
        body["openrouter_api_key"] = openrouter_api_key
    else:
        # v25.0 AUTONOMOUS: Try provisioned key, then env, then empty (free tier)
        _bk = os.environ.get("OPENROUTER_API_KEY", "")
        if not _bk:
            try:
                from arki_project.utils.free_access_router import get_free_router
                _bk = (get_free_router()._provisioned_keys.get("openrouter_free", [None]) or [None])[0] or ""
            except Exception:
                _bk = ""
        if _bk:
            body["openrouter_api_key"] = _bk
    if tools:
        body["tools"] = tools
    return await api_post("/advanced/agent/execute", body, timeout=max_time_ms / 1000)


async def agent_quick(
    query: str,
    openrouter_api_key: str | None = None,
) -> APIResponse:
    """Quick single-shot agent call."""
    body: dict[str, Any] = {"query": query}
    if openrouter_api_key:
        body["openrouter_api_key"] = openrouter_api_key
    else:
        # v25.0 AUTONOMOUS: Try provisioned key, then env, then empty (free tier)
        _bk = os.environ.get("OPENROUTER_API_KEY", "")
        if not _bk:
            try:
                from arki_project.utils.free_access_router import get_free_router
                _bk = (get_free_router()._provisioned_keys.get("openrouter_free", [None]) or [None])[0] or ""
            except Exception:
                _bk = ""
        if _bk:
            body["openrouter_api_key"] = _bk
    return await api_post("/advanced/agent/quick", body, timeout=120.0)


async def get_agent_tools() -> APIResponse:
    """List all agent tools (20: 12 core + 8 API/infra)."""
    return await api_get("/advanced/agent/tools")


# ═══════════════════════════════════════════════════════════════════
# Model Testing Bridge (v2.4)
# ═══════════════════════════════════════════════════════════════════

async def test_model(
    model: str,
    prompt: str = "Explain the distributed Saga pattern with Redis Redlock for consistency.",
    openrouter_api_key: str | None = None,
    max_tokens: int = 2048,
) -> APIResponse:
    """Test a single model and get its response + quality score."""
    messages = [{"role": "user", "content": prompt}]
    body: dict[str, Any] = {
        "messages": messages,
        "model": model,
        "max_tokens": max_tokens,
    }
    if openrouter_api_key:
        body["openrouter_api_key"] = openrouter_api_key
    else:
        _bk = os.environ.get("OPENROUTER_API_KEY", "")
        if not _bk:
            try:
                from arki_project.utils.free_access_router import get_free_router
                _bk = (get_free_router()._provisioned_keys.get("openrouter_free", [None]) or [None])[0] or ""
            except Exception:
                _bk = ""
        if _bk:
            body["openrouter_api_key"] = _bk
    return await api_post("/chat/completions", body, timeout=120.0)


async def batch_test_models(
    models: list[str],
    prompt: str = "Explain the CAP theorem and its practical implications for microservices.",
    openrouter_api_key: str | None = None,
    max_parallel: int = 6,
) -> list[dict[str, Any]]:
    """Test multiple models in parallel. Returns list of results."""
    results = []

    async def _test_one(model_key: str) -> dict:
        try:
            resp = await test_model(model_key, prompt, openrouter_api_key)
            return {
                "model": model_key,
                "success": resp.success,
                "response_preview": str(resp.data)[:200] if resp.success else "",
                "error": resp.error if not resp.success else None,
            }
        except Exception as e:
            return {"model": model_key, "success": False, "error": str(e)}

    # Run in batches
    for i in range(0, len(models), max_parallel):
        batch = models[i:i + max_parallel]
        batch_results = await asyncio.gather(*[_test_one(m) for m in batch])
        results.extend(batch_results)

    return results


# ═══════════════════════════════════════════════════════════════════
# API Builder Bridge (v2.4)
# ═══════════════════════════════════════════════════════════════════

async def get_api_builder_status() -> dict[str, Any]:
    """Get API Builder status via the infra connector."""
    if _apex_infra and hasattr(_apex_infra, 'api_builder') and _apex_infra.api_builder:
        return _apex_infra.api_builder.status()
    return {"error": "API Builder not connected"}


async def create_api_endpoint(
    path: str,
    name: str,
    description: str = "",
    system_prompt: str = "",
    model_tier: str = "auto",
) -> dict[str, Any]:
    """Create a dynamic API endpoint via the builder."""
    if _apex_infra:
        return await _apex_infra.create_endpoint(
            path=path, name=name, description=description,
            system_prompt=system_prompt, model_tier=model_tier,
        )
    return {"error": "Infrastructure connector not available"}


async def list_api_endpoints() -> list[dict[str, Any]]:
    """List all registered API endpoints."""
    if _apex_infra:
        return _apex_infra.list_endpoints()
    return []


async def get_openapi_spec() -> dict[str, Any]:
    """Get OpenAPI 3.1 spec for all endpoints."""
    if _apex_infra:
        return _apex_infra.get_openapi_spec()
    return {"error": "Infrastructure connector not available"}


async def route_model(task_type: str = "general", tier: str = "auto") -> str:
    """Route to optimal model via infra connector."""
    if _apex_infra:
        return _apex_infra.route_model(task_type, tier)
    # Fallback
    fallback = {
        "code": "anthropic/claude-opus-4",
        "analysis": "google/gemini-2.5-pro-preview-05-06",
        "creative": "openai/gpt-4-turbo-2024-04-09",
        "fast": "google/gemini-2.5-flash-preview-04-17",
        "math": "deepseek/deepseek-r1",
    }
    return fallback.get(task_type, "google/gemini-2.5-pro-preview-05-06")


async def get_bridge_health() -> dict[str, Any]:
    """Full health check: APEX server + infra connector."""
    server_running = await is_server_running()
    infra_health = _apex_infra.health() if _apex_infra else {"status": "disconnected"}

    return {
        "apex_server": {
            "running": server_running,
            "port": APEX_PORT,
            "base_url": APEX_API,
        },
        "infrastructure": infra_health,
        "bridge_version": "2.4.0-TITANIUM",
        "capabilities": [
            "chat", "ultraplinian", "consortium", "agent",
            "model_testing", "api_builder", "openapi",
        ],
    }


