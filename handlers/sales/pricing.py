
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
from typing import Any
tg_bot/handlers/sales/pricing.py — Smart Pricing Handler v2.0
═══════════════════════════════════════════════════════════════
AI-powered pricing with competitor analysis, margin calculation,
psychological pricing, and A/B price testing.

Commands:
  /pricing <product> <cost>  — Smart price suggestion
  /pricing analyze <product> — Competitor pricing analysis
  /pricing margin <price> <cost> — Margin calculator
  /pricing strategy <type>   — Pricing strategy guide
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


logger = logging.getLogger(__name__)
router = Router(name="sales_pricing_v2")

STRATEGIES = {
    "premium": "قیمت‌گذاری پریمیوم — ارزش بالا، مارجین بالا",
    "penetration": "نفوذی — قیمت پایین برای جذب بازار",
    "skimming": "اسکیمینگ — شروع بالا، کاهش تدریجی",
    "bundle": "بسته‌ای — تخفیف ترکیبی",
    "psychological": "روان‌شناختی — ۹۹ به جای ۱۰۰",
    "dynamic": "پویا — بر اساس تقاضا",
}


def _calc_margin(price: float, cost: float) -> dict:
    """Calculate profit margins."""
    profit = price - cost
    margin_pct = (profit / price * 100) if price else 0
    markup_pct = (profit / cost * 100) if cost else 0
    return {
        "price": price,
        "cost": cost,
        "profit": profit,
        "margin_pct": margin_pct,
        "markup_pct": markup_pct,
    }


@router.message(Command("pricing"))
async def cmd_pricing(message: Message, ai_client: AIClient = None, settings: Settings = None, **kwargs) -> None:
    """Smart pricing handler."""
    raw = extract_args(message.text or "", "/pricing")
    uid = message.from_user.id
    parts = raw.strip().split()

    if not parts:
        strat_list = "\n".join(f"  `{k}` — {v}" for k, v in STRATEGIES.items())
        await safe_reply(message,
            "💲 *قیمت‌گذاری هوشمند*\n\n"
            "*دستورات:*\n"
            "  `/pricing شمع معطر 5€` — پیشنهاد قیمت\n"
            "  `/pricing analyze شمع` — تحلیل رقبا\n"
            "  `/pricing margin 25 8` — محاسبه مارجین\n"
            "  `/pricing strategy premium` — راهنما\n\n"
            f"*استراتژی‌ها:*\n{strat_list}"
        )
        return

    action = parts[0].lower()

    # Margin calculator
    if action == "margin" and len(parts) >= 3:
        try:
            price = float(parts[1].replace("€", "").replace("$", ""))
            cost = float(parts[2].replace("€", "").replace("$", ""))
        except ValueError:
            await safe_reply(message, "⚠️ فرمت: `/pricing margin 25 8`")
            return

        m = _calc_margin(price, cost)
        health = "🟢" if m["margin_pct"] > 50 else "🟡" if m["margin_pct"] > 30 else "🔴"
        await safe_reply(message,
            f"📊 *محاسبه مارجین*\n\n"
            f"💰 قیمت فروش: *{m['price']:.2f}€*\n"
            f"🏭 هزینه تولید: *{m['cost']:.2f}€*\n"
            f"💚 سود: *{m['profit']:.2f}€*\n"
            f"{health} مارجین: *{m['margin_pct']:.1f}%*\n"
            f"📈 مارک‌آپ: *{m['markup_pct']:.1f}%*\n\n"
            f"*پیشنهاد:*\n"
            f"  🏷 قیمت روان‌شناختی: *{price - 0.01:.2f}€*\n"
            f"  📦 قیمت بسته ۳تایی: *{price * 2.7:.2f}€*\n"
            f"  ⭐ قیمت پریمیوم: *{price * 1.5:.2f}€*"
        )
        return

    # Strategy guide
    if action == "strategy" and len(parts) >= 2:
        strategy = parts[1].lower()
        if strategy not in STRATEGIES:
            await safe_reply(message, f"⚠️ استراتژی `{strategy}` نامعتبر.")
            return

        if not ai_client:
            await safe_reply(message, f"📖 *{STRATEGIES[strategy]}*")
            return

        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        try:
            result = await ai_client.ask(
                user_id=uid,
                text=(
                    f"Explain the {strategy} pricing strategy in detail.\n"
                    "Include: when to use, pros/cons, real examples, implementation steps.\n"
                    "In Farsi. Be practical."
                ),
                system_prompt="You are a pricing strategist. Give actionable advice in Farsi.",
                temperature=0.5,
            )
            await safe_reply(message, f"💲 *استراتژی {strategy}:*\n\n{result}")
        except HandlerError as e:
            logger.error("pricing strategy error: %s", e)
            await safe_reply(message, f"📖 *{STRATEGIES[strategy]}*")
        return

    # Competitor analysis
    if action == "analyze":
        product = " ".join(parts[1:]) if len(parts) > 1 else ""
        if not product:
            await safe_reply(message, "⚠️ محصول را وارد کنید: `/pricing analyze شمع`")
            return

        if not ai_client:
            await safe_reply(message, "⚠️ AI client در دسترس نیست.")
            return

        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        try:
            result = await ai_client.ask(
                user_id=uid,
                text=(
                    f"Analyze pricing for: {product}\n"
                    "Research: competitor price ranges, market positioning, recommended price points.\n"
                    "Include specific EUR prices. In Farsi."
                ),
                system_prompt="You are a market analyst. Give data-driven pricing analysis in Farsi.",
                temperature=0.5,
            )
            await safe_reply(message, f"📊 *تحلیل قیمت: {product}*\n\n{result}")
        except HandlerError as e:
            logger.error("pricing analyze error: %s", e)
            await safe_reply(message, "⚠️ خطا در تحلیل.")
        return

    # Default: smart price suggestion
    product = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]
    cost_str = parts[-1] if len(parts) > 1 else ""
    cost = 0.0
    try:
        cost = float(cost_str.replace("€", "").replace("$", ""))
    except ValueError:
        product = " ".join(parts)

    if not ai_client:
        if cost > 0:
            m = _calc_margin(cost * 3, cost)
            await safe_reply(message,
                f"💲 *پیشنهاد سریع: {product}*\n"
                f"  قیمت پیشنهادی: *{cost * 3:.2f}€* (مارجین {m['margin_pct']:.0f}%)"
            )
        else:
            await safe_reply(message, "💲 لطفاً هزینه تولید را اضافه کنید.")
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    prompt = f"Suggest optimal pricing for: {product}"
    if cost > 0:
        prompt += f"\nProduction cost: {cost}€"
    prompt += (
        "\nProvide: recommended price, pricing tier (budget/mid/premium), "
        "psychological price point, bundle price, margin analysis.\nIn Farsi."
    )

    try:
        result = await ai_client.ask(
            user_id=uid, text=prompt,
            system_prompt="You are a pricing expert. Give specific EUR prices. In Farsi.",
            temperature=0.5,
        )
        await safe_reply(message, f"💲 *قیمت‌گذاری: {product}*\n\n{result}")
    except HandlerError as e:
        logger.error("pricing error: %s", e)
        await safe_reply(message, "⚠️ خطا در پردازش.")


@router.callback_query(F.data.startswith("price:"))
async def cb_pricing(callback: CallbackQuery) -> Any:
    """Handle pricing callbacks."""
    await callback.answer("✅")


