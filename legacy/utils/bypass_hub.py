
from __future__ import annotations
"""
utils.bypass_hub — centralized registry for existing stealth/network automation modules.

The hub is a wiring and discovery layer only. It does not add evasion behavior;
it gives the rest of the project a single place to discover already-existing
components and configuration flags.
"""

import importlib
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any


@dataclass(frozen=True)
class BypassComponent:
    name: str
    module: str
    purpose: str
    safe_default_enabled: bool = False


_COMPONENTS: dict[str, BypassComponent] = {
    "anti_detection": BypassComponent("anti_detection", "arki_project.utils.anti_detection", "browser identity consistency and automation-hardening helpers"),
    "evasion_scripts": BypassComponent("evasion_scripts", "arki_project.utils.evasion_scripts", "script catalog used by the browser worker"),
    "stealth_orchestrator": BypassComponent("stealth_orchestrator", "arki_project.utils.stealth_orchestrator", "high-level stealth worker orchestration"),
    "browser_validator": BypassComponent("browser_validator", "arki_project.utils.browser_validator", "browser stack validation"),
    "proxy_pool": BypassComponent("proxy_pool", "arki_project.utils.proxy_pool", "proxy pool management"),
    "proxy_rotator": BypassComponent("proxy_rotator", "arki_project.utils.proxy_rotator", "request proxy rotation"),
    "tls_fingerprint": BypassComponent("tls_fingerprint", "arki_project.utils.tls_fingerprint", "TLS fingerprint transport helpers"),
    "h2_transport": BypassComponent("h2_transport", "arki_project.utils.h2_transport", "HTTP/2 transport helpers"),
    "captcha_engine": BypassComponent("captcha_engine", "arki_project.utils.captcha_engine", "captcha detection/handling interface"),
    "waf_adaptive": BypassComponent("waf_adaptive", "arki_project.utils.waf_adaptive", "adaptive WAF feedback interface"),
    "fingerprint_engine": BypassComponent("fingerprint_engine", "arki_project.utils.fingerprint_engine", "fingerprint consistency interface"),
    "geo_consistency": BypassComponent("geo_consistency", "arki_project.utils.geo_consistency", "locale/timezone/proxy consistency checks"),
    "behavior_engine": BypassComponent("behavior_engine", "arki_project.utils.behavior_engine", "human-like interaction timing interface"),
    "request_pipeline": BypassComponent("request_pipeline", "arki_project.utils.request_pipeline", "network request pipeline"),
    "session_store": BypassComponent("session_store", "arki_project.sessions.session_store", "browser session persistence"),
    "browser_profile": BypassComponent("browser_profile", "arki_project.sessions.browser_profile", "browser profile persistence"),
    "stealth_worker": BypassComponent("stealth_worker", "arki_project.orchestration.workers.stealth_worker_pkg", "canonical modular stealth worker"),
}

_ENV_FLAGS = {
    "enabled": "ARKI_STEALTH_ENABLED",
    "waf_adaptive": "ARKI_WAF_ADAPTIVE",
    "captcha_solver": "ARKI_CAPTCHA_SOLVER",
    "proxy_rotator": "ARKI_PROXY_ROTATOR_ENABLED",
    "session_persistence": "ARKI_SESSION_PERSISTENCE",
    "use_evasion_arsenal": "ARKI_USE_EVASION_ARSENAL",
    "inject_canvas_noise": "ARKI_INJECT_CANVAS_NOISE",
    "inject_webgl_noise": "ARKI_INJECT_WEBGL_NOISE",
}


def list_bypass_components() -> dict[str, BypassComponent]:
    return dict(_COMPONENTS)


def get_bypass_config() -> dict[str, bool]:
    return {name: os.environ.get(env, "false").strip().lower() in {"1", "true", "yes", "on"} for name, env in _ENV_FLAGS.items()}


@lru_cache(maxsize=None)
def get_bypass_module(name: str) -> Any:
    component = _COMPONENTS[name]
    return importlib.import_module(component.module)


def has_bypass_component(name: str) -> bool:
    try:
        get_bypass_module(name)
        return True
    except Exception:
        return False


def bypass_status() -> dict[str, Any]:
    return {
        "config": get_bypass_config(),
        "components": {name: has_bypass_component(name) for name in _COMPONENTS},
    }


