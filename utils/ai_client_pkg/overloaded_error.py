
"""
ai_client_pkg/overloaded_error.py — OverloadedError
Arki Engine v29.0.0
"""
from __future__ import annotations
from ._base import *  # noqa

class OverloadedError(Exception):
    """503 / high demand / overloaded — should trigger fallback."""
    pass




