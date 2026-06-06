
from __future__ import annotations
"""
tg_bot/handlers/sales/ — Sales Sub-package v9.6
Includes both legacy sales_brain.py AND new split modules.
"""
from aiogram import Router
import logging
logger = logging.getLogger(__name__)

router = Router(name="sales")

# Import legacy monolith router
try:
    from arki_project.handlers.sales_brain import router as _legacy
    router.include_router(_legacy)
except ImportError as _exc:
    logger.debug("Suppressed: %s", _exc)

# Import split sub-modules
_SUB_MODULES = [
    "analytics", "lead_scoring", "funnel",
    "pricing", "seo", "email", "crm", "upsell", "forecast",
]

for _mod_name in _SUB_MODULES:
    try:
        import importlib
        _mod = importlib.import_module(f"tg_bot.handlers.sales.{_mod_name}")
        if hasattr(_mod, "router"):
            router.include_router(_mod.router)
    except ImportError as _exc:
        logger.debug("Suppressed: %s", _exc)


