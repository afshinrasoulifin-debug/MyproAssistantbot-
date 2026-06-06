
from __future__ import annotations
"""
tg_bot/keyboards/inline.py
───────────────────────────
Reusable inline keyboard builders — all menus & sub-menus.
"""


from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup




def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu: v10.5 — comprehensive, organized, professional."""
    return InlineKeyboardMarkup(inline_keyboard=[
        # ── Core AI Engine ──
        [InlineKeyboardButton(text="🤖 چت هوشمند AI", callback_data="menu:ai_chat"),
         InlineKeyboardButton(text="🧬 APEX Engine", callback_data="menu:extra")],
        # ── Creative Studio ──
        [InlineKeyboardButton(text="🎨 تصویر و طراحی", callback_data="menu:image"),
         InlineKeyboardButton(text="✨ ابزارهای متنی", callback_data="menu:tools")],
        # ── Research & Media ──
        [InlineKeyboardButton(text="🔍 جستجو و تحقیق", callback_data="menu:search"),
         InlineKeyboardButton(text="📄 فایل و صدا", callback_data="menu:files_voice")],
        # ── Content & Sales Intelligence ──
        [InlineKeyboardButton(text="🎬 استودیوی محتوا", callback_data="menu:content_studio"),
         InlineKeyboardButton(text="🚀 موتور فروش", callback_data="menu:sales_engine")],
        [InlineKeyboardButton(text="🧠 هوش محتوا", callback_data="menu:content_brain"),
         InlineKeyboardButton(text="💰 هوش فروش", callback_data="menu:sales_brain")],
        # ── Marketing & Platforms ──
        [InlineKeyboardButton(text="📢 مارکتینگ TITAN", callback_data="menu:marketing"),
         InlineKeyboardButton(text="🌐 پلتفرم‌ها", callback_data="menu:platforms")],
        # ── Product & Automation ──
        [InlineKeyboardButton(text="📦 اتوماسیون محصول", callback_data="menu:product_auto"),
         InlineKeyboardButton(text="⚡ اتوماسیون", callback_data="menu:automation")],
        # ── Intelligence Agents ──
        [InlineKeyboardButton(text="🤖 ایجنت‌ها", callback_data="menu:agents"),
         InlineKeyboardButton(text="🧪 ویکتور AI", callback_data="menu:victor")],
        # ── Admin & Settings ──
        [InlineKeyboardButton(text="🛡 پنل ادمین", callback_data="menu:admin"),
         InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="menu:settings")],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Single 'back' button that returns to the main menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="« بازگشت به منو", callback_data="menu:main")]
        ]
    )


def back_button(callback_data: str = "menu:main") -> list[InlineKeyboardButton]:
    """Reusable back button row."""
    return [InlineKeyboardButton(text="« بازگشت", callback_data=callback_data)]


