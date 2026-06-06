
"""
plugin_system_pkg/permission.py — Permission
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class Permission(Enum):
    """Plugin capabilities/permissions."""
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    DATABASE = "database"
    EXECUTE = "execute"
    ADMIN = "admin"
    EVENTS = "events"
    HOOKS = "hooks"
    STORAGE = "storage"


# ═══════════════════════════════════════════════════════════════════
# Semantic Versioning
# ═══════════════════════════════════════════════════════════════════





