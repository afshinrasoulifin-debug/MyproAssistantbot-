
from __future__ import annotations
"""
utils/rbac.py — Role-Based Access Control (RBAC) System
══════════════════════════════════════════════════════════
Enterprise-grade access control replacing simple admin_id checks.

Roles: owner > admin > moderator > premium > user > guest
Permissions: granular action-based permissions
"""

import enum
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional, Set

logger = logging.getLogger(__name__)


class Role(enum.IntEnum):
    """User roles with hierarchy (higher = more permissions)."""
    GUEST = 0
    USER = 10
    PREMIUM = 20
    MODERATOR = 30
    ADMIN = 40
    OWNER = 50


class Permission(str, enum.Enum):
    """Granular permissions for access control."""
    # Basic
    USE_BOT = "use_bot"
    USE_AI = "use_ai"
    USE_SEARCH = "use_search"
    # Content
    CREATE_CONTENT = "create_content"
    MANAGE_TEMPLATES = "manage_templates"
    EXPORT_DATA = "export_data"
    # Sales
    USE_SALES = "use_sales"
    MANAGE_CRM = "manage_crm"
    VIEW_ANALYTICS = "view_analytics"
    # Admin
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"
    VIEW_LOGS = "view_logs"
    BROADCAST = "broadcast"
    MAINTENANCE = "maintenance"
    BACKUP = "backup"
    # System
    EXECUTE_AGENT = "execute_agent"
    BYPASS_LIMITS = "bypass_limits"
    SYSTEM_ADMIN = "system_admin"  # v17.3: GOD_MODE role terminated
    MANAGE_MODELS = "manage_models"
    MANAGE_API_KEYS = "manage_api_keys"
    SYSTEM_HEALTH = "system_health"


# Default permissions per role
ROLE_PERMISSIONS: Dict[Role, FrozenSet[Permission]] = {
    Role.GUEST: frozenset({
        Permission.USE_BOT,
    }),
    Role.USER: frozenset({
        Permission.USE_BOT, Permission.USE_AI, Permission.USE_SEARCH,
        Permission.CREATE_CONTENT,
    }),
    Role.PREMIUM: frozenset({
        Permission.USE_BOT, Permission.USE_AI, Permission.USE_SEARCH,
        Permission.CREATE_CONTENT, Permission.MANAGE_TEMPLATES,
        Permission.EXPORT_DATA, Permission.USE_SALES,
    }),
    Role.MODERATOR: frozenset({
        Permission.USE_BOT, Permission.USE_AI, Permission.USE_SEARCH,
        Permission.CREATE_CONTENT, Permission.MANAGE_TEMPLATES,
        Permission.EXPORT_DATA, Permission.USE_SALES,
        Permission.MANAGE_CRM, Permission.VIEW_ANALYTICS,
        Permission.VIEW_LOGS,
    }),
    Role.ADMIN: frozenset({
        Permission.USE_BOT, Permission.USE_AI, Permission.USE_SEARCH,
        Permission.CREATE_CONTENT, Permission.MANAGE_TEMPLATES,
        Permission.EXPORT_DATA, Permission.USE_SALES,
        Permission.MANAGE_CRM, Permission.VIEW_ANALYTICS,
        Permission.MANAGE_USERS, Permission.MANAGE_SETTINGS,
        Permission.VIEW_LOGS, Permission.BROADCAST,
        Permission.EXECUTE_AGENT, Permission.SYSTEM_HEALTH,
        Permission.MANAGE_MODELS,
    }),
    Role.OWNER: frozenset(Permission),  # All permissions
}


@dataclass
class UserAccess:
    """User's computed access profile."""
    user_id: int
    role: Role
    permissions: FrozenSet[Permission]
    extra_permissions: Set[Permission] = field(default_factory=set)
    denied_permissions: Set[Permission] = field(default_factory=set)
    expires_at: Optional[float] = None  # Unix timestamp

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at

    def has_permission(self, perm: Permission) -> bool:
        if self.is_expired:
            return False
        if perm in self.denied_permissions:
            return False
        return perm in self.permissions or perm in self.extra_permissions

    def has_role(self, min_role: Role) -> bool:
        if self.is_expired:
            return False
        return self.role >= min_role


class RBACManager:
    """Central RBAC manager."""

    def __init__(self) -> None:
        self._user_roles: Dict[int, Role] = {}
        self._extra_permissions: Dict[int, Set[Permission]] = {}
        self._denied: Dict[int, Set[Permission]] = {}
        self._owner_ids: Set[int] = set()
        self._admin_ids: Set[int] = set()
        self._loaded = False

    def load_from_config(self, admin_ids: list[int] = None, owner_ids: list[int] = None) -> None:
        """Load roles from config."""
        if admin_ids:
            for uid in admin_ids:
                self._admin_ids.add(uid)
                self._user_roles[uid] = Role.ADMIN
        if owner_ids:
            for uid in owner_ids:
                self._owner_ids.add(uid)
                self._user_roles[uid] = Role.OWNER
        # Also load from env
        env_admins = os.environ.get("ADMIN_IDS", "")
        if env_admins:
            for uid_str in env_admins.replace(",", " ").split():
                try:
                    uid = int(uid_str.strip())
                    self._admin_ids.add(uid)
                    if uid not in self._user_roles:
                        self._user_roles[uid] = Role.ADMIN
                except ValueError:
                    pass
        env_owners = os.environ.get("OWNER_IDS", "")
        if env_owners:
            for uid_str in env_owners.replace(",", " ").split():
                try:
                    uid = int(uid_str.strip())
                    self._owner_ids.add(uid)
                    self._user_roles[uid] = Role.OWNER
                except ValueError:
                    pass
        self._loaded = True
        logger.info("RBAC loaded: %d admins, %d owners", len(self._admin_ids), len(self._owner_ids))

    def get_user_role(self, user_id: int) -> Role:
        """Get user's role."""
        return self._user_roles.get(user_id, Role.USER)

    def set_user_role(self, user_id: int, role: Role) -> None:
        """Set user's role."""
        self._user_roles[user_id] = role
        logger.info("RBAC: user %d role set to %s", user_id, role.name)

    def grant_permission(self, user_id: int, perm: Permission) -> None:
        """Grant extra permission to user."""
        self._extra_permissions.setdefault(user_id, set()).add(perm)

    def deny_permission(self, user_id: int, perm: Permission) -> None:
        """Explicitly deny a permission."""
        self._denied.setdefault(user_id, set()).add(perm)

    def get_access(self, user_id: int) -> UserAccess:
        """Get full access profile for a user."""
        role = self.get_user_role(user_id)
        base_perms = ROLE_PERMISSIONS.get(role, frozenset())
        return UserAccess(
            user_id=user_id,
            role=role,
            permissions=base_perms,
            extra_permissions=self._extra_permissions.get(user_id, set()),
            denied_permissions=self._denied.get(user_id, set()),
        )

    def check(self, user_id: int, perm: Permission) -> bool:
        """Quick permission check."""
        return self.get_access(user_id).has_permission(perm)

    def require_role(self, user_id: int, min_role: Role) -> bool:
        """Quick role check."""
        return self.get_access(user_id).has_role(min_role)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_users": len(self._user_roles),
            "admins": len(self._admin_ids),
            "owners": len(self._owner_ids),
            "custom_permissions": sum(len(v) for v in self._extra_permissions.values()),
        }


_rbac: Optional[RBACManager] = None

def get_rbac() -> RBACManager:
    global _rbac
    if _rbac is None:
        _rbac = RBACManager()
    return _rbac


