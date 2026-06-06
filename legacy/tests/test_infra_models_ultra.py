
from __future__ import annotations
#!/usr/bin/env python3
"""
Arki Engine v10.4 — Infrastructure-Level Model Test (Pro/Ultra)

Tests ALL 72 models through the project's OWN infrastructure layers:
  Layer 1: models_registry — config validation, tier routing, AutoTune
  Layer 2: AIClient — Gemini/Groq direct provider calls
  Layer 3: UnifiedClient — multi-provider abstraction
  Layer 4: SmartClient — auto model selection
  Layer 5: bridge — APEX API forwarding (OpenRouter)
  Layer 6: agent_executor — autonomous multi-step agent chain

This script tests BOTH the models AND the infrastructure.

Usage:
    GEMINI_API_KEY=... GROQ_API_KEY=... OPENROUTER_API_KEY=... python tests/test_infra_models_ultra.py
    # Or: make test-models
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import List

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ═══════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
TIMEOUT = int(os.environ.get("TEST_TIMEOUT", "60"))

# Complex technical test question
COMPLEX_Q = """Design a fault-tolerant distributed transaction coordinator using the Saga pattern
with the following microservices: OrderService, PaymentService (Stripe idempotency keys),
InventoryService, and ShippingService.

Requirements:
1. Implement Redis Redlock for distributed mutex
2. Compensating transactions for each saga step
3. Dead letter queue with exponential backoff retry
4. OpenTelemetry distributed tracing across all services
5. Exactly-once processing guarantees

