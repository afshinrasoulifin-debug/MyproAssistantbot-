
from __future__ import annotations
"""
tg_bot/utils/error_handler.py — Centralized error handling v29.0.0
Provides a decorator to wrap handlers with proper error logging.
"""
import functools
import logging
import traceback
from typing import Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)


def safe_handler(func: Any) -> None:
    """Decorator that catches and LOGS exceptions instead of silently swallowing them."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> None:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(
                "Handler %s failed: %s\n%s",
                func.__name__, e, traceback.format_exc()
            )
            # v10.3.1: Track error in perf tracker
            track_error(func.__name__, e)
            # Try to notify user
            for arg in args:
                if hasattr(arg, 'answer'):
                    try:
                        await arg.answer("⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")
                    except Exception as _e:
                        logger.debug("Suppressed: %s", _e)  # v10.1: no longer silent
                    break
            return None
    return wrapper


# v10.3: Error tracking integration
def track_error(handler_name: str, error: Exception) -> None:
    """Record handler error to performance tracker."""
    try:
        from arki_project.utils.performance_tracker import perf_tracker
        perf_tracker._errors[f"handler.{handler_name}"] += 1
    except Exception as _err:
        logger.warning("Suppressed error: %s", _err)


