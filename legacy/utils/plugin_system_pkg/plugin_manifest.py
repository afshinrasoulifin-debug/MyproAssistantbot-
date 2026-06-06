
"""
plugin_system_pkg/plugin_manifest.py — PluginManifest
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginManifest:
    """Plugin metadata and configuration."""
    id: str
    name: str
    version: str
    description: str
    author: str = ""
    category: PluginCategory = PluginCategory.OTHER
    permissions: list[PluginPermission] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    hooks: list[str] = field(default_factory=list)
    entry_point: str = "main.py"
    config: dict[str, Any] = field(default_factory=dict)
    min_engine_version: str = "7.0"
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        return cls(
            id=data["id"], name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", ""),
            category=PluginCategory(data.get("category", "other")),
            permissions=[PluginPermission(p) for p in data.get("permissions", [])],
            dependencies=data.get("dependencies", {}),
            hooks=data.get("hooks", []),
            entry_point=data.get("entry_point", "main.py"),
            config=data.get("config", {}),
            tags=data.get("tags", []),
        )






