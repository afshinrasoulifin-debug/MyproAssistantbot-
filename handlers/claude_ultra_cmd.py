"""
tg_bot/handlers/claude_ultra_cmd.py — Claude Ultra Integration
──────────────────────────────────────────────────────────────
Commands for Claude Ultra AI models (powered by free-claude-code proxy):

  /claude_ultra [text]  — Chat with Claude Ultra (default: Sonnet 4)
  /claude_opus [text]   — Chat with Claude Opus 4 (strongest)
  /claude_sonnet [text] — Chat with Claude Sonnet 4 (balanced)
  /claude_haiku [text]  — Chat with Claude Haiku 4 (fastest)

Architecture:
  - Uses AIClient.ask() for full pipeline (history, fallback, transparency)
  - Model keys: claude-ultra-opus, claude-ultra-sonnet, etc.
  - Provider: claude_ultra → routes to free-claude-code proxy via _call_claude_ultra()
  - Proxy: Anthropic Messages API format → 17 free backends
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from arki_project.utils.safe_send import safe_reply, safe_edit_text

logger = logging.getLogger(__name__)
router = Router(name="claude_ultra_cmd")


# ═══════════ Model key mapping ═══════════

CLAUDE_ULTRA_DEFAULT = "claude-ultra-sonnet"

CLAUDE_CMD_MAP: dict[str, str] = {
    "claude_ultra":  "claude-ultra-sonnet",
    "claude_opus":   "claude-ultra-opus",
    "claude_sonnet": "claude-ultra-sonnet",
    "claude_haiku":  "claude-ultra-haiku",
    "claude35s":     "claude-ultra-35s",
    "claude35h":     "claude-ultra-35h",
    "claude3o":      "claude-ultra-3o",
}

SYSTEM_PROMPT = (
    "You are Claude, an AI assistant by Anthropic. "
    "You are helpful, harmless, and honest. "
    "Respond in the same language the user writes in. "
    "For Persian/Farsi input, respond in Persian."
)


# ═══════════ /claude_ultra — Main entry ═══════════

@router.message(Command("claude_ultra"))
async def cmd_claude_ultra(message: Message, **kwargs) -> None:
    """Chat with Claude Ultra (default: Sonnet 4)."""
    ai_client = kwargs.get("ai_client")
    text = (message.text or "").split(maxsplit=1)
    query = text[1].strip() if len(text) > 1 else ""

    if not query:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Claude Opus 4 — قوی‌ترین", callback_data="cu:claude-ultra-opus")],
            [InlineKeyboardButton(text="🟣 Claude Sonnet 4 — متعادل", callback_data="cu:claude-ultra-sonnet")],
            [InlineKeyboardButton(text="⚡ Claude Haiku 4 — سریع‌ترین", callback_data="cu:claude-ultra-haiku")],
            [InlineKeyboardButton(text="🔮 Claude 3.5 Sonnet", callback_data="cu:claude-ultra-35s"),
             InlineKeyboardButton(text="💨 Claude 3.5 Haiku", callback_data="cu:claude-ultra-35h")],
            [InlineKeyboardButton(text="👑 Claude 3 Opus", callback_data="cu:claude-ultra-3o")],
            [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
        ])
        await safe_reply(
            message,
            "🟣 *Claude Ultra* — هوش مصنوعی Anthropic (رایگان)\n\n"
            "مدل مورد نظر رو انتخاب کن یا مستقیم بنویس:\n"
            "`/claude_ultra [سوال]` → Sonnet 4\n"
            "`/claude_opus [سوال]` → Opus 4\n"
            "`/claude_haiku [سوال]` → Haiku 4\n\n"
            "⚡ *ساخته شده با free-claude-code*\n"
            "پروکسی به 17 ارائه‌دهنده رایگان",
            reply_markup=kb,
        )
        return

    await _process_claude_query(message, ai_client, CLAUDE_ULTRA_DEFAULT, query)


@router.message(Command("claude_opus"))
async def cmd_claude_opus(message: Message, **kwargs) -> None:
    """Chat with Claude Opus 4 (strongest)."""
    ai_client = kwargs.get("ai_client")
    text = (message.text or "").split(maxsplit=1)
    query = text[1].strip() if len(text) > 1 else ""
    if not query:
        await safe_reply(message, "💎 *Claude Opus 4*\n\nسوالت رو بنویس:\n`/claude_opus [سوال]`")
        return
    await _process_claude_query(message, ai_client, "claude-ultra-opus", query)


@router.message(Command("claude_sonnet"))
async def cmd_claude_sonnet(message: Message, **kwargs) -> None:
    """Chat with Claude Sonnet 4 (balanced)."""
    ai_client = kwargs.get("ai_client")
    text = (message.text or "").split(maxsplit=1)
    query = text[1].strip() if len(text) > 1 else ""
    if not query:
        await safe_reply(message, "🟣 *Claude Sonnet 4*\n\nسوالت رو بنویس:\n`/claude_sonnet [سوال]`")
        return
    await _process_claude_query(message, ai_client, "claude-ultra-sonnet", query)


@router.message(Command("claude_haiku"))
async def cmd_claude_haiku(message: Message, **kwargs) -> None:
    """Chat with Claude Haiku 4 (fastest)."""
    ai_client = kwargs.get("ai_client")
    text = (message.text or "").split(maxsplit=1)
    query = text[1].strip() if len(text) > 1 else ""
    if not query:
        await safe_reply(message, "⚡ *Claude Haiku 4*\n\nسوالت رو بنویس:\n`/claude_haiku [سوال]`")
        return
    await _process_claude_query(message, ai_client, "claude-ultra-haiku", query)


# ═══════════ Callback: model selection from inline menu ═══════════

@router.callback_query(lambda c: c.data and c.data.startswith("cu:"))
async def cb_claude_ultra_select(callback: CallbackQuery, **kwargs) -> None:
    """User selected a Claude Ultra model from the inline keyboard."""
    await callback.answer()
    ai_client = kwargs.get("ai_client")
    model_key = callback.data[3:]  # Remove "cu:" prefix

    # Special case: cu:menu → show Claude Ultra model selection menu
    if model_key == "menu":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Claude Opus 4 — قوی‌ترین", callback_data="cu:claude-ultra-opus")],
            [InlineKeyboardButton(text="🟣 Claude Sonnet 4 — متعادل", callback_data="cu:claude-ultra-sonnet")],
            [InlineKeyboardButton(text="⚡ Claude Haiku 4 — سریع‌ترین", callback_data="cu:claude-ultra-haiku")],
            [InlineKeyboardButton(text="🔮 Claude 3.5 Sonnet", callback_data="cu:claude-ultra-35s"),
             InlineKeyboardButton(text="💨 Claude 3.5 Haiku", callback_data="cu:claude-ultra-35h")],
            [InlineKeyboardButton(text="👑 Claude 3 Opus", callback_data="cu:claude-ultra-3o")],
            [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
        ])
        await safe_reply(
            callback.message,
            "🟣 *Claude Ultra* — هوش مصنوعی Anthropic (رایگان)\n\n"
            "مدل مورد نظر رو انتخاب کن یا مستقیم بنویس:\n"
            "`/claude_ultra [سوال]` → Sonnet 4\n"
            "`/claude_opus [سوال]` → Opus 4\n"
            "`/claude_haiku [سوال]` → Haiku 4\n\n"
            "⚡ پروکسی به ارائه‌دهنده‌های رایگان",
            reply_markup=kb,
        )
        return

    from arki_project.utils.models_core import CLAUDE_ULTRA_MODELS
    model_info = CLAUDE_ULTRA_MODELS.get(model_key)
    if not model_info:
        await safe_reply(callback.message, "❌ مدل نامعتبر")
        return

    # Set as user's active model (uses set_user_config — the real method)
    user_id = callback.from_user.id
    if ai_client is not None:
        try:
            await ai_client.set_user_config(user_id, "model", model_key)
        except Exception as e:
            logger.warning("Failed to save model pref: %s", e)

    await safe_reply(
        callback.message,
        f"{model_info.emoji} *{model_info.name}* فعال شد!\n\n"
        f"📝 {model_info.desc}\n"
        f"📊 Context: {model_info.ctx}\n\n"
        "حالا هر پیامی بفرست → پاسخ Claude Ultra",
    )


# ═══════════ Core processing ═══════════

async def _process_claude_query(
    message: Message,
    ai_client,
    model_key: str,
    query: str,
) -> None:
    """Process a Claude Ultra query through the full AIClient pipeline."""
    from arki_project.utils.models_core import get_model
    from arki_project.utils.text_processing import split_for_telegram

    user_id = message.from_user.id if message.from_user else 0
    model_info = get_model(model_key)

    # Send "typing" indicator
    wait_msg = await safe_reply(
        message,
        f"🟣 {model_info.emoji} *{model_info.name}*\n⏳ در حال پردازش...",
    )

    if ai_client is None:
        await safe_edit_text(
            wait_msg,
            "❌ *خطا:* AIClient در دسترس نیست.\n"
            "بات رو ریستارت کنید.",
        )
        return

    try:
        result = await ai_client.ask(
            user_id,
            query,
            model_key=model_key,
            system_prompt=SYSTEM_PROMPT,
        )

        if not result or not result.strip():
            await safe_edit_text(
                wait_msg,
                f"{model_info.emoji} *{model_info.name}*\n\n⚠️ پاسخ خالی دریافت شد. دوباره تلاش کنید.",
            )
            return

        # Split long messages for Telegram (4096 char limit)
        parts = split_for_telegram(result)
        for i, part in enumerate(parts):
            if i == 0 and wait_msg:
                try:
                    await safe_edit_text(
                        wait_msg,
                        f"{model_info.emoji} *{model_info.name}*\n\n{part}",
                    )
                except Exception:
                    await safe_reply(message, part)
            else:
                await safe_reply(message, part)

    except Exception as e:
        error_msg = str(e)
        logger.error("Claude Ultra error for user %d: %s", user_id, error_msg)
        try:
            await safe_edit_text(
                wait_msg,
                f"❌ *خطا در Claude Ultra*\n\n`{error_msg[:200]}`\n\n"
                "💡 مطمئن شو پروکسی free-claude-code ران هست.\n"
                "`CLAUDE_ULTRA_BASE_URL` و `CLAUDE_ULTRA_AUTH_TOKEN` رو چک کن.",
            )
        except Exception:
            await safe_reply(
                message,
                f"❌ *خطا در Claude Ultra*\n\n`{error_msg[:200]}`",
            )
