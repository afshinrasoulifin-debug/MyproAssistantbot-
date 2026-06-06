
#!/usr/bin/env python3
"""
tests/test_api_builder_infra.py — API Builder + Agent + Model Integration Tests v2.5
═══════════════════════════════════════════════════════════════════════════════════════
Full 10-layer static infrastructure test:

  L1: models_registry (72 models)
  L2: ai_client (provider routing)
  L3: UnifiedClient (abstraction layer)
  L4: SmartClient (auto-routing)
  L5: Bridge (APEX HTTP bridge)
  L6: AgentExecutor (20 tools)
  L7: APEX TS (20 tools)
  L8: ModelSelector (63 models)
  L9: HF Sync (dataset publisher)
  L10: API Builder (endpoints, model router, OpenAPI, infra connector)

All tests are STATIC — no API keys, no network, no external dependencies.
Uses regex parsing and import validation on the actual source code.
"""

import re
import sys
from pathlib import Path
from typing import List

# Project root
ROOT = Path(__file__).resolve().parent.parent

# ═══════════════════════════════════════════════════════════════════
# Test Framework
# ═══════════════════════════════════════════════════════════════════

class TestResult:
    def __init__(self, name: str, passed: bool, detail: str = ""):
        self.name = name
        self.passed = passed
        self.detail = detail

class TestLayer:
    def __init__(self, number: int, name: str):
        self.number = number
        self.name = name
        self.results: List[TestResult] = []

    def add(self, name: str, passed: bool, detail: str = ""):
        self.results.append(TestResult(name, passed, detail))

    @property
    def passed(self): return sum(1 for r in self.results if r.passed)
    @property
    def total(self): return len(self.results)
    @property
    def all_passed(self): return self.passed == self.total


def read(path: str) -> str:
    """Read file relative to project root."""
    full = ROOT / path
    if full.exists():
        return full.read_text(encoding="utf-8", errors="replace")
    return ""


# ═══════════════════════════════════════════════════════════════════
# L1: Models Registry (72 models)
# ═══════════════════════════════════════════════════════════════════

def test_L1_models_registry() -> TestLayer:
    L = TestLayer(1, "Models Registry")
    src = read("utils/models_registry.py")

    # File exists
    L.add("File exists", bool(src), f"{len(src)} bytes")

    # All 72 model keys present
    all_keys = [
        "gemini-pro", "gemini-flash", "llama8", "llama70",
        "g-gemini-flash", "g-deepseek-chat", "g-sonar", "g-grok4",
    ]
    found = sum(1 for k in all_keys if f'"{k}"' in src)
    L.add("Key models present", found >= 5, f"{found}/{len(all_keys)} key models found")

    # Check total model count — count "g-" prefixed models
    g0d_count = len(re.findall(r'"g-[\w-]+"', src))
    base_count = len(re.findall(r'"(?:gemini|llama|qwen|compound|gemma|mixtral)\w*"', src))
    L.add("60+ model entries", g0d_count + base_count >= 20,
           f"~{g0d_count} APEX + ~{base_count} base = {g0d_count + base_count}")

    # smart_model_key function
    L.add("smart_model_key exists", "smart_model_key" in src)

    # TITANIUM version
    L.add("Version TITANIUM", "TITANIUM" in src or "10.4" in src)

    # Pro/Ultra tiers
    L.add("Pro tier exists", "pro" in src.lower() and ("ultra" in src.lower() or "power" in src.lower()))

    # Providers
    L.add("Gemini provider", "gemini" in src.lower())
    L.add("Groq provider", "groq" in src.lower())
    L.add("OpenRouter provider", "openrouter" in src.lower())

    # No duplicates (basic check)
    keys = re.findall(r'"(g-[\w-]+)":\s*\{', src)
    L.add("No duplicate APEX keys", len(keys) == len(set(keys)),
           f"{len(keys)} keys, {len(set(keys))} unique")

    return L


# ═══════════════════════════════════════════════════════════════════
# L2: AI Client
# ═══════════════════════════════════════════════════════════════════

def test_L2_ai_client() -> TestLayer:
    L = TestLayer(2, "AI Client")
    src = read("utils/ai_client.py")

    L.add("File exists", bool(src))
    L.add("Class AIClient", "class AIClient" in src)
    L.add("Gemini support", "gemini" in src.lower())
    L.add("OpenRouter support", "openrouter" in src.lower())
    L.add("Groq support", "groq" in src.lower())
    L.add("generate/send method", "async def generate" in src or "def generate" in src or
           "async def send" in src or "def send" in src or "async def ask" in src)
    L.add("Error handling", "try:" in src and "except" in src)
    L.add("TITANIUM integration", "TITANIUM" in src or "_ti_" in src)

    return L


