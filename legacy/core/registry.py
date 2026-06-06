
from __future__ import annotations
"""
core/registry.py — Master Infrastructure Registry v29.0.0
═══════════════════════════════════════════════════════════════════
Central registry with resilient auto-discovery.

Instead of hardcoding 100+ imports (many of which may be phantom),
auto-discover all modules under core/* subpackages and register
whatever classes they export.
"""
import importlib
import logging
import os
import pkgutil
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class InfraRegistry:
    """Master registry for all infrastructure components.

    Uses resilient auto-discovery instead of hardcoded imports.
    Any module that fails to import is logged and skipped —
    the system keeps running with what works.

    Usage:
        registry = InfraRegistry()
        registry.auto_register()
        gateway = registry.get("ai_gateway")
    """

    _instance = None

    def __new__(cls) -> Any:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._components: Dict[str, Any] = {}
            cls._instance._initialized = False
            cls._instance._load_errors: List[Dict] = []
            cls._instance._subpackages_scanned = 0
        return cls._instance

    def register(self, name: str, component: Any) -> Any:
        self._components[name] = component
        logger.debug("Registered: %s (%s)", name, type(component).__name__)

    def get(self, name: str) -> Any:
        return self._components.get(name)

    def has(self, name: str) -> bool:
        return name in self._components

    @property
    def component_count(self) -> int:
        return len(self._components)

    def list_components(self) -> List[str]:
        return list(self._components.keys())

    def get_by_type(self, cls_name: str) -> List[Any]:
        return [c for c in self._components.values() if type(c).__name__ == cls_name]

    def _discover_subpackages(self) -> List[str]:
        """Find all Python subpackages under core/."""
        core_dir = os.path.dirname(os.path.abspath(__file__))
        packages = []
        for entry in sorted(os.listdir(core_dir)):
            pkg_path = os.path.join(core_dir, entry)
            if (os.path.isdir(pkg_path)
                    and os.path.isfile(os.path.join(pkg_path, "__init__.py"))
                    and entry not in ("__pycache__", "architecture", "combined", "core")):
                packages.append(entry)
        return packages

    def _try_import_and_register(self, module_path: str, package_name: str) -> Any:
        """Try to import a module and register any exported classes."""
        try:
            mod = importlib.import_module(module_path)
        except Exception as exc:
            self._load_errors.append({
                "module": module_path,
                "error": f"{type(exc).__name__}: {exc}",
            })
            logger.debug("Skip %s: %s", module_path, exc)
            return 0

        registered = 0
        # Look for classes defined in this module (not imported ones)
        for attr_name in dir(mod):
            obj = getattr(mod, attr_name)
            if (isinstance(obj, type)
                    and obj.__module__ == mod.__name__
                    and not attr_name.startswith("_")):
                # Convert CamelCase to snake_case for registry key
                import re
                snake = re.sub(r'(?<!^)(?=[A-Z])', '_', attr_name).lower()
                reg_key = f"{package_name}.{snake}"
                try:
                    instance = obj()
                    self.register(reg_key, instance)
                    registered += 1
                except Exception:
                    # Some classes need args — register the class itself
                    self.register(f"{package_name}.{snake}_cls", obj)
                    registered += 1
        return registered

    def auto_register(self) -> Any:
        """Auto-discover and register ALL infrastructure components resiliently."""
        if self._initialized:
            return
        self._initialized = True

        total_registered = 0
        subpackages = self._discover_subpackages()
        self._subpackages_scanned = len(subpackages)

        for pkg_name in subpackages:
            pkg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), pkg_name)
            for _, module_name, _ in pkgutil.iter_modules([pkg_dir]):
                module_path = f"arki_project.core.{pkg_name}.{module_name}"
                count = self._try_import_and_register(module_path, pkg_name)
                total_registered += count

        logger.info(
            "InfraRegistry: %d components from %d subpackages (%d load errors)",
            self.component_count,
            self._subpackages_scanned,
            len(self._load_errors),
        )

    @property
    def health(self) -> Dict:
        """Return registry health status."""
        return {
            "components": self.component_count,
            "subpackages": self._subpackages_scanned,
            "errors": len(self._load_errors),
            "error_rate": len(self._load_errors) / max(self.component_count + len(self._load_errors), 1),
        }

    def reset(self) -> Any:
        """Reset for testing."""
        self._components.clear()
        self._initialized = False
        self._load_errors.clear()
        self._subpackages_scanned = 0


