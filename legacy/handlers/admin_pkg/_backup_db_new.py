
"""
admin_pkg/_backup_db_new.py — Arki Engine v29.0.0
"""
from ._common import *  # noqa

# ──────────── /backup_db (NEW) ────────────

@router.message(Command("backup_db"))
async def cmd_backup_db(message: Message, settings: Settings) -> None:
    """Export database as a file."""
    if not message.from_user or not _is_admin(message.from_user.id, settings):
        await message.answer("🚫 فقط ادمین.")
        return

    try:
        # Find the SQLite file
        db_url = settings.database_url
        if "sqlite" not in db_url:
            await message.answer("⚠️ بکاپ فقط برای SQLite پشتیبانی می‌شود.")
            return

        db_path = db_url.split("///")[-1]
        if not os.path.exists(db_path):
            await message.answer(f"❌ فایل دیتابیس یافت نشد: {db_path}")
            return

        # Copy to temp backup
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"/tmp/bot_backup_{timestamp}.db"
        shutil.copy2(db_path, backup_path)

        # Send as document
        backup_file = FSInputFile(backup_path, filename=f"arki_backup_{timestamp}.db")
        await message.answer_document(
            backup_file,
            caption=f"💾 *بکاپ دیتابیس*\n`{timestamp}`",
            parse_mode="Markdown",
        )

        # Cleanup
        os.remove(backup_path)
        logger.info("Admin %d exported database backup", message.from_user.id)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ خطا در بکاپ: {exc}")





