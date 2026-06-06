
from __future__ import annotations
"""
architecture.helper.support_helper — SupportHelper, AdminHelper, ExecutionHelper
═══════════════════════════════════════════════════════════════════════════════
Support, admin, and execution helpers.
Covers: support-helper, admin-helper, execution-helper
"""
import logging, time
from typing import Any, Dict, List



logger = logging.getLogger(__name__)

class SupportHelper:
    """Helper for user support operations."""
    def __init__(self) -> None:
        self._tickets: List[Dict[str, Any]] = []

    def create_ticket(self, user_id: int, issue: str) -> Dict[str, Any]:
        ticket = {"id": len(self._tickets) + 1, "user_id": user_id,
                  "issue": issue, "status": "open", "created": time.time()}
        self._tickets.append(ticket)
        return ticket

    def resolve(self, ticket_id: int) -> bool:
        for t in self._tickets:
            if t["id"] == ticket_id:
                t["status"] = "resolved"
                return True
        return False

class AdminHelper:
    """Helper for admin operations."""
    def __init__(self) -> None:
        self._admin_actions: List[Dict[str, Any]] = []

    def log_action(self, admin_id: int, action: str, details: str = "") -> None:
        self._admin_actions.append({
            "admin_id": admin_id, "action": action, "details": details, "time": time.time()
        })

    def recent_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._admin_actions[-limit:]

class ExecutionHelper:
    """Helper for safe execution with error handling."""
    @staticmethod
    def safe_exec(fn, *args, default=None, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            logger.warning("safe_exec failed: %s", exc)
            return default

    @staticmethod
    def timed_exec(fn, *args, **kwargs) -> tuple:
        t0 = time.time()
        result = fn(*args, **kwargs)
        return result, time.time() - t0


