
"""
plugin_system_pkg/hot_reloader.py — HotReloader
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class HotReloader:
    """Watch plugin files and reload on change."""

    def __init__(self):
        self._watched: dict[str, float] = {}  # path -> last_mtime

    def watch(self, path: str):
        import os
        try:
            self._watched[path] = os.path.getmtime(path)
        except OSError:
            self._watched[path] = 0

    def check_changes(self) -> list[str]:
        """Return paths that have changed since last check."""
        import os
        changed = []
        for path, mtime in self._watched.items():
            try:
                current = os.path.getmtime(path)
                if current > mtime:
                    changed.append(path)
                    self._watched[path] = current
            except OSError:
                pass
        return changed

    def reload_module(self, module_name: str) -> bool:
        """Reload a Python module by name."""
        import importlib, sys
        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                return True
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)
        return False



