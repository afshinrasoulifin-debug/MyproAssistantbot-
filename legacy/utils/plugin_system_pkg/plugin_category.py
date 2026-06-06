
"""
plugin_system_pkg/plugin_category.py — PluginCategory
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginCategory(str, Enum):
    TOOL = "tool"
    TRANSPORT = "transport"
    MODEL = "model"
    TRANSFORM = "transform"
    SECURITY = "security"
    STORAGE = "storage"
    ANALYTICS = "analytics"
    INTEGRATION = "integration"
    UTILITY = "utility"
    OTHER = "other"