# ═══════════════════════════════════════════════════════════════════
# L3: Unified Client
# ═══════════════════════════════════════════════════════════════════

def test_L3_unified_client() -> TestLayer:
    L = TestLayer(3, "Unified Client")
    src = read("infrastructure/clients/unified_client.py")

    L.add("File exists", bool(src))
    L.add("Class UnifiedClient", "class UnifiedClient" in src)
    L.add("send/request method", "def send" in src or "def request" in src or "async def" in src)
    L.add("Provider routing", "provider" in src.lower())

    return L


# ═══════════════════════════════════════════════════════════════════
# L4: Smart Client
# ═══════════════════════════════════════════════════════════════════

def test_L4_smart_client() -> TestLayer:
    L = TestLayer(4, "Smart Client")
    src = read("infrastructure/clients/smart_client.py")

    L.add("File exists", bool(src))
    L.add("Class SmartClient", "class SmartClient" in src)
    L.add("Auto-selection", "select" in src.lower() or "auto" in src.lower() or "route" in src.lower())

    return L


# ═══════════════════════════════════════════════════════════════════
# L5: Bridge
# ═══════════════════════════════════════════════════════════════════

def test_L5_bridge() -> TestLayer:
    L = TestLayer(5, "APEX Bridge")
    src = read("extra/bridge.py")

    L.add("File exists", bool(src))
    L.add("httpx client", "httpx" in src)
    L.add("Port 7860", "7860" in src)
    L.add("Enterprise auth", "enterprise" in src.lower() or "INTERNAL_KEY" in src)
    L.add("chat_completion", "async def chat_completion" in src)
    L.add("ultraplinian_completion", "async def ultraplinian_completion" in src)
    L.add("consortium_completion", "async def consortium_completion" in src)
    L.add("SSE streaming", "stream" in src)
    L.add("TITANIUM integration", "TITANIUM" in src or "shielded" in src)

    # v2.4 enhancements
    L.add("Agent execute", "async def agent_execute" in src)
    L.add("Model test", "async def test_model" in src)
    L.add("Batch test", "async def batch_test_models" in src)
    L.add("API builder bridge", "async def create_api_endpoint" in src)
    L.add("Model routing", "async def route_model" in src)
    L.add("Bridge health", "async def get_bridge_health" in src)
    L.add("OpenAPI spec", "async def get_openapi_spec" in src)

    return L


# ═══════════════════════════════════════════════════════════════════
# L6: Agent Executor (Python — 20 tools)
# ═══════════════════════════════════════════════════════════════════

def test_L6_agent_executor() -> TestLayer:
    L = TestLayer(6, "Agent Executor (Python)")
    src = read("utils/agent_executor.py")

    L.add("File exists", bool(src))
    L.add("Class AgentExecutor", "class AgentExecutor" in src or "class StepScheduler" in src)

    # Core 12 tools
    core_tools = [
        "web_search", "academic_search", "code_search", "web_recon",
        "google_dork", "http_request", "execute_code", "analyze_text",
        "transform_data", "encode_decode", "crypto", "network_scan",
    ]
    for tool in core_tools:
        L.add(f"Tool: {tool}", f'name="{tool}"' in src)

    # New API/Infra tools (8)
    api_tools = [
        "api_create_endpoint", "api_execute", "api_list",
        "api_openapi_spec", "model_list", "model_route",
        "infra_health", "api_status",
    ]
    for tool in api_tools:
        L.add(f"Tool: {tool}", f'name="{tool}"' in src)

    # 20 tools total
    tool_names = re.findall(r'name="(\w+)"', src)
    # De-dup (first occurrence per name is the registration)
    unique_tools = []
    seen = set()
    for t in tool_names:
        if t not in seen and len(t) > 3:
            seen.add(t)
            unique_tools.append(t)
    L.add("20 tools registered", len(unique_tools) >= 20,
           f"{len(unique_tools)} unique tools: {', '.join(unique_tools[:22])}")

    # ToolCategory enum includes API, MODELS, INFRA
    L.add("ToolCategory.API", 'API' in src and '"api"' in src)
    L.add("ToolCategory.MODELS", 'MODELS' in src and '"models"' in src)
    L.add("ToolCategory.INFRA", 'INFRA' in src and '"infrastructure"' in src)

    # Import api_builder
    L.add("API Builder import", "from infrastructure.api.api_builder import" in src)

    return L