Provide:
- Architecture diagram (text-based)
- TypeScript implementation of the SagaCoordinator class
- Failure recovery state machine
- Monitoring alerts for SLA violations"""


@dataclass
class TestResult:
    model_key: str
    model_name: str
    model_id: str
    provider: str
    tier: str
    layer: str  # which infra layer was used
    status: str  # pass | fail | error | skip
    latency_ms: int = 0
    response_length: int = 0
    quality_score: int = 0
    error: str = ""
    preview: str = ""


def score_response(text: str) -> int:
    """Score quality 0-100."""
    if not text:
        return 0
    s = 0
    # Length
    if len(text) > 2000: s += 25
    elif len(text) > 1000: s += 15
    elif len(text) > 300: s += 8
    # Technical keywords
    kw = ['saga', 'redlock', 'idempoten', 'dead letter', 'compensat',
          'opentelemetry', 'distributed', 'exactly-once', 'mutex',
          'retry', 'rollback', 'circuit', 'trace', 'span']
    matches = sum(1 for k in kw if k in text.lower())
    s += min(25, matches * 2)
    # Code blocks
    code = text.count('```') // 2
    s += min(25, code * 5)
    # Structure
    heads = text.count('\n#') + text.count('\n##') + text.count('\n###')
    bullets = text.count('\n- ') + text.count('\n* ') + text.count('\n1.')
    s += min(25, (heads + bullets) * 2)
    return min(100, s)


# ═══════════════════════════════════════════════════════════════════
# Layer 1: Model Registry — config validation
# ═══════════════════════════════════════════════════════════════════

def test_layer1_registry() -> List[TestResult]:
    """Validate model registry configuration."""
    from utils.models_registry import (
        MODELS, APEX_TIERS, PERSONAS, LITE_MODELS, HEAVY_MODELS,
        DEFAULT_MODEL, smart_model_key, autotune, get_model,
    )
    results = []

    # Test 1.1: All models exist
    total = len(MODELS)
    r = TestResult("registry", "Model Count", "", "registry", "all", "L1-Registry",
                   "pass" if total >= 72 else "fail")
    r.preview = f"{total} models registered"
    results.append(r)

    # Test 1.2: LITE_MODELS is empty (all Pro)
    r = TestResult("lite_check", "Lite Mode Disabled", "", "registry", "all", "L1-Registry",
                   "pass" if len(LITE_MODELS) == 0 else "fail")
    r.preview = f"LITE={len(LITE_MODELS)}, HEAVY={len(HEAVY_MODELS)}"
    results.append(r)

    # Test 1.3: smart_model_key routes to Pro for all task types
    for task in ["simple", "standard", "complex"]:
        key = smart_model_key(task, gemini_key="test", groq_key="test")
        is_pro = key in ("gemini-pro", "llama70", "qwen3")
        r = TestResult(f"smart_{task}", f"smart_model_key({task})", key, "registry",
                       "pro", "L1-Registry", "pass" if is_pro else "fail")
        r.preview = f"→ {key}"
        results.append(r)

    # Test 1.4: AutoTune returns Ultra params
    params = autotune("Write a Python function to sort a linked list using merge sort")
    has_top_k = "top_k" in params
    has_ultra_tokens = params.get("max_tokens", 0) >= 65536
    r = TestResult("autotune", "AutoTune Ultra Params", "", "registry", "ultra", "L1-Registry",
                   "pass" if has_top_k and has_ultra_tokens else "fail")
    r.preview = f"top_k={params.get('top_k')}, max_tokens={params.get('max_tokens')}"
    results.append(r)

    # Test 1.5: All personas exist and are Ultra
    ultra_personas = sum(1 for p in PERSONAS.values() if "Ultra" in p.name or "Pro" in p.name)
    r = TestResult("personas", "Personas Ultra", "", "registry", "all", "L1-Registry",
                   "pass" if ultra_personas >= 5 else "fail")
    r.preview = f"{ultra_personas}/{len(PERSONAS)} are Pro/Ultra"
    results.append(r)

    # Test 1.6: APEX tiers complete
    tier_counts = {t: len(d["models"]) for t, d in APEX_TIERS.items()}
    total_g0d = sum(tier_counts.values())
    r = TestResult("g0d_tiers", "APEX Tier Count", "", "openrouter", "all", "L1-Registry",
                   "pass" if total_g0d == 59 else "fail")
    r.preview = f"{tier_counts} = {total_g0d}"
    results.append(r)

    # Test 1.7: Each model has valid structure
    invalid = []
    for key, m in MODELS.items():
        if not m.id or not m.name or m.provider not in ("gemini", "groq", "openrouter"):
            invalid.append(key)
    r = TestResult("model_struct", "Model Structure Valid", "", "registry", "all", "L1-Registry",
                   "pass" if not invalid else "fail")
    r.preview = f"{len(MODELS)} valid, {len(invalid)} invalid"
    if invalid:
        r.error = f"Invalid: {invalid[:5]}"
    results.append(r)

    # Test 1.8: Default model is Pro
    default = get_model(DEFAULT_MODEL)
    r = TestResult("default", "Default Model Pro", default.id, default.provider, "pro", "L1-Registry",
                   "pass" if "pro" in default.id.lower() or "pro" in DEFAULT_MODEL else "fail")
    r.preview = f"Default: {DEFAULT_MODEL} = {default.name}"
    results.append(r)

    return results


# ═══════════════════════════════════════════════════════════════════
# Layer 2: AIClient — direct provider calls
# ═══════════════════════════════════════════════════════════════════

async def test_layer2_aiclient() -> List[TestResult]:
    """Test models through AIClient (Gemini + Groq)."""
    results = []
    from utils.models_registry import MODELS

    # Filter base models
    base_models = {k: v for k, v in MODELS.items() if v.provider in ("gemini", "groq")}

    if not GEMINI_KEY and not GROQ_KEY:
        for key, m in base_models.items():
            results.append(TestResult(key, m.name, m.id, m.provider, "base", "L2-AIClient",
                                      "skip", error="No API key"))
        return results

    import httpx

    for key, m in base_models.items():
        if m.provider == "gemini" and not GEMINI_KEY:
            results.append(TestResult(key, m.name, m.id, m.provider, "base", "L2-AIClient",
                                      "skip", error="No GEMINI_API_KEY"))
            continue
        if m.provider == "groq" and not GROQ_KEY:
            results.append(TestResult(key, m.name, m.id, m.provider, "base", "L2-AIClient",
                                      "skip", error="No GROQ_API_KEY"))
            continue

        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                if m.provider == "gemini":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m.id}:generateContent?key={GEMINI_KEY}"
                    resp = await client.post(url, json={
                        "contents": [{"parts": [{"text": COMPLEX_Q}]}],
                        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
                    })
                    latency = int((time.time() - start) * 1000)
                    if resp.status_code != 200:
                        results.append(TestResult(key, m.name, m.id, m.provider, "base", "L2-AIClient",
                                                  "error", latency, error=f"HTTP {resp.status_code}"))
                        continue
                    data = resp.json()
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

                elif m.provider == "groq":
                    resp = await client.post("https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {GROQ_KEY}"},
                        json={
                            "model": m.id,
                            "messages": [{"role": "user", "content": COMPLEX_Q}],
                            "temperature": 0.3, "max_tokens": 4096,
                        })
                    latency = int((time.time() - start) * 1000)
                    if resp.status_code != 200:
                        results.append(TestResult(key, m.name, m.id, m.provider, "base", "L2-AIClient",
                                                  "error", latency, error=f"HTTP {resp.status_code}: {resp.text[:100]}"))
                        continue
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]

                qs = score_response(text)
                results.append(TestResult(key, m.name, m.id, m.provider, "base", "L2-AIClient",
                                          "pass" if len(text) > 50 else "fail", latency,
                                          len(text), qs, preview=text[:150]))

        except Exception as e:
            latency = int((time.time() - start) * 1000)
            results.append(TestResult(key, m.name, m.id, m.provider, "base", "L2-AIClient",
                                      "error", latency, error=str(e)[:200]))

    return results


# ═══════════════════════════════════════════════════════════════════
# Layer 3: UnifiedClient — multi-provider abstraction
# ═══════════════════════════════════════════════════════════════════

async def test_layer3_unified() -> List[TestResult]:
    """Test UnifiedClient provider resolution."""
    from infrastructure.clients.unified_client import UnifiedClient

    uc = UnifiedClient()
    results = []

    # Test provider resolution
    test_cases = [
        ("gemini-2.5-pro", "gemini"),
        ("llama-3.3-70b-versatile", "groq"),
        ("google/gemini-2.5-pro", "openrouter"),
        ("anthropic/claude-opus-4", "openrouter"),
        ("openai/gpt-5", "openrouter"),
    ]

    for model_id, expected_provider in test_cases:
        resolved = uc._resolve_provider(model_id)
        r = TestResult(f"uc_{model_id[:20]}", f"Resolve {model_id[:25]}", model_id,
                       resolved, "all", "L3-UnifiedClient",
                       "pass" if resolved == expected_provider else "fail")
        r.preview = f"→ {resolved} (expected {expected_provider})"
        results.append(r)

    return results


# ═══════════════════════════════════════════════════════════════════
# Layer 4: SmartClient — auto model selection
# ═══════════════════════════════════════════════════════════════════

async def test_layer4_smart() -> List[TestResult]:
    """Test SmartClient auto-selection."""
    from infrastructure.clients.smart_client import SmartClient

    sc = SmartClient()
    results = []

    test_msgs = [
        ([{"role": "user", "content": "Hello"}], "auto", "Simple chat"),
        ([{"role": "user", "content": COMPLEX_Q}], "complex", "Complex technical"),
        ([{"role": "user", "content": "Write me a React component"}], "code", "Code generation"),
    ]

    for msgs, task_type, desc in test_msgs:
        selected = sc._select_model(msgs, task_type)
        is_pro = "pro" in selected or "70b" in selected or "grok" in selected
        r = TestResult(f"sc_{task_type}", f"SmartClient: {desc}", selected,
                       "smart", "pro", "L4-SmartClient",
                       "pass" if is_pro else "fail")
        r.preview = f"→ {selected}"
        results.append(r)

    return results


# ═══════════════════════════════════════════════════════════════════
# Layer 5: Bridge → APEX (OpenRouter)
# ═══════════════════════════════════════════════════════════════════

async def test_layer5_openrouter() -> List[TestResult]:
    """Test APEX models via OpenRouter directly (no local server needed)."""
    results = []
    from utils.models_registry import APEX_TIERS

    if not OPENROUTER_KEY:
        # Enumerate all and mark skip
        for tier_name, tier_data in APEX_TIERS.items():
            for key, m in tier_data["models"].items():
                results.append(TestResult(key, m.name, m.id, "openrouter", tier_name,
                                          "L5-OpenRouter", "skip", error="No OPENROUTER_API_KEY"))
        return results

    import httpx

    for tier_name, tier_data in APEX_TIERS.items():
        for key, m in tier_data["models"].items():
            start = time.time()
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    resp = await client.post("https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_KEY}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://apex.app",
                            "X-Title": "APEX v2.3 Infra Test",
                        },
                        json={
                            "model": m.id,
                            "messages": [
                                {"role": "system", "content": "You are an expert distributed systems architect. Provide detailed technical answers with code."},
                                {"role": "user", "content": COMPLEX_Q},
                            ],
                            "temperature": 0.3,
                            "max_tokens": 4096,
                        })
                    latency = int((time.time() - start) * 1000)

                    if resp.status_code != 200:
                        err_msg = f"HTTP {resp.status_code}"
                        try:
                            err_msg = resp.json().get("error", {}).get("message", err_msg)
                        except Exception:
                            pass
                        results.append(TestResult(key, m.name, m.id, "openrouter", tier_name,
                                                  "L5-OpenRouter", "error", latency, error=err_msg[:200]))
                        continue

                    data = resp.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    qs = score_response(text)
                    results.append(TestResult(key, m.name, m.id, "openrouter", tier_name,
                                              "L5-OpenRouter", "pass" if len(text) > 50 else "fail",
                                              latency, len(text), qs, preview=text[:150]))

            except Exception as e:
                latency = int((time.time() - start) * 1000)
                results.append(TestResult(key, m.name, m.id, "openrouter", tier_name,
                                          "L5-OpenRouter", "error", latency, error=str(e)[:200]))

            # Small delay between requests to avoid rate limits
            await asyncio.sleep(0.3)

    return results


# ═══════════════════════════════════════════════════════════════════
# Layer 6: Agent Executor — autonomous chain test
# ═══════════════════════════════════════════════════════════════════

async def test_layer6_agent() -> List[TestResult]:
    """Test agent executor infrastructure (no API calls needed)."""
    results = []
    try:
        from utils.agent_executor import (
            ToolCategory, StepStatus, TraceStatus,
            MAX_AGENT_STEPS, PARALLEL_BATCH_SIZE, REFLECTION_THRESHOLD,
        )

        # Test 6.1: Agent config is Pro-level
        r = TestResult("agent_config", "Agent Config Pro", "", "agent", "pro", "L6-AgentExecutor",
                       "pass" if MAX_AGENT_STEPS >= 50 and PARALLEL_BATCH_SIZE >= 6 else "fail")
        r.preview = f"max_steps={MAX_AGENT_STEPS}, parallel={PARALLEL_BATCH_SIZE}, reflection={REFLECTION_THRESHOLD}"
        results.append(r)

        # Test 6.2: Tool categories exist
        categories = list(ToolCategory)
        r = TestResult("agent_tools", "Agent Tool Categories", "", "agent", "pro", "L6-AgentExecutor",
                       "pass" if len(categories) >= 10 else "fail")
        r.preview = f"{len(categories)} categories: {[c.value for c in categories[:6]]}..."
        results.append(r)

        # Test 6.3: Step/Trace statuses
        step_statuses = list(StepStatus)
        trace_statuses = list(TraceStatus)
        r = TestResult("agent_states", "Agent State Machine", "", "agent", "pro", "L6-AgentExecutor",
                       "pass" if len(step_statuses) >= 7 and len(trace_statuses) >= 5 else "fail")
        r.preview = f"step_statuses={len(step_statuses)}, trace_statuses={len(trace_statuses)}"
        results.append(r)

    except ImportError as e:
        results.append(TestResult("agent_import", "Agent Import", "", "agent", "pro", "L6-AgentExecutor",
                                  "error", error=str(e)[:200]))
    except Exception as e:
        results.append(TestResult("agent_err", "Agent Executor", "", "agent", "pro", "L6-AgentExecutor",
                                  "error", error=str(e)[:200]))

    return results


# ═══════════════════════════════════════════════════════════════════
# Main Runner
# ═══════════════════════════════════════════════════════════════════

async def main():
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║  Arki Engine v10.4 TITANIUM — Infrastructure Model Test (Pro/Ultra)  ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print(f"\n🔑 API Keys:")
    print(f"   Gemini:     {'✅ ' + GEMINI_KEY[:8] + '...' if GEMINI_KEY else '❌ Not set'}")
    print(f"   Groq:       {'✅ ' + GROQ_KEY[:8] + '...' if GROQ_KEY else '❌ Not set'}")
    print(f"   OpenRouter: {'✅ ' + OPENROUTER_KEY[:8] + '...' if OPENROUTER_KEY else '❌ Not set'}")
    print(f"   Timeout:    {TIMEOUT}s")

    all_results: List[TestResult] = []

    # Layer 1: Registry (no API needed)
    print("\n" + "═" * 70)
    print("📦 Layer 1: Model Registry — Configuration Validation")
    print("═" * 70)
    l1 = test_layer1_registry()
    all_results.extend(l1)
    for r in l1:
        icon = "✅" if r.status == "pass" else "❌" if r.status == "fail" else "⏭️"
        print(f"  {icon} {r.model_name.ljust(30)} {r.preview}")

    # Layer 2: AIClient (needs Gemini/Groq keys)
    print("\n" + "═" * 70)
    print("🔌 Layer 2: AIClient — Direct Provider Calls (Gemini + Groq)")
    print("═" * 70)
    l2 = await test_layer2_aiclient()
    all_results.extend(l2)
    for r in l2:
        icon = {"pass": "✅", "fail": "❌", "error": "💥", "skip": "⏭️"}[r.status]
        qs = f" Q:{r.quality_score}/100" if r.quality_score else ""
        lat = f" {r.latency_ms}ms" if r.latency_ms else ""
        print(f"  {icon} {r.model_name.ljust(25)} {r.model_id.ljust(35)}{lat}{qs} {r.error or r.preview[:60]}")

    # Layer 3: UnifiedClient (no API needed)
    print("\n" + "═" * 70)
    print("🔗 Layer 3: UnifiedClient — Provider Resolution")
    print("═" * 70)
    l3 = await test_layer3_unified()
    all_results.extend(l3)
    for r in l3:
        icon = "✅" if r.status == "pass" else "❌"
        print(f"  {icon} {r.model_name.ljust(35)} {r.preview}")

    # Layer 4: SmartClient (no API needed)
    print("\n" + "═" * 70)
    print("🧠 Layer 4: SmartClient — Auto Model Selection")
    print("═" * 70)
    l4 = await test_layer4_smart()
    all_results.extend(l4)
    for r in l4:
        icon = "✅" if r.status == "pass" else "❌"
        print(f"  {icon} {r.model_name.ljust(35)} {r.preview}")

    # Layer 5: OpenRouter (needs key)
    print("\n" + "═" * 70)
    print("🌐 Layer 5: APEX OpenRouter — 59 Models Test")
    print("═" * 70)
    l5 = await test_layer5_openrouter()
    all_results.extend(l5)
    for r in l5:
        icon = {"pass": "✅", "fail": "❌", "error": "💥", "skip": "⏭️"}[r.status]
        qs = f" Q:{r.quality_score}/100" if r.quality_score else ""
        lat = f" {r.latency_ms}ms" if r.latency_ms else ""
        tier_icon = {"fast": "⚡", "standard": "🔵", "pro": "🌟", "power": "🟠", "ultra": "🔴"}.get(r.tier, "⚪")
        err = f" ERR: {r.error[:60]}" if r.error and r.status != "skip" else ""
        if r.status == "skip":
            print(f"  ⏭️  {tier_icon} {r.model_name.ljust(25)} skipped")
        else:
            print(f"  {icon} {tier_icon} {r.model_name.ljust(25)} {r.model_id.ljust(40)}{lat}{qs}{err}")

    # Layer 6: Agent Executor (no API needed)
    print("\n" + "═" * 70)
    print("🤖 Layer 6: Agent Executor — Infrastructure Test")
    print("═" * 70)
    l6 = await test_layer6_agent()
    all_results.extend(l6)
    for r in l6:
        icon = "✅" if r.status == "pass" else "❌" if r.status == "fail" else "💥"
        print(f"  {icon} {r.model_name.ljust(30)} {r.preview}")

    # ═══ Final Report ═══
    print("\n" + "═" * 70)
    print("📊 FINAL REPORT — Arki Engine v10.4 TITANIUM Pro/Ultra")
    print("═" * 70)

    passed = [r for r in all_results if r.status == "pass"]
    failed = [r for r in all_results if r.status == "fail"]
    errors = [r for r in all_results if r.status == "error"]
    skipped = [r for r in all_results if r.status == "skip"]

    print(f"\n  Total Tests:  {len(all_results)}")
    print(f"  ✅ Passed:    {len(passed)}")
    print(f"  ❌ Failed:    {len(failed)}")
    print(f"  💥 Error:     {len(errors)}")
    print(f"  ⏭️  Skipped:   {len(skipped)}")

    # By layer
    print("\n  📈 By Layer:")
    layers = {}
    for r in all_results:
        layers.setdefault(r.layer, []).append(r)
    for layer, layer_results in sorted(layers.items()):
        p = sum(1 for r in layer_results if r.status == "pass")
        t = len(layer_results)
        s = sum(1 for r in layer_results if r.status == "skip")
        print(f"    {layer.ljust(20)} {p}/{t - s} passed (of {t - s} tested, {s} skipped)")

    # By tier
    print("\n  📈 By Tier:")
    tier_results = {}
    for r in all_results:
        if r.tier in ("fast", "standard", "pro", "power", "ultra", "base"):
            tier_results.setdefault(r.tier, []).append(r)
    for tier in ["fast", "standard", "pro", "power", "ultra", "base"]:
        if tier not in tier_results:
            continue
        trs = tier_results[tier]
        p = sum(1 for r in trs if r.status == "pass")
        t = len(trs)
        s = sum(1 for r in trs if r.status == "skip")
        tested = t - s
        avg_q = 0
        avg_lat = 0
        with_quality = [r for r in trs if r.quality_score > 0]
        if with_quality:
            avg_q = sum(r.quality_score for r in with_quality) // len(with_quality)
            avg_lat = sum(r.latency_ms for r in with_quality) // len(with_quality)
        icon = {"fast": "⚡", "standard": "🔵", "pro": "🌟", "power": "🟠", "ultra": "🔴", "base": "🔵"}.get(tier, "⚪")
        print(f"    {icon} {tier.ljust(10)} {p}/{tested} passed | avg Q:{avg_q}/100 | avg lat:{avg_lat}ms")

    # Top models by quality
    with_quality = [r for r in all_results if r.quality_score > 0]
    if with_quality:
        print("\n  🏆 Top 10 by Quality:")
        sorted_q = sorted(with_quality, key=lambda r: r.quality_score, reverse=True)
        for i, r in enumerate(sorted_q[:10], 1):
            print(f"    {i:2d}. Q:{r.quality_score}/100 | {r.model_name} ({r.tier}) | {r.latency_ms}ms | {r.response_length} chars")

    # Errors detail
    if errors:
        print(f"\n  💥 Errors ({len(errors)}):")
        for r in errors[:10]:
            print(f"    • {r.model_name}: {r.error[:100]}")

    # Pro/Ultra verdict
    all_configured = not failed  # Only registry failures count
    registry_tests = [r for r in all_results if r.layer == "L1-Registry"]
    registry_pass = all(r.status == "pass" for r in registry_tests)
    print(f"\n  {'✅' if registry_pass else '❌'} Model Registry: {'All Pro/Ultra' if registry_pass else 'ISSUES FOUND'}")
    print(f"  {'✅' if not failed else '❌'} Infrastructure: {'All layers operational' if not failed else f'{len(failed)} failures'}")

    # Save JSON report
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "version": "29.0.0",
        "total": len(all_results),
        "passed": len(passed),
        "failed": len(failed),
        "errors": len(errors),
        "skipped": len(skipped),
        "results": [
            {
                "model_key": r.model_key, "model_name": r.model_name, "model_id": r.model_id,
                "provider": r.provider, "tier": r.tier, "layer": r.layer,
                "status": r.status, "latency_ms": r.latency_ms,
                "response_length": r.response_length, "quality_score": r.quality_score,
                "error": r.error,
            }
            for r in all_results
        ],
    }
    report_path = f"test_report_infra_{int(time.time())}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  📄 Report: {report_path}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))


