
from __future__ import annotations
"""
tg_bot/utils/feature_check.py — Feature flag checker v9.6
Quick helper for handlers to check feature flags.
"""
import logging
from typing import Any

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

_flags = None

def is_enabled(flag_name: str, default: bool = True) -> bool:
    """Check if a feature flag is enabled."""
    global _flags
    if _flags is None:
        try:
            from arki_project.utils.feature_flags import get_feature_flags
            _flags = get_feature_flags()
        except Exception:
            return default
    try:
        return _flags.is_enabled(flag_name)
    except Exception:
        return default


def require_flag(flag_name: str) -> Any:
    """Decorator that skips handler if flag is disabled."""
    def decorator(func: Any) -> Any:
        import functools
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if not is_enabled(flag_name):
                logger.debug("Feature %s disabled, skipping %s", flag_name, func.__name__)
                return
            return await func(*args, **kwargs)
        return wrapper
    return decorator


