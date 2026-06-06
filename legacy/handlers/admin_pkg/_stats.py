
"""
admin_pkg/_stats.py — Arki Engine v29.0.0
"""
from ._common import *  # noqa

# ──────────── /stats ────────────

@router.message(Command("stats"))
async def cmd_stats(message: Message, settings: Settings) -> None:
    """Show comprehensive bot statistics."""
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        await message.answer("🚫 فقط ادمین.")
        return

    try:
        async with get_session() as session:
            # Total users
            total_users = (await session.execute(
                select(func.count()).select_from(User)
            )).scalar() or 0

            # Active users (have messages)
            active_users = (await session.execute(
                select(func.count(func.distinct(ChatMessage.user_id)))
            )).scalar() or 0

            # Banned users
            banned_users = (await session.execute(
                select(func.count()).select_from(User).where(User.is_banned == True)
            )).scalar() or 0

            # Total messages
            total_messages = (await session.execute(
                select(func.count()).select_from(ChatMessage)
            )).scalar() or 0

            # Messages today
            today = datetime.datetime.now(datetime.timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_messages = (await session.execute(
                select(func.count()).select_from(ChatMessage)
                .where(ChatMessage.created_at >= today)
            )).scalar() or 0

            # CRM stats
            total_customers = (await session.execute(
                select(func.count()).select_from(Customer)
            )).scalar() or 0

            # Reminders
            active_reminders = (await session.execute(
                select(func.count()).select_from(Reminder)
                .where(Reminder.sent == False)
            )).scalar() or 0

            # Recent users (last 5)
            recent_result = await session.execute(
                select(User).order_by(User.created_at.desc()).limit(5)
            )
            recent_users = recent_result.scalars().all()

            # Analytics: commands today
            try:
                commands_today = (await session.execute(
                    select(func.count()).select_from(AnalyticsEvent)
                    .where(AnalyticsEvent.created_at >= today)
                    .where(AnalyticsEvent.event_type == "command")
                )).scalar() or 0
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                commands_today = -1  # Table might not exist yet

            # Errors today
            try:
                errors_today = (await session.execute(
                    select(func.count()).select_from(AnalyticsEvent)
                    .where(AnalyticsEvent.created_at >= today)
                    .where(AnalyticsEvent.success == False)
                )).scalar() or 0
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                errors_today = -1

        uptime = format_duration(int(_time.monotonic() - _BOT_START_TIME))

        recent_list = "\n".join(
            f"  • `{u.telegram_id}` — {u.full_name} (@{u.username or 'N/A'})"
            for u in recent_users
        ) or "  هنوز کاربری ثبت نشده"

        # v26.1: AI Performance stats from analytics engine
        _ai_stats_section = ""
        try:
            from arki_project.utils.performance_analytics import get_analytics as _get_analytics
            _ai_analytics = _get_analytics()
            _ai_stats_section = "\n\n" + _ai_analytics.format_stats_message()
        except Exception as _ai_err:
            logger.debug("AI stats unavailable: %s", _ai_err)

        stats_text = (
            f"📊 *آمار ربات — Arki Engine v{_VERSION}*\n\n"
            f"⏱ آپتایم: `{uptime}`\n\n"
            "👥 *کاربران:*\n"
            f"  کل: *{format_number(total_users)}*\n"
            f"  فعال: *{format_number(active_users)}*\n"
            f"  بن‌شده: *{banned_users}*\n\n"
            "💬 *پیام‌ها:*\n"
            f"  کل: *{format_number(total_messages)}*\n"
            f"  امروز: *{format_number(today_messages)}*\n\n"
            "📈 *فعالیت امروز:*\n"
            f"  کامندها: *{format_number(commands_today)}*\n"
            f"  خطاها: *{errors_today}*\n\n"
            "🗂 *داده‌ها:*\n"
            f"  مشتریان CRM: *{total_customers}*\n"
            f"  یادآوری فعال: *{active_reminders}*\n\n"
            f"🆕 *آخرین کاربران:*\n{recent_list}"
            f"{_ai_stats_section}"
        )
        await send_long_text(message, stats_text)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ خطا در دریافت آمار: {exc}")





