
"""
plugin_system_pkg/plugin_meta.py — PluginMeta
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginMeta:
    name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    state: PluginState = PluginState.UNLOADED
    module: Any = None
    error: Optional[str] = None






