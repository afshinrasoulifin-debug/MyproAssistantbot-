
"""
common_pkg/agents_submenu.py — Arki Engine v29.0.0
"""
from __future__ import annotations
from ._common import *  # noqa
from arki_project.exceptions import AgentExecutionError

# ── Agents Sub-menu ──

@router.callback_query(F.data == "menu:agents")
async def cb_agents_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Workflow", callback_data="act:workflow"),
         InlineKeyboardButton(text="👥 CRM", callback_data="act:crm")],
        [InlineKeyboardButton(text="💰 حسابداری", callback_data="act:finance"),
         InlineKeyboardButton(text="🕷 مانیتور وب", callback_data="act:monitor")],
        [InlineKeyboardButton(text="⚡ پاسخ خودکار", callback_data="act:autoreply"),
         InlineKeyboardButton(text="📅 برنامه محتوا", callback_data="act:plan")],
        [InlineKeyboardButton(text="« بازگشت", callback_data="menu:main")],
    ])
    try:
        await safe_edit_text(
            callback.message,
            "🧠 *ایجنت‌های هوشمند — 6 ایجنت*\n\n"
            "`/workflow` — پایپلاین محتوا ۵ مرحله‌ای\n"
            "`/crm` — مدیریت مشتری + سفارش\n"
            "`/finance` — حسابداری درآمد/هزینه\n"
            "`/monitor` — مانیتور تغییرات وب\n"
            "`/autoreply` — پاسخ خودکار\n"
            "`/plan` — تقویم محتوایی AI",
            reply_markup=kb,
        )
    except AgentExecutionError as e:
        logger.debug("Suppressed: %s", e)





