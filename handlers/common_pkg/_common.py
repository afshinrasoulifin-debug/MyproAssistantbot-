
from __future__ import annotations
"""
Shared imports for common sub-modules.
Arki Engine v29.0.0
"""
"""
tg_bot/handlers/common.py
──────────────────────────
Core command handlers: /start, /help, and main-menu callback dispatcher.
All callbacks properly wired to sub-menus.
"""


import logging

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from arki_project.config import Settings
from arki_project.utils.safe_send import safe_reply, safe_edit_text, safe_delete
from arki_project.keyboards.inline import main_menu_keyboard, back_to_menu_keyboard
from arki_project.utils.models_registry import MODELS

try:
    from arki_project.database.models import User
except ImportError:
    User = None  # type: ignore

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config as _ti_config
except ImportError:
    pass
__all__ = [
    "router", "logger", "VER", "_escape_md",
    "F", "Command", "CommandStart", "Message", "CallbackQuery",
    "InlineKeyboardMarkup", "InlineKeyboardButton",
    "Settings", "safe_reply", "safe_edit_text", "safe_delete",
    "main_menu_keyboard", "back_to_menu_keyboard", "MODELS", "User",
]

logger = logging.getLogger(__name__)
router = Router(name="common")

VER = "7.0"


def _escape_md(text: str) -> str:
    """Escape Markdown V1 special characters in user-provided text."""
    for ch in ("*", "_", "`", "[", "]"):
        text = text.replace(ch, f"\\{ch}")
    return text


# ──────────────── /start ────────────────


