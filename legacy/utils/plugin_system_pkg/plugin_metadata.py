
"""
plugin_system_pkg/plugin_metadata.py — PluginMetadata
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginMetadata:
    """Plugin metadata."""
    id: str
    name: str
    version: SemVer
    description: str = ""
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    dependencies: List[PluginDependency] = field(default_factory=list)
    permissions: Set[Permission] = field(default_factory=set)
    tags: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": str(self.version),
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "dependencies": [
                {"plugin": d.plugin_id, "version": d.version_constraint}
                for d in self.dependencies
            ],
            "permissions": [p.value for p in self.permissions],
            "tags": self.tags,
        }


# ═══════════════════════════════════════════════════════════════════
# Plugin Base Class
# ═══════════════════════════════════════════════════════════════════





