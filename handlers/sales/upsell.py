
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
from typing import Any
tg_bot/handlers/sales/upsell.py — Upsell & Cross-sell Handler v2.0
═══════════════════════════════════════════════════════════════════
AI-powered upselling with product bundles, customer journey mapping,
and cross-sell recommendations.

Commands:
  /upsell <product>     — Upsell strategy
  /upsell bundle <items> — Create bundle
  /upsell journey <product> — Customer journey map
  /upsell cross <product> — Cross-sell ideas
"""


import logging

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
router = Router(name="sales_upsell_v2")


@router.message(Command("upsell"))
async def cmd_upsell(message: Message, ai_client: AIClient = None, settings: Settings = None, **kwargs) -> None:
    """Upsell and cross-sell strategy."""
    raw = extract_args(message.text or "", "/upsell")
    uid = message.from_user.id
    parts = raw.strip().split(maxsplit=1)

    if not parts:
        await safe_reply(message,
            "💡 *آپسل و کراس‌سل*\n\n"
            "*دستورات:*\n"
            "  `/upsell شمع معطر` — استراتژی آپسل\n"
            "  `/upsell bundle شمع | جاشمعی | کبریت` — بسته‌بندی\n"
            "  `/upsell journey شمع` — نقشه سفر مشتری\n"
            "  `/upsell cross شمع` — محصولات مکمل\n\n"
            "*آپسل:* محصول بهتر/گران‌تر\n"
            "*کراس‌سل:* محصول مکمل"
        )
        return

    action = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if not ai_client:
        await safe_reply(message, "⚠️ AI client در دسترس نیست.")
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    if action == "bundle" and args:
        items = [i.strip() for i in args.split("|")]
        prompt = (
            f"Create 3 product bundles from these items: {', '.join(items)}\n"
            "For each bundle: name, items, discount %, price strategy, target customer.\n"
            "In Farsi."
        )
    elif action == "journey" and args:
        prompt = (
            f"Map the complete customer journey for buying: {args}\n"
            "Stages: awareness → interest → consideration → purchase → post-purchase.\n"
            "At each stage: touchpoint, upsell opportunity, message. In Farsi."
        )
    elif action == "cross" and args:
        prompt = (
            f"Generate cross-sell recommendations for customers who buy: {args}\n"
            "List 5-7 complementary products with: why they pair well, "
            "recommended bundle discount, sales script. In Farsi."
        )
    else:
        product = " ".join(parts) if not args else f"{action} {args}"
        prompt = (
            f"Create a complete upsell/cross-sell strategy for: {product}\n"
            "Include:\n"
            "1. 3 upsell options (higher tier)\n"
            "2. 3 cross-sell products (complementary)\n"
            "3. Bundle suggestion with pricing\n"
            "4. Email/message templates for each\n"
            "5. When to offer each (timing)\n"
            "In Farsi. Be specific with prices in EUR."
        )

    try:
        result = await ai_client.ask(
            user_id=uid,
            text=prompt,
            system_prompt=(
                "You are a sales strategist specializing in e-commerce upselling. "
                "Give practical, specific advice with real price examples in EUR. In Farsi."
            ),
            temperature=0.7,
        )
        await safe_reply(message, f"💡 *آپسل:*\n\n{result}")
    except HandlerError as e:
        logger.error("upsell error: %s", e)
        err = _ti_sanitize(str(e)) if _TITANIUM_ACTIVE else str(e)
        await safe_reply(message, f"⚠️ خطا: {err}")


@router.callback_query(F.data.startswith("upsell:"))
async def cb_upsell(callback: CallbackQuery) -> Any:
    """Handle upsell callbacks."""
    await callback.answer("✅")


