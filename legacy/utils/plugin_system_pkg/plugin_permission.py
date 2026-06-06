
"""
plugin_system_pkg/plugin_permission.py — PluginPermission
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginPermission(str, Enum):
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    EXECUTE = "execute"
    CRYPTO = "crypto"
    MEMORY = "memory"
    MODELS = "models"
    PLUGINS = "plugins"
    SYSTEM = "system"
    UNLIMITED = "unlimited"






