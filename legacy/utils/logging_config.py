
from __future__ import annotations
"""
tg_bot/utils/logging_config.py — Structured Logging v9.4
Consistent JSON logging across all handlers.
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: Any) -> Any:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = "INFO", json_format: bool = None) -> None:
    """Configure application logging."""
    if json_format is None:
        json_format = os.environ.get("JSON_LOGS", "false").lower() == "true"

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
        ))

    root.addHandler(handler)

    # Reduce noise from libraries
    for lib in ["httpx", "httpcore", "aiogram.event", "sqlalchemy.engine"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

import contextvars

# ── TITANIUM v29.0 Integration ──


correlation_id_var = contextvars.ContextVar("correlation_id", default="")


