
from __future__ import annotations
from arki_project.exceptions import CallbackError, HandlerError
"""
from typing import Any
tg_bot/handlers/settings_handler.py — Settings Dashboard v2.0
════════════════════════════════════════════════════════════════
Full settings management with inline keyboards, theme selection,
notification preferences, language, and AI behavior config.

Commands:
  /config           — Show settings dashboard
  /config lang fa   — Set language
  /config theme     — Change theme
  /config notify    — Notification settings
  /config ai        — AI behavior settings
  /config export    — Export all settings as JSON
  /config reset     — Reset to defaults
"""


import json
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.safe_send import safe_reply, safe_edit_text
from arki_project.handlers.shared import extract_args

try:
    from arki_project.database.connection import get_session
    from arki_project.database.models import UserConfig
    from sqlalchemy import select, update as sa_update
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False


logger = logging.getLogger(__name__)
router = Router(name="settings_handler_v2")

# Default config
DEFAULT_CONFIG = {
    "language": "fa",
    "theme": "default",
    "notifications": True,
    "auto_translate": False,
    "ai_creativity": 0.7,
    "ai_max_tokens": 4096,
    "ai_persona": "assistant",
    "response_length": "medium",
}

# In-memory cache (backed by DB when available)
_user_configs: dict[int, dict] = {}


async def _load_config(uid: int) -> dict:
    """Load user config from DB or return defaults."""
    if uid in _user_configs:
        return _user_configs[uid]

    cfg = DEFAULT_CONFIG.copy()

    if _DB_AVAILABLE:
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(UserConfig).where(UserConfig.user_id == uid)
                )
                row = result.scalar_one_or_none()
                if row:
                    if row.model:
                        cfg["ai_persona"] = row.model
                    if hasattr(row, "language") and row.language:
                        cfg["language"] = row.language
        except HandlerError as e:
            logger.warning("Failed to load config for %d: %s", uid, e)

    _user_configs[uid] = cfg
    return cfg


async def _save_config(uid: int, cfg: dict) -> Any:
    """Save config to cache and DB."""
    _user_configs[uid] = cfg
    if _DB_AVAILABLE:
        try:
            async with get_session() as session:
                result = await session.execute(
                    select(UserConfig).where(UserConfig.user_id == uid)
                )
                row = result.scalar_one_or_none()
                if row:
                    row.model = cfg.get("ai_persona", "assistant")
                else:
                    session.add(UserConfig(
                        user_id=uid,
                        model=cfg.get("ai_persona", "assistant"),
                    ))
                await session.commit()
        except HandlerError as e:
            logger.warning("Failed to save config for %d: %s", uid, e)


