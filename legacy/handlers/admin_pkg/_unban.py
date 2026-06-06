
"""
admin_pkg/_unban.py — Arki Engine v29.0.0
"""
from ._common import *  # noqa

# ──────────── /unban ────────────

@router.message(Command("unban"))
async def cmd_unban(message: Message, settings: Settings) -> None:
    """Unban a user by Telegram ID."""
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        await message.answer("🚫 فقط ادمین.")
        return

    target_id = _get_target_id(message)
    if not target_id:
        await safe_reply(message, "✅ *آنبن کاربر*\n\nاستفاده: `/unban 123456789`")
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

            user.is_banned = False
            await session.flush()

        await safe_reply(message, f"✅ *آنبن شد:* `{target_id}` ({user.full_name})")
        logger.info("Admin %d unbanned user %d", message.from_user.id, target_id)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ خطا: {exc}")





