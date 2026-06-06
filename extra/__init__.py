
"""
tg_bot/extra — APEX Engine (UNMODIFIED)
───────────────────────────────────────────
The ENTIRE APEX project runs as-is as a Node.js API server.
This module provides a thin Telegram bridge to that API.

Architecture:
  [Telegram Bot] → [router.py] → [bridge.py] → [HTTP] → [APEX API :7860]
                                                              ↓
                                                    [Original TypeScript code]
                                                    [ZERO modifications]

The APEX source lives at: tg_bot/extra/apex_app/
  (complete copy, not a single byte changed)

Features (all from original APEX):
  56+ AI models • 5 tiers • ULTRAPLINIAN racing • CONSORTIUM hive-mind
  APEX prompt • L1B3RT4S combos • Parseltongue obfuscation
  AutoTune Pro • STM modules • Feedback loop • Telemetry • Metadata
  Dataset collection • Research API • Tier system
"""

try:
    from arki_project.extra.router import router as extra_router
    from arki_project.extra.router import get_apex_prompt, apply_stm_to_response
except (ImportError, ModuleNotFoundError):
    try:
        from extra.router import router as extra_router
        from extra.router import get_apex_prompt, apply_stm_to_response
    except (ImportError, ModuleNotFoundError):
        extra_router = None  # type: ignore
        get_apex_prompt = None  # type: ignore
        apply_stm_to_response = None  # type: ignore

__all__ = ["extra_router", "get_apex_prompt", "apply_stm_to_response"]


