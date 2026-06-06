
"""
stealth_worker_pkg/browser_engine.py — BrowserEngine
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class BrowserEngine(Enum):
    """Supported browser engines for stealth operations."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"




