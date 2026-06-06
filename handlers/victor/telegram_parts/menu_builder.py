
"""
telegram_parts/menu_builder.py — Victor menu/keyboard builder
Extracted from cmd_victor() to reduce complexity.
"""
from __future__ import annotations
from typing import Any, Dict, List


def build_victor_menu(section: str = "main") -> Dict[str, Any]:
    """Build inline keyboard for Victor menu sections.
    
    Centralizes the menu building logic that was duplicated
    across multiple branches of cmd_victor().
    """
    menus = {
        "main": {
            "text": "🤖 منوی اصلی ویکتور",
            "buttons": [
                [("🧠 هوش مصنوعی", "victor:ai"), ("📊 تحلیل", "victor:analytics")],
                [("🔧 ابزارها", "victor:tools"), ("⚙️ تنظیمات", "victor:settings")],
                [("📝 پرامپت‌ها", "victor:prompts"), ("🎭 پرسونا", "victor:persona")],
            ],
        },
        "ai": {
            "text": "🧠 بخش هوش مصنوعی",
            "buttons": [
                [("💬 چت", "victor:chat"), ("🔍 جستجو", "victor:search")],
                [("🖼 تصویر", "victor:image"), ("🗣 صدا", "victor:voice")],
                [("🔙 برگشت", "victor:main")],
            ],
        },
        "tools": {
            "text": "🔧 ابزارها",
            "buttons": [
                [("📱 QR Code", "victor:qr"), ("🔗 لینک کوتاه", "victor:short")],
                [("🔐 رمز ساز", "victor:password"), ("📋 ترجمه", "victor:translate")],
                [("🔙 برگشت", "victor:main")],
            ],
        },
    }
    return menus.get(section, menus["main"])


