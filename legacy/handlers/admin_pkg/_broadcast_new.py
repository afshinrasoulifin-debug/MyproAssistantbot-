
"""
admin_pkg/_broadcast_new.py — Arki Engine v29.0.0
"""
from ._common import *  # noqa

# ──────────── /broadcast (NEW) ────────────

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, settings: Settings) -> None:
    """Broadcast a message to all non-banned users."""
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        await message.answer("🚫 فقط ادمین.")
        return

    text = extract_args(message.text or "", "/broadcast")
    if not text:
        await safe_reply(message,
            "📢 *ارسال همگانی*\n\n"
            "استفاده: `/broadcast متن پیام`\n\n"
            "⚠️ پیام به تمام کاربران غیر بن ارسال می‌شود.")
        return

    # Get all active users
    try:
        async with get_session() as session:
            result = await session.execute(
                select(User.telegram_id).where(User.is_banned == False)
            )
            user_ids = [row[0] for row in result.fetchall()]

        if not user_ids:
            await message.answer("❌ کاربری برای ارسال یافت نشد.")
            return

        status_msg = await safe_reply(message,
            f"📢 ارسال به {len(user_ids)} کاربر...")

        success = 0
        failed = 0
        blocked = 0
        bot = message.bot

        # v9.6: Batch status updates every 50 users
        batch_size = 50

        for i, uid in enumerate(user_ids):
            if i > 0 and i % batch_size == 0:
                try:
                    await status_msg.edit_text(
                        f"📢 ارسال... {i}/{len(user_ids)} "
                        f"(✅{success} ❌{failed})"
                    )
                except Exception as _exc:
                    logger.debug("Suppressed: %s", _exc)

            try:
                await bot.send_message(uid, text, parse_mode="Markdown")  # type: ignore[misc]
                success += 1
                await asyncio.sleep(0.05)  # v9.6: Flood control — max 20 msg/sec
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                failed += 1
                await asyncio.sleep(0.05)  # v9.6: Rate limit even on failure

        result_text = (
            "📢 *نتیجه ارسال همگانی:*\n\n"
            f"✅ موفق: *{success}*\n"
            f"❌ ناموفق: *{failed}*\n"
            f"📨 کل: *{len(user_ids)}*"
        )
        await safe_reply(message, result_text)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ خطا: {exc}")





