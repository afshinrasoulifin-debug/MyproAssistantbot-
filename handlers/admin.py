
from __future__ import annotations

"""Compatibility shim for the modular admin handler package.

The implementation lives in ``arki_project.handlers.admin_pkg``. Existing imports keep working, while
the runtime source of truth is the split package.
"""

from arki_project.handlers.admin_pkg import *  # noqa: F401,F403


