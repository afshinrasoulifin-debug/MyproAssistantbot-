
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
from typing import Any
tg_bot/handlers/summarize_handler.py — Advanced Summarizer v2.0
═══════════════════════════════════════════════════════════════
Multi-mode summarization: bullet points, executive summary,
tweet-sized, key facts extraction, and action items.

Commands:
  /sum <text>           — Smart summary (auto-selects mode)
  /sum bullet <text>    — Bullet point summary
  /sum exec <text>      — Executive summary (1 paragraph)
  /sum tweet <text>     — Tweet-sized (280 chars)
  /sum actions <text>   — Extract action items only
  /sum facts <text>     — Key facts extraction
  /sum tldr <text>      — One-line TLDR
"""


import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
router = Router(name="summarize_handler_v2")

MODES = {
    "bullet": {
        "label": "📋 نکات کلیدی",
        "prompt": "Summarize in clear bullet points (Farsi). Use • for each point. Max 10 points.",
    },
    "exec": {
        "label": "📊 خلاصه اجرایی",
        "prompt": "Write a concise executive summary in one paragraph (Farsi). Focus on decisions and impacts.",
    },
    "tweet": {
        "label": "🐦 توییت",
        "prompt": "Summarize in under 280 characters (Farsi). Make it engaging and shareable.",
    },
    "actions": {
        "label": "✅ اقدامات",
        "prompt": "Extract only the action items and next steps from this text. Format as numbered list in Farsi.",
    },
    "facts": {
        "label": "🔑 حقایق کلیدی",
        "prompt": "Extract the key facts, numbers, dates, and names. Format as a structured list in Farsi.",
    },
    "tldr": {
        "label": "⚡ TLDR",
        "prompt": "Summarize in exactly ONE sentence in Farsi. Be concise.",
    },
}


def _parse_sum_args(raw: str) -> tuple[str, str]:
    """Returns (mode, text)."""
    parts = raw.strip().split(maxsplit=1)
    if not parts:
        return "bullet", ""
    if parts[0].lower() in MODES:
        return parts[0].lower(), parts[1] if len(parts) > 1 else ""
    return "bullet", raw.strip()


@router.message(Command("sum"))
async def cmd_summarize_advanced(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Advanced multi-mode summarizer."""
    raw = extract_args(message.text or "", "/sum")

    # Check reply-to for source text
    source_text = ""
    if message.reply_to_message and message.reply_to_message.text:
        source_text = message.reply_to_message.text

    if not raw.strip() and not source_text:
        mode_list = "\n".join(f"  `{k}` — {v['label']}" for k, v in MODES.items())
        await safe_reply(message,
            "📝 *خلاصه‌ساز پیشرفته*\n\n"
            "*استفاده:*\n"
            "• `/sum متن` — خلاصه خودکار\n"
            "• `/sum bullet متن` — نکات کلیدی\n"
            "• `/sum exec متن` — خلاصه اجرایی\n"
            "• `/sum tweet متن` — اندازه توییت\n"
            "• `/sum actions متن` — اقدامات\n"
            "• `/sum tldr متن` — یک خط\n"
            "• ریپلای روی پیام + `/sum` — خلاصه آن پیام\n\n"
            f"*حالت‌ها:*\n{mode_list}"
        )
        return

    mode, text = _parse_sum_args(raw)
    if not text:
        text = source_text
    if not text:
        await safe_reply(message, "⚠️ متنی برای خلاصه‌سازی وارد نشده.")
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    mode_info = MODES.get(mode, MODES["bullet"])
    word_count = len(text.split())

    prompt = (
        f"{mode_info['prompt']}\n\n"
        f"Original text ({word_count} words):\n{text}"
    )

    try:
        result = await ai_client.ask(
            user_id=message.from_user.id,
            text=prompt,
            system_prompt=(
                "You are an expert summarizer. Be accurate — never add information "
                "not in the original. Respond in Farsi unless the text is in another language."
            ),
            temperature=0.3,
        )

        # Build mode selection keyboard for follow-up
        buttons = []
        row = []
        for k, v in MODES.items():
            if k != mode:
                row.append(InlineKeyboardButton(
                    text=v["label"], callback_data=f"sum:{k}",
                ))
                if len(row) == 3:
                    buttons.append(row)
                    row = []
        if row:
            buttons.append(row)

        header = f"{mode_info['label']} *خلاصه ({mode}):*\n\n"
        await safe_reply(
            message, header + (result or "—"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None,
        )

    except HandlerError as e:
        logger.error("summarize error: %s", e)
        err = _ti_sanitize(str(e)) if _TITANIUM_ACTIVE else str(e)
        await safe_reply(message, f"⚠️ خطا: {err}")


@router.callback_query(F.data.startswith("sum:"))
async def cb_summarize_mode(callback: CallbackQuery) -> Any:
    """Handle mode switch callback."""
    mode = callback.data.split(":")[1] if ":" in callback.data else "bullet"
    mode_info = MODES.get(mode, MODES["bullet"])
    await callback.answer(f"حالت: {mode_info['label']}")


