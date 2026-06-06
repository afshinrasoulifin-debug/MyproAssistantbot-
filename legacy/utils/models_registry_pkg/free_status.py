
"""
models_registry_pkg/free_status.py — FreeStatus
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class FreeStatus(_FreeEnum):
    """Model's free access status."""
    DIRECT_FREE = "direct_free"           # Truly free on OpenRouter :free (no key needed)
    FALLBACK_FREE = "fallback_free"       # Paid model → free alternative via Smart Fallback
    KEY_FREE = "key_free"                 # Free tier available but needs registration for key

# Models confirmed directly free on OpenRouter (May 2026)


