
#!/usr/bin/env python3
"""
Arki Engine v10.4 — All-Models Test Suite (Pro/Ultra)

Tests all 13 base models (Gemini + Groq) with a complex technical question.
Requires: GEMINI_API_KEY and/or GROQ_API_KEY

Usage:
    GEMINI_API_KEY=... GROQ_API_KEY=... python scripts/test_all_models.py
"""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.models_registry import MODELS, APEX_TIERS

COMPLEX_QUESTION = """You are given a distributed system with 5 microservices communicating via gRPC and Kafka.
A race condition occurs when two concurrent saga transactions attempt to:
1. Reserve inventory (Inventory Service)
2. Process payment (Payment Service — Stripe with idempotency keys)
3. Create shipping label (Shipping Service)

The payment succeeds but inventory reservation fails due to a database deadlock.

Design a complete solution:
a) Distributed locking with Redis Redlock
b) Compensating transactions for the saga
c) Dead letter queue for failed events
d) Exactly-once payment processing
e) OpenTelemetry distributed tracing across all services

Provide architecture, TypeScript/Go code for critical paths, and failure recovery."""


def score_response(text: str) -> int:
    """Score response quality (0-100)."""
    score = 0
    # Length
    if len(text) > 2000: score += 30
    elif len(text) > 1000: score += 20
    elif len(text) > 500: score += 10
    # Keywords
    keywords = ['redis', 'redlock', 'saga', 'idempoten', 'dead letter',
                'compensat', 'opentelemetry', 'trace', 'deadlock', 'rollback',
                'exactly-once', 'distributed lock', 'circuit breaker']
    matches = sum(1 for k in keywords if k in text.lower())
    score += min(30, matches * 3)
    # Code blocks
    code_blocks = text.count('```') // 2
    score += min(20, code_blocks * 5)
    # Structure
    headers = text.count('\n#') + text.count('\n##')
    bullets = text.count('\n- ') + text.count('\n* ')
    score += min(20, (headers + bullets) * 2)
    return min(100, score)


async def test_gemini(model_id: str, api_key: str) -> dict:
    """Test a Gemini model."""
    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json={
                "contents": [{"parts": [{"text": COMPLEX_QUESTION}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
            })
            latency = int((time.time() - start) * 1000)
            if resp.status_code != 200:
                return {"status": "error", "latency_ms": latency, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            data = resp.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return {
                "status": "pass" if len(text) > 50 else "fail",
                "latency_ms": latency,
                "response_length": len(text),
                "quality_score": score_response(text),
                "preview": text[:200],
            }
    except Exception as e:
        return {"status": "error", "latency_ms": int((time.time() - start) * 1000), "error": str(e)[:200]}


async def test_groq(model_id: str, api_key: str) -> dict:
    """Test a Groq model."""
    import httpx
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": "You are an expert distributed systems architect."},
                        {"role": "user", "content": COMPLEX_QUESTION},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                })
            latency = int((time.time() - start) * 1000)
            if resp.status_code != 200:
                return {"status": "error", "latency_ms": latency, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return {
                "status": "pass" if len(text) > 50 else "fail",
                "latency_ms": latency,
                "response_length": len(text),
                "quality_score": score_response(text),
                "preview": text[:200],
            }
    except Exception as e:
        return {"status": "error", "latency_ms": int((time.time() - start) * 1000), "error": str(e)[:200]}


async def main():
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")

    if not gemini_key and not groq_key:
        print("❌ Set GEMINI_API_KEY and/or GROQ_API_KEY")
        sys.exit(1)

    print("╔═══════════════════════════════════════════════════════╗")
    print("║  Arki Engine v10.4 — Base Models Test (Pro/Ultra)    ║")
    print("╚═══════════════════════════════════════════════════════╝")

    base_models = {k: v for k, v in MODELS.items() if v.provider in ("gemini", "groq")}
    print(f"\n📊 Testing {len(base_models)} base models")
    print(f"   Gemini key: {'✅' if gemini_key else '❌'}")
    print(f"   Groq key:   {'✅' if groq_key else '❌'}\n")

    results = []
    for key, model in base_models.items():
        if model.provider == "gemini" and gemini_key:
            print(f"  ⏳ {model.emoji} {model.name} ({model.id})...", end=" ", flush=True)
            r = await test_gemini(model.id, gemini_key)
        elif model.provider == "groq" and groq_key:
            print(f"  ⏳ {model.emoji} {model.name} ({model.id})...", end=" ", flush=True)
            r = await test_groq(model.id, groq_key)
        else:
            print(f"  ⏭️  {model.emoji} {model.name} — skipped (no API key)")
            continue

        r["model_key"] = key
        r["model_name"] = model.name
        r["provider"] = model.provider
        results.append(r)

        icon = "✅" if r["status"] == "pass" else "❌"
        qs = r.get("quality_score", 0)
        print(f"{icon} {r['latency_ms']}ms | Q:{qs}/100 | {r.get('response_length', 0)} chars")

    # Summary
    passed = [r for r in results if r["status"] == "pass"]
    print(f"\n{'═' * 50}")
    print(f"📊 Results: {len(passed)}/{len(results)} passed")
    if passed:
        avg_q = sum(r["quality_score"] for r in passed) // len(passed)
        avg_lat = sum(r["latency_ms"] for r in passed) // len(passed)
        print(f"📈 Avg quality: {avg_q}/100 | Avg latency: {avg_lat}ms")

    # APEX summary
    g0d_total = sum(len(t["models"]) for t in APEX_TIERS.values())
    print(f"\n📡 APEX OpenRouter models: {g0d_total}")
    print(f"   Run: OPENROUTER_API_KEY=... npx tsx scripts/test_all_models.ts")
    print(f"   (in extra/apex_app/)")

if __name__ == "__main__":
    asyncio.run(main())


