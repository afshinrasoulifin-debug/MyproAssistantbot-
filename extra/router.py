"""
extra/router.py — APEX Engine bridge (simplified stub)

The full APEX engine runs as a separate Node.js API server.
This module provides the Telegram bot bridge to that API.
When the APEX server is not available, these stubs allow graceful degradation.
"""
from __future__ import annotations

import logging
from aiogram import Router

logger = logging.getLogger(__name__)

router = Router(name="extra_router")


def get_apex_prompt(model_key: str = "default", tier: str = "t3") -> str:
    """Get APEX-style system prompt for model."""
    return (
        "You are APEX — an advanced AI assistant with comprehensive knowledge. "
        "Provide accurate, detailed, helpful responses."
    )


def apply_stm_to_response(text: str, stm_config: dict | None = None) -> str:
    """Apply STM (Style/Tone/Mode) transforms to response text."""
    return text


# Try loading full implementation from _pkg
try:
    from arki_project.extra.router_pkg import *  # noqa
    logger.debug("APEX router_pkg loaded successfully")
except Exception:
    logger.debug("APEX router_pkg not available — using stubs")


__all__ = ["router", "get_apex_prompt", "apply_stm_to_response"]
