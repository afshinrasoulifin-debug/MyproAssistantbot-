
"""
utils/models_registry.py — Thin re-export shim
────────────────────────────────────────────────
All implementation moved to focused modules:
  • models_core.py     — ModelInfo, MODELS dict, tiers, lookups, free status
  • personas.py        — Personas, AutoTune, TTS
  • text_processing.py — clean_think_tags, STM pipeline, split_for_telegram
  • apex_bypass.py     — APEX prompt, L1B3RT4S, boost, consortium

This file re-exports everything so existing imports keep working.
"""
from __future__ import annotations

import re  # needed by some legacy importers

# ═══════════ models_core ═══════════
from arki_project.utils.models_core import (
    APEX_TIERS,
    CLAUDE_ULTRA_MODELS,
    DEFAULT_MODEL,
    FALLBACK_CLAUDE_ULTRA,
    FALLBACK_GEMINI,
    FALLBACK_GROQ,
    FreeStatus,
    MODELS,
    ModelInfo,
    UNCENSORED_KEYS,
    _NEW_FREE_MODELS,
    available_models,
    get_apex_tier,
    get_free_badge,
    get_free_label,
    get_free_status,
    get_model,
    is_uncensored,
    smart_model_key,
    working_model_key,
)

# ═══════════ personas ═══════════
from arki_project.utils.personas import (
    PERSONAS,
    Persona,
    TTS_MODEL,
    TTS_VOICES,
    autotune,
)

# ═══════════ text_processing ═══════════
from arki_project.utils.text_processing import (
    clean_think_tags,
    split_for_telegram,
    user_friendly_error,
)

# ═══════════ apex_bypass ═══════════
from arki_project.utils.apex_bypass import (
    APEX_SYSTEM_PROMPT,
    CONSORTIUM_SYSTEM_PROMPT,
    DEPTH_DIRECTIVE,
    GodmodeBoostResult,
    GodmodeParamKey,
    L1B3RT4S_COMBOS,
    LibertasCombo,
    LibertasComboId,
    LibertasInjectionResult,
    apply_apex_boost,
    apply_libertas_combo,
    build_apex_messages,
    get_all_libertas_models,
    get_fast_libertas_combos,
    get_libertas_combo,
    inject_libertas_query,
)

# Public API — everything importable via `from models_registry import X`
__all__ = [
    # models_core
    "APEX_TIERS", "CLAUDE_ULTRA_MODELS", "DEFAULT_MODEL",
    "FALLBACK_CLAUDE_ULTRA", "FALLBACK_GEMINI", "FALLBACK_GROQ",
    "FreeStatus", "MODELS", "ModelInfo", "UNCENSORED_KEYS",
    "available_models", "get_apex_tier", "get_free_badge", "get_free_label",
    "get_free_status", "get_model", "is_uncensored", "smart_model_key",
    "working_model_key",
    # personas
    "PERSONAS", "Persona", "TTS_MODEL", "TTS_VOICES", "autotune",
    # text_processing
    "clean_think_tags", "split_for_telegram", "user_friendly_error",
    # apex_bypass
    "APEX_SYSTEM_PROMPT", "CONSORTIUM_SYSTEM_PROMPT", "DEPTH_DIRECTIVE",
    "GodmodeBoostResult", "GodmodeParamKey", "L1B3RT4S_COMBOS",
    "LibertasCombo", "LibertasComboId", "LibertasInjectionResult",
    "apply_apex_boost", "apply_libertas_combo", "build_apex_messages",
    "get_all_libertas_models", "get_fast_libertas_combos",
    "get_libertas_combo", "inject_libertas_query",
]


