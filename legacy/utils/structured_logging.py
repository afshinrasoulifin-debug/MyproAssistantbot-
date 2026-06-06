
from __future__ import annotations
"""
utils/structured_logging.py — Centralized Structured JSON Logging
══════════════════════════════════════════════════════════════════
Enterprise-grade logging: JSON format, correlation IDs, redaction.
Replaces all print() statements with structured, queryable logs.
"""

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar

# ── Context variables for request tracing ──
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
_user_id: ContextVar[int] = ContextVar("user_id", default=0)

SENSITIVE_KEYS = frozenset({
    "api_key", "token", "secret", "password", "authorization",
    "x-goog-api-key", "bearer", "openrouter", "groq_key",
})


def set_correlation_id(cid: str = "") -> str:
    """Set correlation ID for the current async context."""
    cid = cid or uuid.uuid4().hex[:12]
    _correlation_id.set(cid)
    return cid

def set_user_context(user_id: int) -> None:
    _user_id.set(user_id)


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter with redaction."""

    def __init__(self, service_name: str = "arki") -> None:
        super().__init__()
        self._service = service_name

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "service": self._service,
        }
        # Add context
        cid = _correlation_id.get("")
        if cid:
            entry["correlation_id"] = cid
        uid = _user_id.get(0)
        if uid:
            entry["user_id"] = uid
        # Add exception info
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]),
            }
        # Redact sensitive values
        msg = entry["msg"]
        for key in SENSITIVE_KEYS:
            if key in msg.lower():
                entry["msg"] = "[REDACTED — contains sensitive key]"
                break

        return json.dumps(entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Pretty console formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m", "INFO": "\033[32m",
        "WARNING": "\033[33m", "ERROR": "\033[31m",
        "CRITICAL": "\033[1;31m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        cid = _correlation_id.get("")
        prefix = f"[{cid[:8]}] " if cid else ""
        return f"{color}{record.levelname:7s}{self.RESET} {prefix}{record.name}: {record.getMessage()}"


def setup_logging(
    level: str = "INFO",
    json_output: bool = True,
    service_name: str = "arki",
) -> None:
    """Configure root logging for the entire application."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    if json_output and os.environ.get("LOG_FORMAT", "json") == "json":
        handler.setFormatter(JSONFormatter(service_name))
    else:
        handler.setFormatter(ConsoleFormatter())

    root.addHandler(handler)

    # Suppress noisy libraries
    for lib in ("httpx", "httpcore", "aiohttp.access", "aiogram.event"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name (convenience)."""
    return logging.getLogger(name)


