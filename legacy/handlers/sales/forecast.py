
from __future__ import annotations
"""
tg_bot/handlers/sales/forecast.py — Sales Forecast Handler v2.0
════════════════════════════════════════════════════════════════
Data-driven forecasting from real CRM data.

Commands:
  /forecast             — 30-day forecast + insights
  /forecast 7           — 7-day forecast
  /forecast 90          — Quarter forecast
  /forecast insights    — Sales insights & trends
"""


import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from arki_project.utils.safe_send import safe_reply
from typing import Any


logger = logging.getLogger(__name__)
router = Router(name="sales_forecast")


def _extract_args(text: str, command: str) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


@router.message(Command("forecast"))
async def cmd_forecast(message: Message, **kwargs) -> Any:
    """Sales forecasting from real data."""
    raw = _extract_args(message.text or "", "/forecast")

    try:
        from arki_project.utils.forecast_engine import get_forecast_engine, SalesDataPoint
        engine = get_forecast_engine()
    except ImportError:
        await safe_reply(message, "⚠️ `forecast_engine.py` پیدا نشد.")
        return

    # Load data from database if engine is empty
    if not engine._data:
        await _load_from_db(engine, message.from_user.id)

    if not raw:
        # Default: 30-day forecast
        raw = "30"

    if raw == "insights":
        # ─── /forecast insights ───
        insights = engine.get_insights()
        text = "📊 *تحلیل فروش*\n\n"
        for insight in insights:
            text += f"• *{insight.metric}:* {insight.value}\n"
            if insight.change:
                arrow = "📈" if insight.change > 0 else "📉"
                text += f"  {arrow} {insight.change:+.1f}%\n"
        await safe_reply(message, text)
        return

    # ─── /forecast [days] ───
    try:
        days = int(raw)
    except ValueError:
        await safe_reply(message,
            "📈 *پیش‌بینی فروش*\n\n"
            "دستورات:\n"
            "`/forecast` — ۳۰ روز آینده\n"
            "`/forecast 7` — ۷ روز آینده\n"
            "`/forecast 90` — فصل آینده\n"
            "`/forecast insights` — تحلیل فروش"
        )
        return

    await safe_reply(message, f"⏳ محاسبه پیش‌بینی {days} روزه...")

    fc = engine.forecast(days)

    trend_emoji = {"growing": "📈", "stable": "➡️", "declining": "📉"}.get(fc.trend, "❓")
    conf_bar = "█" * int(fc.confidence * 10) + "░" * (10 - int(fc.confidence * 10))

    text = (
        f"📈 *پیش‌بینی فروش — {days} روز آینده*\n\n"
        f"💰 درآمد پیش‌بینی: *€{fc.predicted_revenue:,.2f}*\n"
        f"🛒 سفارشات: *~{fc.predicted_orders}*\n"
        f"{trend_emoji} روند: *{fc.trend}* ({fc.growth_rate:+.1f}%)\n"
        f"🎯 اطمینان: `{conf_bar}` {fc.confidence*100:.0f}%\n\n"
    )

    if fc.details:
        text += "*جزئیات:*\n"
        text += f"  📊 میانگین روزانه: €{fc.details.get('daily_avg', 0):,.2f}\n"
        text += f"  📈 WMA: €{fc.details.get('wma_daily', 0):,.2f}/روز\n"
        text += f"  📉 LR: €{fc.details.get('lr_daily', 0):,.2f}/روز\n"
        text += f"  📋 داده‌ها: {fc.details.get('data_points', 0)} روز\n"

        if fc.details.get("error"):
            text += f"\n⚠️ {fc.details['error']}"

    await safe_reply(message, text)


async def _load_from_db(engine: Any, user_id: int) -> Any:
    """Load sales data from FinanceRecord table."""
    try:
        from arki_project.database.connection import get_session
        from arki_project.database.models import FinanceRecord
        from arki_project.utils.forecast_engine import SalesDataPoint
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(
                select(FinanceRecord).where(
                    FinanceRecord.user_id == user_id,
                    FinanceRecord.record_type == "income",
                ).order_by(FinanceRecord.created_at)
            )
            records = result.scalars().all()

        for r in records:
            engine.add_sale(SalesDataPoint(
                date=r.created_at,
                amount=float(r.amount),
                product=r.description or "",
                platform=r.category or "",
                customer_id=r.user_id,
            ))

    except Exception as exc:
        logger.warning("Could not load finance data: %s", exc)