def _build_dashboard(cfg: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Build settings dashboard message and keyboard."""
    lang_name = {"fa": "فارسی", "en": "English", "ar": "العربية"}.get(cfg["language"], cfg["language"])
    theme_name = {"default": "پیش‌فرض", "dark": "تاریک", "light": "روشن"}.get(cfg["theme"], cfg["theme"])
    length_name = {"short": "کوتاه", "medium": "متوسط", "long": "بلند"}.get(cfg["response_length"], "متوسط")

    text = (
        "⚙️ *داشبورد تنظیمات*\n\n"
        f"🌐 زبان: *{lang_name}*\n"
        f"🎨 تم: *{theme_name}*\n"
        f"🔔 اعلان‌ها: *{'فعال ✅' if cfg['notifications'] else 'غیرفعال ❌'}*\n"
        f"🤖 پرسونا: *{cfg['ai_persona']}*\n"
        f"🎯 خلاقیت AI: *{cfg['ai_creativity']}*\n"
        f"📏 طول پاسخ: *{length_name}*\n"
        f"🔄 ترجمه خودکار: *{'فعال ✅' if cfg['auto_translate'] else 'غیرفعال ❌'}*"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 زبان", callback_data="cfg:lang"),
            InlineKeyboardButton(text="🎨 تم", callback_data="cfg:theme"),
        ],
        [
            InlineKeyboardButton(
                text=f"🔔 اعلان {'❌' if cfg['notifications'] else '✅'}",
                callback_data="cfg:toggle_notify",
            ),
            InlineKeyboardButton(
                text=f"🔄 ترجمه {'❌' if cfg['auto_translate'] else '✅'}",
                callback_data="cfg:toggle_translate",
            ),
        ],
        [
            InlineKeyboardButton(text="📏 طول پاسخ", callback_data="cfg:length"),
            InlineKeyboardButton(text="🎯 خلاقیت", callback_data="cfg:creativity"),
        ],
        [
            InlineKeyboardButton(text="📤 خروجی JSON", callback_data="cfg:export"),
            InlineKeyboardButton(text="🔄 بازنشانی", callback_data="cfg:reset"),
        ],
    ])

    return text, keyboard


@router.message(Command("config"))
async def cmd_config(message: Message, settings: Settings, **kwargs) -> None:
    """Show or modify settings dashboard."""
    raw = extract_args(message.text or "", "/config")
    uid = message.from_user.id
    cfg = await _load_config(uid)

    if not raw.strip():
        text, kb = _build_dashboard(cfg)
        await safe_reply(message, text, reply_markup=kb)
        return

    parts = raw.strip().split()
    key = parts[0].lower()
    val = parts[1] if len(parts) > 1 else ""

    if key == "lang" and val:
        cfg["language"] = val
        await _save_config(uid, cfg)
        await safe_reply(message, f"✅ زبان تغییر کرد به: *{val}*")
    elif key == "reset":
        _user_configs[uid] = DEFAULT_CONFIG.copy()
        await _save_config(uid, DEFAULT_CONFIG.copy())
        await safe_reply(message, "✅ تنظیمات بازنشانی شد.")
    elif key == "export":
        data = json.dumps(cfg, ensure_ascii=False, indent=2)
        doc = BufferedInputFile(data.encode(), filename=f"settings_{uid}.json")
        await message.answer_document(doc, caption="📤 تنظیمات شما")
    else:
        text, kb = _build_dashboard(cfg)
        await safe_reply(message, text, reply_markup=kb)


@router.callback_query(F.data.startswith("cfg:"))
async def cb_config(callback: CallbackQuery) -> Any:
    """Handle settings callbacks."""
    action = callback.data.split(":")[1] if ":" in callback.data else ""
    uid = callback.from_user.id
    cfg = await _load_config(uid)

    if action == "toggle_notify":
        cfg["notifications"] = not cfg["notifications"]
        await _save_config(uid, cfg)
    elif action == "toggle_translate":
        cfg["auto_translate"] = not cfg["auto_translate"]
        await _save_config(uid, cfg)
    elif action == "length":
        order = ["short", "medium", "long"]
        idx = (order.index(cfg["response_length"]) + 1) % 3
        cfg["response_length"] = order[idx]
        await _save_config(uid, cfg)
    elif action == "creativity":
        vals = [0.3, 0.5, 0.7, 0.9, 1.0]
        idx = vals.index(cfg["ai_creativity"]) if cfg["ai_creativity"] in vals else 2
        cfg["ai_creativity"] = vals[(idx + 1) % len(vals)]
        await _save_config(uid, cfg)
    elif action == "theme":
        order = ["default", "dark", "light"]
        idx = (order.index(cfg["theme"]) + 1) % 3
        cfg["theme"] = order[idx]
        await _save_config(uid, cfg)
    elif action == "lang":
        order = ["fa", "en", "ar"]
        idx = (order.index(cfg["language"]) + 1) % 3
        cfg["language"] = order[idx]
        await _save_config(uid, cfg)
    elif action == "reset":
        cfg = DEFAULT_CONFIG.copy()
        _user_configs[uid] = cfg
        await _save_config(uid, cfg)
    elif action == "export":
        data = json.dumps(cfg, ensure_ascii=False, indent=2)
        await callback.message.answer(f"```json\n{data}\n```", parse_mode="Markdown")
        await callback.answer("✅")
        return

    text, kb = _build_dashboard(cfg)
    try:
        await safe_edit_text(callback.message, text, reply_markup=kb)
    except CallbackError as _err:
        logger.warning("Suppressed error: %s", _err)
    await callback.answer("✅")


