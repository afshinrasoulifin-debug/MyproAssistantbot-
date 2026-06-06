
from __future__ import annotations
"""Centralized bypass/stealth activation shim.

This script now delegates discovery and status reporting to ``utils.bypass_hub``
so bypass-related configuration has one source of truth.
"""

import os
from arki_project.utils.bypass_hub import bypass_status


def activate_stealth_config() -> None:
    defaults = {
        "ARKI_STEALTH_ENABLED": "true",
        "ARKI_WAF_ADAPTIVE": "true",
        "ARKI_CAPTCHA_SOLVER": "true",
        "ARKI_PROXY_ROTATOR_ENABLED": "true",
        "ARKI_SESSION_PERSISTENCE": "true",
        "ARKI_USE_EVASION_ARSENAL": "true",
        "ARKI_INJECT_CANVAS_NOISE": "true",
        "ARKI_INJECT_WEBGL_NOISE": "true",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


def main() -> None:
    activate_stealth_config()
    status = bypass_status()
    available = sum(1 for ok in status["components"].values() if ok)
    total = len(status["components"])
    print(f"Central bypass hub active: {available}/{total} components importable")
    print(f"Enabled flags: {status['config']}")


if __name__ == "__main__":
    main()