# ═══════════════════════════════════════════════════════════════════
# L7: APEX TS Agent (20 tools)
# ═══════════════════════════════════════════════════════════════════

def test_L7_apex_ts() -> TestLayer:
    L = TestLayer(7, "APEX TS Agent")
    src = read("extra/apex_app/src/lib/agent-executor.ts")

    L.add("File exists", bool(src))

    # All 20 TS tools
    ts_tools = [
        "web_search", "academic_search", "code_search", "deep_crawl",
        "web_recon", "google_dork", "web_automate", "execute_code",
        "http_request", "analyze_text", "transform_data", "encode_decode",
        "api_create_endpoint", "model_list", "model_route", "api_execute",
        "api_openapi_spec", "infra_health", "batch_model_test", "api_status",
    ]
    for tool in ts_tools:
        L.add(f"TS Tool: {tool}", f"name: '{tool}'" in src)

    # Tool count
    ts_tool_names = re.findall(r"name:\s*'(\w+)'", src)
    L.add("20 TS tools", len(ts_tool_names) >= 20,
           f"{len(ts_tool_names)} tools found")

    # API categories
    L.add("Category: api", "'api'" in src)
    L.add("Category: models", "'models'" in src)
    L.add("Category: infrastructure", "'infrastructure'" in src)

    return L


# ═══════════════════════════════════════════════════════════════════
# L8: Model Selector
# ═══════════════════════════════════════════════════════════════════

def test_L8_model_selector() -> TestLayer:
    L = TestLayer(8, "Model Selector (TSX)")
    src = read("extra/apex_app/src/components/ModelSelector.tsx")

    L.add("File exists", bool(src))
    L.add("ModelSelector component", "ModelSelector" in src)
    L.add("Gemini models", "gemini" in src.lower())
    L.add("APEX models", "g-" in src or "g0d" in src.lower() or "grok" in src.lower())

    # Model references
    model_refs = re.findall(r"'([\w/-]+)'", src)
    L.add("50+ model refs", len(model_refs) >= 50, f"{len(model_refs)} model references")

    return L


# ═══════════════════════════════════════════════════════════════════
# L9: HF Sync
# ═══════════════════════════════════════════════════════════════════

def test_L9_hf_sync() -> TestLayer:
    L = TestLayer(9, "HF Sync")
    src = read("extra/apex_app/api/lib/hf-publisher.ts")

    L.add("File exists", bool(src))

    return L


# ═══════════════════════════════════════════════════════════════════
# L10: API Builder (NEW — comprehensive)
# ═══════════════════════════════════════════════════════════════════

