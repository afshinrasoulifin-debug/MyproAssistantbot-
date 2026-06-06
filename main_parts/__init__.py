
"""
main_parts/ — Extracted sections from main.py

Reduces main.py from 1318 lines while preserving all functionality.
main.py remains the entry point and orchestrator.
"""
from __future__ import annotations
from .boot_infrastructure import _boot_v33_infrastructure  # noqa: F401
from .middleware_setup import register_middlewares  # noqa: F401
from .router_setup import register_routers  # noqa: F401
from .background_bootstrap import start_background_tasks  # noqa: F401


