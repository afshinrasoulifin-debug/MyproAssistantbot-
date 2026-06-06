
from __future__ import annotations
"""
from typing import Any
tg_bot/handlers/translate_handler.py — Advanced Translation Handler v2.0
═══════════════════════════════════════════════════════════════════════
Enhanced translation with language detection, batch translate, 
translation history, and style options.

Commands:
  /tr <text>          — Auto-detect → Persian
  /tr en <text>       — Translate to English
  /tr fa en <text>    — Translate from Persian to English
  /tr batch           — Reply to message to translate to multiple languages
  /tr history         — Show recent translations
  /tr langs           — List supported languages
"""


import logging
import time
from collections import defaultdict

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.safe_send import safe_reply
from arki_project.handlers.shared import extract_args

try:
    from arki_project.utils.titanium.error_shield import sanitize_error as _ti_sanitize
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False

logger = logging.getLogger(__name__)
router = Router(name="translate_handler_v2")

# Language map with native names
LANGUAGES = {
    "fa": "فارسی", "en": "English", "ar": "العربية", "tr": "Türkçe",
    "de": "Deutsch", "fr": "Français", "es": "Español", "it": "Italiano",
    "ru": "Русский", "zh": "中文", "ja": "日本語", "ko": "한국어",
    "pt": "Português", "nl": "Nederlands", "sv": "Svenska", "fi": "Suomi",
    "hi": "हिन्दी", "ur": "اردو", "az": "Azərbaycan", "ku": "کوردی",
}

# In-memory translation history (per user, last 20)
_history: dict[int, list[dict]] = defaultdict(list)
MAX_HISTORY = 20


def _parse_tr_args(raw: str) -> tuple[str | None, str, str]:
    """Parse translation arguments. Returns (source_lang, target_lang, text)."""
    parts = raw.strip().split(maxsplit=2)
    if not parts:
        return None, "fa", ""

    # Check for subcommands
    if parts[0] in ("batch", "history", "langs", "help"):
        return None, parts[0], ""

    # /tr en hello world → target=en, text=hello world
    if len(parts) >= 2 and parts[0].lower() in LANGUAGES:
        if len(parts) >= 3 and parts[1].lower() in LANGUAGES:
            # /tr fa en some text → source=fa, target=en, text=...
            return parts[0].lower(), parts[1].lower(), parts[2]
        # /tr en some text → auto-detect, target=en
        return None, parts[0].lower(), " ".join(parts[1:])

    # /tr some text → auto-detect → fa
    return None, "fa", raw.strip()


@router.message(Command("tr"))
async def cmd_translate_advanced(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Advanced translation with language detection."""
    raw = extract_args(message.text or "", "/tr")

    if not raw.strip():
        # Check if replying to a message
        if message.reply_to_message and message.reply_to_message.text:
            raw = message.reply_to_message.text
        else:
            await safe_reply(message,
                "🌐 *ترجمه پیشرفته*\n\n"
                "*استفاده:*\n"
                "• `/tr متن` — ترجمه خودکار به فارسی\n"
                "• `/tr en متن` — ترجمه به انگلیسی\n"
                "• `/tr fa en متن` — فارسی → انگلیسی\n"
                "• `/tr batch` — ریپلای روی پیام → ترجمه به ۵ زبان\n"
                "• `/tr history` — تاریخچه ترجمه‌ها\n"
                "• `/tr langs` — لیست زبان‌ها"
            )
            return

    source, target, text = _parse_tr_args(raw)

    # Handle subcommands
    if target == "langs":
        lang_list = "\n".join(f"  `{k}` — {v}" for k, v in LANGUAGES.items())
        await safe_reply(message, f"🌐 *زبان‌های پشتیبانی:*\n\n{lang_list}")
        return

    if target == "history":
        uid = message.from_user.id
        hist = _history.get(uid, [])
        if not hist:
            await safe_reply(message, "📜 تاریخچه ترجمه خالی است.")
            return
        lines = []
        for i, h in enumerate(hist[-10:], 1):
            src = h.get("src", "?")[:40]
            tgt = h.get("tgt", "?")[:40]
            lang = h.get("lang", "?")
            lines.append(f"{i}. `{lang}` {src} → {tgt}")
        await safe_reply(message, f"📜 *آخرین ترجمه‌ها:*\n\n" + "\n".join(lines))
        return

    if target == "batch":
        # Batch translate to 5 languages
        reply = message.reply_to_message
        if not reply or not reply.text:
            await safe_reply(message, "⚠️ برای ترجمه دسته‌ای، روی یک پیام ریپلای کنید.")
            return
        text = reply.text
        batch_langs = ["en", "ar", "tr", "de", "fr"]
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        prompt = (
            f"Translate the following text into these languages: "
            f"{', '.join(LANGUAGES[l] for l in batch_langs)}.\n\n"
            f"Format: put each language on its own line with the language name first.\n\n"
            f"Text: {text}"
        )
        try:
            result = await ai_client.ask(
                user_id=message.from_user.id,
                text=prompt,
                system_prompt="You are a professional multilingual translator. Translate accurately.",
                temperature=0.3,
            )
            await safe_reply(message, f"🌐 *ترجمه دسته‌ای:*\n\n{result}")
        except Exception as e:
            logger.error("batch translate error: %s", e)
            await safe_reply(message, "⚠️ خطا در ترجمه دسته‌ای.")
        return

    if not text:
        text = raw.strip()

    # Main translation
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    src_name = LANGUAGES.get(source, "auto-detect") if source else "auto-detect"
    tgt_name = LANGUAGES.get(target, target)

    prompt = (
        f"Translate the following text to {tgt_name}"
        f"{f' from {LANGUAGES.get(source, source)}' if source else ''}.\n"
        f"Only output the translation. No explanations.\n\n"
        f"Text: {text}"
    )

    try:
        result = await ai_client.ask(
            user_id=message.from_user.id,
            text=prompt,
            system_prompt=(
                "You are a professional translator. Translate naturally and accurately. "
                "Preserve the tone and style. Only output the translation."
            ),
            temperature=0.3,
        )

        # Save to history
        uid = message.from_user.id
        _history[uid].append({
            "src": text[:100], "tgt": (result or "")[:100],
            "lang": f"{source or 'auto'}→{target}", "ts": time.time(),
        })
        if len(_history[uid]) > MAX_HISTORY:
            _history[uid] = _history[uid][-MAX_HISTORY:]

        header = f"🌐 *{src_name} → {tgt_name}:*\n\n"
        await safe_reply(message, header + (result or "—"))

    except Exception as e:
        logger.error("translate error: %s", e)
        err = _ti_sanitize(str(e)) if _TITANIUM_ACTIVE else str(e)
        await safe_reply(message, f"⚠️ خطا در ترجمه: {err}")


@router.callback_query(F.data.startswith("tr:"))
async def cb_translate(callback: CallbackQuery, ai_client: AIClient, settings: Settings) -> Any:
    """Handle translate callback buttons."""
    action = callback.data.split(":", 1)[1] if ":" in callback.data else ""
    await callback.answer(f"ترجمه: {action}")


