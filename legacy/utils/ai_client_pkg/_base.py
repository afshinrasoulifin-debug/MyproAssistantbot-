
from __future__ import annotations
"""
ai_client_pkg/_base.py — shared imports
Arki Engine v29.0.0
"""
"""
tg_bot/utils/ai_client.py — Multi-Provider AI Client v10 (Optimized)
═════════════════════════════════════════════════════════════════════
Multi-provider AI client with:

• Gemini (primary) → Groq (fallback) → OpenRouter (universal fallback)
• Same-provider fallback chain + cross-provider fallback
• DB-backed conversation persistence (survives restarts)
• AutoTune support
• Per-user model/persona selection
• Exponential backoff with jitter
• Think-tag cleaning

v10 Optimizations:
  ✅ Smart model selection based on task complexity
  ✅ Adaptive temperature per task type
  ✅ Smart context window packing (prioritize recent + relevant)
  ✅ Post-response quality validation integration
  ✅ Response length estimation for max_tokens optimization
"""

# NOTE: Consider using arki_project.utils.feature_registry for optional imports


# REMOVED: import httpx — now uses aiohttp via http_pool


# ═══ v26.0: Pro/Ultra Quality Engine imports ═══


