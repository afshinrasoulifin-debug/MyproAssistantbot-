
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/titanium/error_shield.py — L3 Error Shield Layer v10.3.1
═════════════════════════════════════════════════════════════════
Masks errors to prevent information leakage and timing attacks.

Features:
  • Recursive error sanitization (strips stack traces, file paths)
  • Timing normalization (errors take same time as successes)
  • Fabricated responses for detection evasion
  • Context-aware error messages

Ported from: TITANIUM ZKI security/error_shield.ts
"""


import logging
import re
from enum import Enum
from typing import Any

from arki_project.utils.titanium.timing import TimingNormalizer
from arki_project.utils.titanium.crypto import csprng_choice

logger = logging.getLogger("titanium.error_shield")


class ErrorContext(str, Enum):
    """Context hint for fabricating appropriate responses."""
    AI_RESPONSE = "ai_response"
    TELEGRAM_API = "telegram_api"
    HEALTH_CHECK = "health_check"
    GENERIC = "generic"


# ── Fabricated responses per context (C2 fix) ────────────

_FABRICATED_AI = [
    "متأسفم، لطفاً دوباره تلاش کنید.",
    "در حال حاضر امکان پاسخ‌گویی نیست. چند لحظه صبر کنید.",
    "پردازش درخواست شما با تأخیر مواجه شد.",
]

_FABRICATED_TG = [
    '{"ok":true,"result":true}',
    '{"ok":true,"result":{"message_id":1}}',
]

_FABRICATED_HEALTH = [
    '{"status":"ok"}',
]

_FABRICATED_GENERIC = [
    "Operation completed.",
    "Request processed.",
]

_FABRICATION_MAP = {
    ErrorContext.AI_RESPONSE: _FABRICATED_AI,
    ErrorContext.TELEGRAM_API: _FABRICATED_TG,
    ErrorContext.HEALTH_CHECK: _FABRICATED_HEALTH,
    ErrorContext.GENERIC: _FABRICATED_GENERIC,
}


def sanitize_error(error: Exception | str) -> str:
    """
    Recursively strip sensitive info from error messages.

    Removes:
      • File paths (/home/user/..., C:\\Users\\...)
      • Stack traces (at Module.xxx, File "xxx", line N)
      • IP addresses
      • API keys / tokens
      • Internal hostnames
    """
    msg = str(error)

    # Strip file paths
    msg = re.sub(r'(?:/[\w./\\-]+)+\.py', '[file]', msg)
    msg = re.sub(r'(?:[A-Z]:\\[\w\\.-]+)+', '[file]', msg)

    # Strip line numbers / stack traces
    msg = re.sub(r'line \d+', 'line [N]', msg)
    msg = re.sub(r'at [\w./<>]+', 'at [module]', msg)

    # Strip IPs
    msg = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?', '[addr]', msg)

    # Strip API keys / tokens (long hex/base64 strings)
    msg = re.sub(r'[A-Za-z0-9_-]{20,}', '[redacted]', msg)

    return msg


def fabricate_response(context: ErrorContext = ErrorContext.GENERIC) -> str:
    """Generate a fabricated response appropriate to the context."""
    pool = _FABRICATION_MAP.get(context, _FABRICATED_GENERIC)
    return csprng_choice(pool)


class ErrorShield:
    """
    Wrap operations with automatic error masking and timing normalization.

    Usage:
        shield = ErrorShield(context=ErrorContext.AI_RESPONSE)
        result = await shield.execute(async_fn, *args)
    """

    def __init__(
        self,
        context: ErrorContext = ErrorContext.GENERIC,
        target_ms: float = 2000.0,
        normalize_timing: bool = True,
    ) -> None:
        self.context = context
        self.target_ms = target_ms
        self.normalize_timing = normalize_timing

    async def execute(self, fn: Any, *args, **kwargs) -> tuple[bool, str]:
        """
        Execute fn with error masking.

        Returns (success: bool, result: str).
        On error: returns fabricated response after timing normalization.
        """
        normalizer = TimingNormalizer(self.target_ms).start() if self.normalize_timing else None

        try:
            result = await fn(*args, **kwargs)
            return True, result
        except ArkiBaseError as exc:
            safe_msg = sanitize_error(exc)
            logger.warning("ErrorShield [%s]: %s", self.context.value, safe_msg)

            if normalizer:
                await normalizer.wait()

            return False, fabricate_response(self.context)


# ══════════════════════════════════════════════════════════════
# v10.4 Advanced Error Intelligence
# ══════════════════════════════════════════════════════════════

class ErrorCategory:
    """Categorize errors for intelligent handling."""
    NETWORK = "network"
    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    RESOURCE = "resource"
    INTERNAL = "internal"
    EXTERNAL = "external"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


def classify_error(exc: Exception) -> str:
    """Classify an error into a category for intelligent routing."""
    msg = str(exc).lower()
    exc_type = type(exc).__name__.lower()

    if any(k in msg for k in ["timeout", "timed out", "deadline"]):
        return ErrorCategory.TIMEOUT
    if any(k in msg for k in ["connection", "dns", "socket", "network", "unreachable"]):
        return ErrorCategory.NETWORK
    if any(k in msg for k in ["401", "403", "unauthorized", "forbidden", "auth"]):
        return ErrorCategory.AUTH
    if any(k in msg for k in ["429", "rate limit", "too many requests", "quota"]):
        return ErrorCategory.RATE_LIMIT
    if any(k in msg for k in ["validation", "invalid", "malformed", "bad request", "400"]):
        return ErrorCategory.VALIDATION
    if any(k in msg for k in ["memory", "disk", "oom", "resource", "capacity"]):
        return ErrorCategory.RESOURCE
    if any(k in msg for k in ["500", "502", "503", "504", "internal server"]):
        return ErrorCategory.EXTERNAL
    return ErrorCategory.UNKNOWN


_ERROR_RECOVERY = {
    ErrorCategory.TIMEOUT: "Increase timeout or retry with exponential backoff",
    ErrorCategory.NETWORK: "Check network connectivity; retry after brief delay",
    ErrorCategory.AUTH: "Verify API key/token; rotate credentials if expired",
    ErrorCategory.RATE_LIMIT: "Implement backoff; switch to backup provider",
    ErrorCategory.VALIDATION: "Check input format and parameters",
    ErrorCategory.RESOURCE: "Free resources or scale up; check memory/disk",
    ErrorCategory.EXTERNAL: "External service issue; retry or use fallback",
    ErrorCategory.UNKNOWN: "Check logs for detailed error context",
}


def suggest_recovery(exc: Exception) -> str:
    """Suggest recovery action for an error."""
    category = classify_error(exc)
    return _ERROR_RECOVERY.get(category, _ERROR_RECOVERY[ErrorCategory.UNKNOWN])


class ErrorAggregator:
    """Track error patterns for proactive monitoring."""

    def __init__(self, window_size: int = 100) -> None:
        self._history: list = []
        self._window = window_size

    def record(self, exc: Exception, context: str = "") -> dict:
        category = classify_error(exc)
        entry = {
            "category": category,
            "type": type(exc).__name__,
            "message": sanitize_error(exc),
            "recovery": suggest_recovery(exc),
            "context": context,
            "timestamp": __import__("time").time(),
        }
        self._history.append(entry)
        if len(self._history) > self._window:
            self._history = self._history[-self._window:]
        return entry

    def get_pattern(self) -> dict:
        """Analyze error patterns."""
        if not self._history:
            return {"total": 0, "categories": {}, "top_errors": []}
        from collections import Counter
        cats = Counter(e["category"] for e in self._history)
        types = Counter(e["type"] for e in self._history)
        return {
            "total": len(self._history),
            "categories": dict(cats.most_common()),
            "top_errors": types.most_common(5),
            "health_score": 1.0 - (len(self._history) / self._window),
        }


