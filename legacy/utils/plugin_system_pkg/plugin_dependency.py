
"""
plugin_system_pkg/plugin_dependency.py — PluginDependency
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginDependency:
    """Plugin dependency specification."""
    plugin_id: str
    version_constraint: str = ">=0.0.0"
    optional: bool = False

    def is_satisfied_by(self, version: SemVer) -> bool:
        return version.satisfies(self.version_constraint)






