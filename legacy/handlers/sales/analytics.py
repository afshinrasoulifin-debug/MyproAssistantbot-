
from __future__ import annotations
"""
tg_bot/handlers/sales/analytics.py — Sales Analytics v9.5
Extracted from sales_brain.py for maintainability.
"""
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from arki_project.utils.safe_send import safe_reply

logger = logging.getLogger(__name__)
router = Router(name="sales_analytics")


@router.message(Command("salesreport"))
async def cmd_sales_report(message: Message) -> None:
    """Generate a comprehensive sales analytics report."""
    user_id = message.from_user.id if message.from_user else 0

    try:
        from arki_project.database.connection import get_session
        from sqlalchemy import select, func
        from arki_project.database.models import AnalyticsEvent

        async with get_session() as session:
            # Last 30 days analytics
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            result = await session.execute(
                select(func.count()).select_from(AnalyticsEvent).where(
                    AnalyticsEvent.created_at >= cutoff
                )
            )
            total_events = result.scalar() or 0

        report = (
            "📊 *گزارش فروش (۳۰ روز اخیر)*\n\n"
            f"📈 کل رویدادها: {total_events}\n"
            f"📅 تاریخ: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
        )
        await safe_reply(message, report)
    except Exception as e:
        logger.error("Sales report error: %s", e)
        await safe_reply(message, "❌ خطا در تولید گزارش فروش")


@router.message(Command("conversion"))
async def cmd_conversion(message: Message) -> None:
    """Show conversion funnel metrics."""
    await safe_reply(message,
        "📊 *نرخ تبدیل*\n\n"
        "🔵 بازدید → علاقه‌مند: ---%\n"
        "🟢 علاقه‌مند → مشتری: ---%\n"
        "🟡 مشتری → خرید مجدد: ---%\n\n"
        "_(برای فعال‌سازی، دیتای فروش وارد کنید)_"
    )


