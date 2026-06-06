
"""
tg_bot/utils/web_automation_compat.py — Compatibility stub v9.8.6

web_automation.py was removed (deprecated in v9.6).
This module provides no-op stubs for backward compatibility.
Remove this file and all imports when all references are cleaned up.
"""
import logging
import warnings
from typing import Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)
warnings.warn(
    "web_automation is deprecated and will be removed in v10.0",
    DeprecationWarning,
    stacklevel=2,
)


class WebAutomation:
    """Deprecated stub."""
    def __init__(self, *a, **kw) -> None:
        logger.warning("WebAutomation is deprecated")


async def fetch_page(*a, **kw) -> Any:
    """Deprecated no-op."""
    logger.warning("fetch_page is deprecated")
    return None


async def screenshot(*a, **kw) -> Any:
    """Deprecated no-op."""
    return None


async def web_search(*a, **kw) -> Any:
    """Deprecated no-op."""
    return []


