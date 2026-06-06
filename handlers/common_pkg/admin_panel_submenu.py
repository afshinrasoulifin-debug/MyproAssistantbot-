
"""
common_pkg/admin_panel_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import HandlerError

# ── Admin Panel Sub-menu ──

@router.callback_query(F.data == "menu:admin")
async def cb_admin_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    uid = callback.from_user.id
    from arki_project.config import Settings as _Settings
    _s = _Settings()
    is_admin = uid in _s.admin_ids

    if not is_admin:
        try:
            await safe_edit_text(
                callback.message,
                "🔒 *دسترسی محدود*\n\nاین بخش فقط برای ادمین‌هاست.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
                ]),
            )
        except HandlerError as _err:
            logger.warning("Suppressed error: %s", _err)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار کاربران", callback_data="act:admin_stats"),
         InlineKeyboardButton(text="📢 پیام همگانی", callback_data="act:admin_broadcast")],
        [InlineKeyboardButton(text="🏥 سلامت سیستم", callback_data="act:admin_health"),
         InlineKeyboardButton(text="📈 آنالیتیکز", callback_data="act:admin_analytics")],
        [InlineKeyboardButton(text="🔧 تعمیرات", callback_data="act:admin_maintenance"),
         InlineKeyboardButton(text="💾 بکاپ دیتابیس", callback_data="act:admin_backup")],
        [InlineKeyboardButton(text="🚫 بن/آنبن", callback_data="act:admin_ban"),
         InlineKeyboardButton(text="⚡ عملکرد", callback_data="act:admin_perf")],
        [InlineKeyboardButton(text="🐚 شل سرور", callback_data="act:admin_shell"),
         InlineKeyboardButton(text="🎛 ارکستراتور", callback_data="act:admin_orch")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🛡 *پنل ادمین — کنترل کامل*\n\n"
            "📋 *دستورات:*\n"
            "`/stats` — آمار کاربران\n"
            "`/users` — لیست کاربران\n"
            "`/broadcast [پیام]` — ارسال همگانی\n"
            "`/health` — سلامت سیستم\n"
            "`/analytics` — آنالیتیکز\n"
            "`/maintenance` — حالت تعمیرات\n"
            "`/backup_db` — بکاپ دیتابیس\n"
            "`/ban [id]` / `/unban [id]` — بن/آنبن\n"
            "`/perfstats` — آمار عملکرد\n"
            "`/orchstatus` — وضعیت ارکستراتور\n"
            "`/sh [cmd]` — اجرای دستور شل\n"
            "`/py [code]` — اجرای کد پایتون\n"
            "`/sysinfo` — اطلاعات سیستم\n"
            "`/ping` — تست اتصال",
            reply_markup=kb,
        )
    except HandlerError as e:
        logger.debug("Suppressed: %s", e)





