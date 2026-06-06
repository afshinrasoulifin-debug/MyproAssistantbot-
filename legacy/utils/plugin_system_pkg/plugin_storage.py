
"""
plugin_system_pkg/plugin_storage.py — PluginStorage
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PluginStorage:
    """Isolated key-value storage for plugins."""

    def __init__(self) -> None:
        self.stores: Dict[str, Dict[str, Any]] = defaultdict(dict)

    def get(self, plugin_id: str, key: str,
            default: Any = None) -> Any:
        """Get a value from plugin storage."""
        return self.stores.get(plugin_id, {}).get(key, default)

    def set(self, plugin_id: str, key: str, value: Any) -> None:
        """Set a value in plugin storage."""
        self.stores[plugin_id][key] = value

    def delete(self, plugin_id: str, key: str) -> bool:
        """Delete a key from plugin storage."""
        if plugin_id in self.stores and key in self.stores[plugin_id]:
            del self.stores[plugin_id][key]
            return True
        return False

    def list_keys(self, plugin_id: str) -> List[str]:
        """List all keys for a plugin."""
        return list(self.stores.get(plugin_id, {}).keys())

    def clear(self, plugin_id: str) -> None:
        """Clear all storage for a plugin."""
        self.stores.pop(plugin_id, None)

    def size(self, plugin_id: str) -> int:
        """Get storage size in bytes."""
        data = self.stores.get(plugin_id, {})
        return len(json.dumps(data))

    def export_all(self) -> Dict[str, Dict[str, Any]]:
        """Export all storage."""
        return dict(self.stores)

    def import_all(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Import storage data."""
        for plugin_id, store in data.items():
            self.stores[plugin_id] = store


# ═══════════════════════════════════════════════════════════════════
# Config Validator
# ═══════════════════════════════════════════════════════════════════





