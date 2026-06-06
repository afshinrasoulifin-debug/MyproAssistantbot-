
from __future__ import annotations
"""
utils/feature_registry.py — Centralized Feature Detection
══════════════════════════════════════════════════════════════
Arki Engine v29.0.0

Instead of scattering try/except ImportError blocks throughout the codebase,
use this registry to check feature availability.

Usage:
    from arki_project.utils.feature_registry import has_feature, get_feature

    if has_feature("quality_engine"):
        QualityGate = get_feature("quality_engine", "QualityGate")
"""

import importlib
import logging
from typing import Any, Dict

from arki_project.utils.tool_hub import has_tool, list_tools
from arki_project.utils.bypass_hub import list_bypass_components

logger = logging.getLogger(__name__)

_registry: Dict[str, Dict[str, Any]] = {}
_checked: Dict[str, bool] = {}


def _probe(module_path: str) -> bool:
    """Check if a module can be imported."""
    if module_path in _checked:
        return _checked[module_path]
    try:
        importlib.import_module(module_path)
        _checked[module_path] = True
        return True
    except Exception:
        _checked[module_path] = False
        return False


def register_feature(name: str, module_path: str, symbols: list[str] | None = None) -> bool:
    """Register a feature by trying to import its module.
    
    Returns True if the feature is available.
    """
    available = _probe(module_path)
    _registry[name] = {
        "module": module_path,
        "available": available,
        "symbols": symbols or [],
    }
    if not available:
        logger.debug("Feature %r not available (module %s)", name, module_path)
    return available


def has_feature(name: str) -> bool:
    """Check if a feature is available."""
    if name in _registry:
        return _registry[name]["available"]
    return False


def get_feature(name: str, symbol: str) -> Any:
    """Get a symbol from a registered feature.
    
    Returns None if the feature is not available.
    """
    if name not in _registry or not _registry[name]["available"]:
        return None
    try:
        mod = importlib.import_module(_registry[name]["module"])
        return getattr(mod, symbol, None)
    except Exception:
        return None


def get_module(name: str) -> Any:
    """Get the module for a registered feature."""
    if name not in _registry or not _registry[name]["available"]:
        return None
    try:
        return importlib.import_module(_registry[name]["module"])
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# Auto-register known features on import
# ═══════════════════════════════════════════════════════════════

_KNOWN_FEATURES = {
    # Quality Engine
    "smart_router": "arki_project.utils.smart_router",
    "consensus_engine": "arki_project.utils.consensus_engine",
    "adaptive_prompt": "arki_project.utils.adaptive_prompt",
    "performance_analytics": "arki_project.utils.performance_analytics",
    "quality_gate": "arki_project.utils.quality_gate",
    
    # Metrics & Monitoring
    "metrics_exporter": "arki_project.utils.metrics_exporter",
    "prometheus_client": "prometheus_client",
    "opentelemetry": "opentelemetry",
    
    # Canonical shared tools (legacy + modular variants are selected in utils.tool_hub)
    **{f"tool:{name}": (spec.legacy_module or spec.canonical_module) for name, spec in list_tools().items()},
    
    # Bypass/stealth wiring registry (centralized discovery only)
    **{f"bypass:{name}": component.module for name, component in list_bypass_components().items()},

    # Backward-compatible feature aliases
    "free_access_router": "arki_project.utils.free_access_router",
    
    # Infrastructure
    "internal_api_gateway": "arki_project.utils.internal_api_gateway",
    "event_bus": "arki_project.utils.event_bus",
    "automation_connector": "arki_project.utils.automation_connector",
    "marketing_engine": "arki_project.utils.marketing_engine",
    "search_privacy": "arki_project.utils.search_privacy",
    "proxy_rotator": "arki_project.utils.proxy_rotator",
    "request_queue": "arki_project.utils.request_queue",
    "api_key_manager": "arki_project.utils.api_key_manager",
    
    # Performance
    "performance_tracker": "arki_project.utils.performance_tracker",
    
    # Victor Brain
    "victor_brain": "arki_project.handlers.victor.brain",
    
    # External optional
    "redis": "redis",
    "tiktoken": "tiktoken",
    "stripe": "stripe",
    "cryptography": "cryptography",
    "curl_cffi": "curl_cffi",
}

for feat_name, mod_path in _KNOWN_FEATURES.items():
    register_feature(feat_name, mod_path)

logger.debug(
    "Feature registry: %d/%d features available",
    sum(1 for v in _registry.values() if v["available"]),
    len(_registry),
)


