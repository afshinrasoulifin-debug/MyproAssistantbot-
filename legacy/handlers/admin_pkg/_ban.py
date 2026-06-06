
"""
admin_pkg/_ban.py — Arki Engine v29.0.0
"""
from ._common import *  # noqa

# ──────────── /ban ────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message, settings: Settings) -> None:
    """Ban a user by Telegram ID or by replying to their message."""
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        await message.answer("🚫 فقط ادمین.")
        return

    target_id = _get_target_id(message)
    if not target_id:
        await safe_reply(message, "🔨 *بن کاربر*\n\n"
            "استفاده: `/ban 123456789`\n"
            "یا ریپلای به پیام کاربر با `/ban`")
        return

    if target_id in settings.admin_ids:
        await message.answer("⚠️ ادمین قابل بن نیست.")
        return

    try:
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == target_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                await message.answer(f"❌ کاربر `{target_id}` یافت نشد.")
                return

            user.is_banned = True
            await session.flush()

        await safe_reply(message, f"🔨 *بن شد:* `{target_id}` ({user.full_name})")
        logger.info("Admin %d banned user %d", message.from_user.id, target_id)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ خطا: {exc}")





