
"""
admin_pkg/_analytics_new.py — Arki Engine v29.0.0
"""
from ._common import *  # noqa

# ──────────── /analytics (NEW) ────────────

@router.message(Command("analytics"))
async def cmd_analytics(message: Message, settings: Settings) -> None:
    """Show usage analytics for today."""
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        await message.answer("🚫 فقط ادمین.")
        return

    try:
        today = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        async with get_session() as session:
            # Top commands today
            top_commands = (await session.execute(
                select(
                    AnalyticsEvent.command,
                    func.count().label("cnt"),
                )
                .where(AnalyticsEvent.created_at >= today)
                .where(AnalyticsEvent.event_type == "command")
                .where(AnalyticsEvent.command != "")
                .group_by(AnalyticsEvent.command)
                .order_by(func.count().desc())
                .limit(10)
            )).fetchall()

            # Avg response time today
            avg_time = (await session.execute(
                select(func.avg(AnalyticsEvent.response_time_ms))
                .where(AnalyticsEvent.created_at >= today)
                .where(AnalyticsEvent.success == True)
            )).scalar() or 0

            # Error count today
            error_count = (await session.execute(
                select(func.count()).select_from(AnalyticsEvent)
                .where(AnalyticsEvent.created_at >= today)
                .where(AnalyticsEvent.success == False)
            )).scalar() or 0

            # Unique users today
            unique_users = (await session.execute(
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(AnalyticsEvent.created_at >= today)
            )).scalar() or 0

        cmd_list = "\n".join(
            f"  {i+1}. `{cmd}` — {cnt} بار"
            for i, (cmd, cnt) in enumerate(top_commands)
        ) or "  هنوز داده‌ای نیست"

        text = (
            "📈 *آنالیتیکس امروز*\n\n"
            f"👤 کاربران یکتا: *{unique_users}*\n"
            f"⏱ میانگین پاسخ: *{int(avg_time)}ms*\n"
            f"❌ خطاها: *{error_count}*\n\n"
            f"*🏆 پرکاربردترین کامندها:*\n{cmd_list}"
        )
        await safe_reply(message, text)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ خطا: {exc}")





