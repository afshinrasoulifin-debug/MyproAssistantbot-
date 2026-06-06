
"""
admin_pkg/_users.py — Arki Engine v29.0.0
"""
from ._common import *  # noqa

# ──────────── /users ────────────

@router.message(Command("users"))
async def cmd_users(message: Message, settings: Settings) -> None:
    """List all users."""
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        await message.answer("🚫 فقط ادمین.")
        return

    try:
        async with get_session() as session:
            result = await session.execute(
                select(User).order_by(User.created_at.desc()).limit(30)
            )
            users = result.scalars().all()

        if not users:
            await message.answer("هنوز کاربری ثبت نشده.")
            return

        lines = [f"👥 *کاربران* (آخرین {len(users)}):\n"]
        for u in users:
            status = "🚫" if u.is_banned else "✅"
            lines.append(
                f"{status} `{u.telegram_id}` — {u.full_name} "
                f"(@{u.username or 'N/A'})"
            )

        await send_long_text(message, "\n".join(lines))

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ خطا: {exc}")





