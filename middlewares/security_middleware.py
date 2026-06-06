
from __future__ import annotations
from arki_project.exceptions import SecurityError
"""
middlewares/security_middleware.py — Security Scanning Middleware v10.4.1
════════════════════════════════════════════════════════════════════════
Bridges SecurityInterceptorFilter into the aiogram middleware chain.

This is the RUNTIME connection — without this middleware, the security
filter is dead code. Every incoming message passes through this layer.

Configurable via:
  - INFRA_APEX env var → bypasses all checks (admin override)
  - Settings.admin_ids → auto-cleared (whitelisted)
  - Settings sensitivity level
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

logger = logging.getLogger(__name__)

# Lazy import to avoid circular
_filter_instance = None


def _get_filter():
    global _filter_instance
    if _filter_instance is None:
        try:
            from arki_project.infrastructure.combined.security_interceptor_filter import (
                SecurityInterceptorFilter,
            )
            from arki_project.config import PRODUCTION_STRICT
            # v17.3: APEX terminated — security filter runs in strict mode
            _filter_instance = SecurityInterceptorFilter(apex=False)
            logger.info(
                "SecurityInterceptorFilter initialized (production_strict=%s, patterns=%d)",
                PRODUCTION_STRICT, len(_filter_instance._patterns),
            )
        except SecurityError as e:
            logger.warning("SecurityInterceptorFilter unavailable: %s", e)
    return _filter_instance


class SecurityMiddleware(BaseMiddleware):
    """aiogram middleware — scans every incoming message through SecurityInterceptorFilter.

    - Admins are auto-cleared (whitelisted) via settings.admin_ids
    - INFRA_APEX=true → all checks bypassed
    - Blocked messages are silently dropped (no error to user)
    - Threat data injected into handler data dict for downstream use
    """

    def __init__(self, admin_ids: list[int] | None = None, block_on_threat: bool = False):
        """
        Args:
            admin_ids: List of admin Telegram IDs to auto-clear.
            block_on_threat: If True, block (don't process) messages that contain threats.
                             If False, just tag them and let handlers decide.
        """
        super().__init__()
        self._admin_ids = set(admin_ids or [])
        self._block_on_threat = block_on_threat
        self._initialized = False
        self._stats = {
            "scanned": 0,
            "blocked": 0,
            "passed": 0,
            "bypassed": 0,
        }

    def _ensure_init(self):
        if self._initialized:
            return
        f = _get_filter()
        if f and self._admin_ids:
            f.auto_clear_admin([str(aid) for aid in self._admin_ids])
            logger.info("SecurityMiddleware: auto-cleared %d admin IDs", len(self._admin_ids))
        self._initialized = True

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        self._ensure_init()
        sec_filter = _get_filter()

        # Extract text from message
        text = ""
        user_id = ""
        if isinstance(event, Update) and event.message:
            msg = event.message
            text = msg.text or msg.caption or ""
            user_id = str(msg.from_user.id) if msg.from_user else ""
        elif isinstance(event, Message):
            text = event.text or event.caption or ""
            user_id = str(event.from_user.id) if event.from_user else ""

        # If no filter or no text, pass through
        if not sec_filter or not text:
            data["security_scan"] = {"safe": True, "bypassed": True}
            return await handler(event, data)

        # Scan
        self._stats["scanned"] += 1
        scan_result = sec_filter.scan_input(text, user_id=user_id)
        data["security_scan"] = scan_result

        if scan_result.get("safe", True):
            self._stats["passed"] += 1
            if scan_result.get("apex") or scan_result.get("cleared"):
                self._stats["bypassed"] += 1
            return await handler(event, data)
        else:
            # Threat detected
            if self._block_on_threat:
                self._stats["blocked"] += 1
                logger.warning(
                    "🛡️ SecurityMiddleware blocked user=%s severity=%s threats=%s",
                    user_id, scan_result.get("severity"), scan_result.get("threats"),
                )
                return None  # Silently drop
            else:
                # Tag but don't block — let handler decide
                self._stats["passed"] += 1
                return await handler(event, data)

    @property
    def stats(self) -> Dict:
        return dict(self._stats)