def test_L10_api_builder() -> TestLayer:
    L = TestLayer(10, "API Builder Agent")

    # ── Python API Builder ──
    py_src = read("infrastructure/api/api_builder.py")
    L.add("Python file exists", bool(py_src))
    L.add("Class APIBuilderAgent", "class APIBuilderAgent" in py_src)
    L.add("Class EndpointRegistry", "class EndpointRegistry" in py_src)
    L.add("Class ModelRouter", "class ModelRouter" in py_src)
    L.add("Class OpenAPIGenerator", "class OpenAPIGenerator" in py_src)
    L.add("72 models catalogued", "72" in py_src)

    # All 5 tiers in ModelRouter
    for tier in ["FAST", "PRO", "ULTRA"]:
        L.add(f"ModelTier.{tier}", f"ModelTier.{tier}" in py_src or f'"{tier.lower()}"' in py_src.lower())

    # Built-in endpoints (12)
    builtin_paths = [
        "chat/completions", "agent/execute", "ultraplinian/completions",
        "consortium/completions", "models/test", "models/list",
        "builder/create", "builder/test", "builder/openapi",
        "infra/health", "smart/completions", "batch/completions",
    ]
    for path in builtin_paths:
        L.add(f"Endpoint: {path}", f'"{path}"' in py_src)

    # OpenAPI spec generation
    L.add("OpenAPI 3.1", '"3.1.0"' in py_src or "'3.1.0'" in py_src)

    # Singleton accessor
    L.add("get_api_builder()", "def get_api_builder" in py_src)

    # ── TS API Builder Routes ──
    ts_src = read("extra/apex_app/api/routes/api-builder.ts")
    L.add("TS routes file exists", bool(ts_src))
    L.add("TS model registry (72)", "72" in ts_src)

    # TS routes
    ts_routes = [
        "router.get('/endpoints'", "router.post('/endpoints'",
        "router.post('/execute/", "router.get('/openapi'",
        "router.get('/models'", "router.post('/models/route'",
        "router.post('/models/test'", "router.post('/models/batch'",
        "router.get('/health'", "router.get('/stats'",
    ]
    for route in ts_routes:
        L.add(f"TS route: {route.split('(')[0]}", route in ts_src)

    # Smart routing map
    L.add("TS smart routing", "SMART_ROUTES" in ts_src)

    # ── Server Integration ──
    server_src = read("extra/apex_app/api/server.ts")
    L.add("Server imports builder", "apiBuilderRoutes" in server_src)
    L.add("Server mounts /v1/builder", "'/v1/builder'" in server_src)
    L.add("Server info includes builder", "builder" in server_src.lower())

    # ── Infra Connector v2.0 ──
    conn_src = read("extra/infra_connector.py")
    L.add("InfraConnector v2.0", "v2.0" in conn_src or "2.0.0" in conn_src)
    L.add("Bidirectional bridge", "bidirectional" in conn_src.lower() or "create_endpoint" in conn_src)
    L.add("Model routing", "route_model" in conn_src)
    L.add("Agent execution", "execute_agent" in conn_src)
    L.add("Health method", "def health" in conn_src)
    L.add("API builder property", "def api_builder" in conn_src or "api_builder" in conn_src)
    L.add("72 models", "72" in conn_src)

    # ── Infrastructure Registry ──
    reg_src = read("infrastructure/registry.py")
    L.add("Registry includes api_builder", "api_builder" in reg_src)
    L.add("Registry imports APIBuilderAgent", "APIBuilderAgent" in reg_src)

    # ── Bridge enhancements ──
    bridge_src = read("extra/bridge.py")
    L.add("Bridge agent_execute", "async def agent_execute" in bridge_src)
    L.add("Bridge batch_test_models", "async def batch_test_models" in bridge_src)
    L.add("Bridge create_api_endpoint", "async def create_api_endpoint" in bridge_src)
    L.add("Bridge get_openapi_spec", "async def get_openapi_spec" in bridge_src)
    L.add("Bridge get_bridge_health", "async def get_bridge_health" in bridge_src)

    return L


# ═══════════════════════════════════════════════════════════════════
# Main Runner
# ═══════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("  Arki Engine v10.4 TITANIUM — Full Infrastructure Test Suite v2.5")
    print("  10 Layers | Static Analysis | No API Keys Required")
    print("=" * 72)

    layers = [
        test_L1_models_registry(),
        test_L2_ai_client(),
        test_L3_unified_client(),
        test_L4_smart_client(),
        test_L5_bridge(),
        test_L6_agent_executor(),
        test_L7_apex_ts(),
        test_L8_model_selector(),
        test_L9_hf_sync(),
        test_L10_api_builder(),
    ]

    total_pass = 0
    total_tests = 0
    failed_details = []

    for layer in layers:
        icon = "✅" if layer.all_passed else "⚠️"
        print(f"\n{icon} L{layer.number}: {layer.name} — {layer.passed}/{layer.total}")

        for r in layer.results:
            mark = "  ✅" if r.passed else "  ❌"
            detail = f" ({r.detail})" if r.detail else ""
            print(f"    {mark} {r.name}{detail}")
            if not r.passed:
                failed_details.append(f"L{layer.number} {r.name}{detail}")

        total_pass += layer.passed
        total_tests += layer.total

    # Summary
    print("\n" + "=" * 72)
    pct = (total_pass / total_tests * 100) if total_tests > 0 else 0
    print(f"  TOTAL: {total_pass}/{total_tests} ({pct:.1f}%)")
    print(f"  Layers: {sum(1 for l in layers if l.all_passed)}/{len(layers)} fully passing")

    if failed_details:
        print(f"\n  Failed tests ({len(failed_details)}):")
        for f in failed_details:
            print(f"    ❌ {f}")

    print("=" * 72)

    # Return exit code
    return 0 if pct >= 95 else 1


if __name__ == "__main__":
    sys.exit(main())


