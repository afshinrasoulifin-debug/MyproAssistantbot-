
from __future__ import annotations
"""
Shared imports for admin sub-modules.
Arki Engine v29.0.0
"""
"""
tg_bot/handlers/admin.py
────────────────────────
Admin-only commands: /ban, /unban, /stats, /users, /broadcast,
/health, /analytics, /maintenance, /backup_db.

v29.0.0:
  • /broadcast — send message to all users
  • /health — system health check
  • /analytics — usage analytics dashboard
  • /maintenance — toggle maintenance mode
  • /backup_db — export database
  • Enhanced /stats with more metrics
  • Better error handling
"""


import logging
import time as _time

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from arki_project.config import Settings
from arki_project.utils.safe_send import safe_reply, safe_edit_text, safe_delete
from arki_project.database.connection import health_check

# v26.0: Performance Analytics
try:
    from arki_project.utils.performance_analytics import get_analytics as _get_pa
    _HAS_ANALYTICS = True
except ImportError:
    _HAS_ANALYTICS = False

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config as _ti_config
except ImportError:
    pass
# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]


logger = logging.getLogger(__name__)

# v3.4: RBAC integration — replaces simple admin_id checks
try:
    from arki_project.utils.rbac import get_rbac, Permission, Role
    _HAS_RBAC = True
except ImportError:
    _HAS_RBAC = False
router = Router(name="admin")

_BOT_START_TIME = _time.monotonic()
try:
    from config import APP_VERSION as _VERSION
except ImportError:
    _VERSION = "29.0.0"


def _is_admin(user_id: int, settings: Settings) -> bool:
    """Check if user has admin access via RBAC or legacy admin_ids."""
    if _HAS_RBAC:
        rbac = get_rbac()
        if rbac.require_role(user_id, Role.ADMIN):
            return True
    return user_id in settings.admin_ids


def _check_permission(user_id: int, perm: Permission, settings: Settings) -> bool:
    """Check specific permission via RBAC with legacy fallback."""
    if _HAS_RBAC:
        return get_rbac().check(user_id, perm)
    return user_id in settings.admin_ids


# ──────────── /ping ────────────


