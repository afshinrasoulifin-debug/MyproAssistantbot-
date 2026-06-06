
"""platform_auto_pkg.cmd_templates_group — sub-module of platform_auto"""

from __future__ import annotations
from arki_project.exceptions import CallbackError, HandlerError

# ═══ TITANIUM v29.0 Integration ═══

__all__ = ['cmd_templates']

async def cmd_templates(message: Message) -> None:
    raw = extract_args(message.text or "", "/templates")

    tmps = _templates.get(message.chat.id, {})

    if not raw:
        if not tmps:
            await safe_reply(message, "📄 *قالب‌ها:*\n\n"
                "ذخیره قالب آگهی/کپشن برای استفاده مجدد:\n\n"
                "`/templates save [نام] | [متن قالب]`\n"
                "`/templates list` — لیست قالب‌ها\n"
                "`/templates use [نام]` — استفاده از قالب\n"
                "`/templates delete [نام]` — حذف")
        else:
            names = "\n".join(f"  📄 `{n}` — {t[:50]}..." for n, t in tmps.items())
            await safe_reply(message, f"📄 *قالب‌ها ({len(tmps)}):*\n\n{names}\n\n"
                "`/templates use [نام]`")
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()

    if action == "list":
        if not tmps:
            await message.answer("📄 قالبی ذخیره نشده.")
            return
        names = "\n".join(f"  📄 `{n}` — {t[:60]}..." for n, t in tmps.items())
        await safe_reply(message, f"📄 *قالب‌ها:*\n\n{names}")

    elif action == "save":
        data = parts[1] if len(parts) > 1 else ""
        if "|" not in data:
            await message.answer("❌ فرمت: `/templates save [نام] | [متن]`")
            return
        name, text = data.split("|", 1)
        name = name.strip()
        text = text.strip()
        _templates.setdefault(message.chat.id, {})[name] = text
        await message.answer(f"✅ قالب «{name}» ذخیره شد ({len(text)} کاراکتر).")

    elif action == "use":
        name = parts[1].strip() if len(parts) > 1 else ""
        if name in tmps:
            await safe_reply(message, f"📄 *قالب «{name}»:*\n\n{tmps[name]}")
        else:
            await message.answer(f"❌ قالب «{name}» پیدا نشد.")

    elif action == "delete":
        name = parts[1].strip() if len(parts) > 1 else ""
        if name in tmps:
            del tmps[name]
            await message.answer(f"🗑 قالب «{name}» حذف شد.")
        else:
            await message.answer(f"❌ قالب «{name}» پیدا نشد.")
    else:
        await message.answer("❌ `/templates save|list|use|delete`")



