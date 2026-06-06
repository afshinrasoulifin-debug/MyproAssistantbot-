
from __future__ import annotations
"""
free_access_router_pkg/_base.py — shared imports
Arki Engine v29.0.0
"""
"""
utils/free_access_router.py — Free Access Router v26.1.0
═══════════════════════════════════════════════════════════════════
Fully autonomous free API access for ALL 116 models.
Zero manual configuration. Zero cost. Zero API keys required.
The system manages everything from production to consumption.

All blocking key checks removed. Every model has a guaranteed free
access path. No startup gate. No "key not set" errors. Pure autonomy.

Architecture:
─────────────
  ┌─────────────────────────────────────────────────────────────┐
  │             FreeAccessRouter v26.1.0                │
  │                                                               │
  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
  │  │ OpenRouter    │  │ Direct Free  │  │ Smart Fallback    │  │
  │  │ :free models  │  │ Providers    │  │ Chains (paid→free)│  │
  │  │ (NO KEY!)     │  │ (auto-keyed) │  │                   │  │
  │  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
  │         └─────────────────┼───────────────────┘              │
  │                           ▼                                   │
  │  ┌───────────────────────────────────────────────────────┐   │
  │  │    Adaptive Load Balancer + Concurrent Race Engine     │   │
  │  │  Score-based routing • Latency tracking • Token TPM    │   │
  │  │  Request dedup • Response caching • Stream support     │   │
  │  └───────────────────────────────────────────────────────┘   │
  │                           │                                   │
  │  ┌───────────────────────────────────────────────────────┐   │
  │  │            AutoKeyProvisioner v2.0                      │   │
  │  │  Env → File → Auto-template → Probe → Key Pool         │   │
  │  │  Dynamic discovery → Auto-recovery → Health monitor     │   │
  │  └───────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────┘

Free Access Sources (priority order):
  1. OpenRouter :free — NO API KEY NEEDED (just HTTP-Referer header)
  2. OpenRouter natively free models (Gemini, DeepSeek via OR)
  3. Google AI Studio — free tier (5-30 RPM, key from env/auto)
  4. Groq Cloud — free tier (30 RPM, key from env/auto)
  5. HuggingFace Inference — free for open models
  6. Together.ai — free tier
  7. Cerebras — free ultra-fast inference
  8. DeepInfra — free tier
  9. Proxy rotation — multiple free proxy endpoints
  10. Smart Fallback — paid model → best free alternative chain

Advanced Features:
  • Adaptive routing score: success_rate × latency_factor × availability
  • Concurrent multi-route race for high-priority calls
  • LRU response caching with content-hash deduplication
  • Per-provider token tracking (TPM accounting)
  • Dynamic free model discovery via OpenRouter /models API
  • SSE streaming support for real-time responses
  • Exponential backoff with jitter on failures
  • Latency tracking (p50/p95) per route
  • Auto route reordering based on runtime performance
  • Self-healing health monitor with auto-recovery
"""
# NOTE: Consider using arki_project.utils.feature_registry for optional imports


