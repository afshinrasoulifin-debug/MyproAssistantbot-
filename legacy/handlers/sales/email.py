
from __future__ import annotations
"""
from typing import Any
tg_bot/handlers/sales/email.py — Real Email Marketing Handler v2.0
═════════════════════════════════════════════════════════════════
Actually sends emails via email_engine. Not just AI text generation.

Commands:
  /email                — Dashboard: provider status + stats
  /email send [to] [subject] — Send single email
  /email welcome [email] — Send welcome email
  /email winback [email] [discount%] — Send win-back campaign
  /email promo [email] [title] — Send promotion
  /email bulk [template] — Send to all CRM contacts
  /email test [email]    — Send test email to yourself
"""


import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
)

from arki_project.utils.safe_send import safe_reply


logger = logging.getLogger(__name__)
router = Router(name="sales_email")


def _extract_args(text: str, command: str) -> str:
    """Extract args after command."""
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


@router.message(Command("email"))
async def cmd_email(message: Message, **kwargs) -> Any:
    """Handle /email command — Email Marketing Hub."""
    raw = _extract_args(message.text or "", "/email")
    ai_client = kwargs.get("ai_client") or (message.bot and message.bot.get("ai_client"))

    if not raw:
        # Show dashboard
        try:
            from arki_project.utils.email_engine import get_email_engine
            engine = get_email_engine()
            providers = engine.get_configured_providers()
            status = "✅ آماده" if engine.is_configured() else "❌ تنظیم نشده"

            text = (
                "📧 *ایمیل مارکتینگ*\n\n"
                f"وضعیت: {status}\n"
                f"Providerها: {', '.join(providers) if providers else 'هیچکدام'}\n\n"
                "━━━━━━━━━━━━━━━\n"
                "*دستورات:*\n"
                "📨 `/email send [ایمیل] | [عنوان] | [متن]`\n"
                "👋 `/email welcome [ایمیل]` — ایمیل خوش‌آمد\n"
                "💕 `/email winback [ایمیل] | [تخفیف%]`\n"
                "🔥 `/email promo [ایمیل] | [عنوان] | [پیام]`\n"
                "📋 `/email bulk [template]` — ارسال به همه مشتریان CRM\n"
                "🧪 `/email test [ایمیل]` — تست\n\n"
                "*تنظیم:* یکی از این env varها رو ست کن:\n"
                "```\n"
                "SMTP_USER + SMTP_PASSWORD\n"
                "SENDGRID_API_KEY\n"
                "RESEND_API_KEY\n"
                "```"
            )
        except ImportError:
            text = (
                "📧 *ایمیل مارکتینگ*\n\n"
                "⚠️ `email_engine.py` پیدا نشد.\n"
                "فایل `utils/email_engine.py` رو اضافه کنید."
            )
        await safe_reply(message, text)
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    try:
        from arki_project.utils.email_engine import get_email_engine, EmailMessage
        engine = get_email_engine()
    except ImportError:
        await safe_reply(message, "⚠️ `email_engine.py` پیدا نشد.")
        return

    if not engine.is_configured():
        await safe_reply(message,
            "⚠️ هیچ email provider تنظیم نشده.\n"
            "یکی از اینها رو تو `.env` بذار:\n"
            "`SMTP_USER` + `SMTP_PASSWORD`\n"
            "`SENDGRID_API_KEY`\n"
            "`RESEND_API_KEY`"
        )
        return

    # ─── /email send [to] | [subject] | [body] ───
    if action == "send":
        fields = [f.strip() for f in args.split("|")]
        if len(fields) < 3:
            await safe_reply(message,
                "📨 فرمت:\n"
                "`/email send email@example.com | عنوان | متن ایمیل`"
            )
            return

        to, subject, body = fields[0], fields[1], fields[2]

        # Use AI to enhance the email body if ai_client available
        html_body = f"<div style='direction:rtl;font-family:Tahoma;'><p>{body}</p></div>"
        if ai_client:
            try:
                enhanced = await ai_client.chat(
                    user_id=message.from_user.id,
                    message=f"این متن ایمیل رو حرفه‌ای‌تر بنویس (HTML با استایل فارسی):\n{body}",
                    system="شما طراح ایمیل حرفه‌ای هستید. فقط HTML خروجی بده.",
                )
                if enhanced and "<" in enhanced:
                    html_body = enhanced
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        result = await engine.send(EmailMessage(
            to=to, subject=subject, html_body=html_body,
        ))

        if result.success:
            await safe_reply(message, f"✅ ایمیل ارسال شد به `{to}` via {result.provider}")
        else:
            await safe_reply(message, f"❌ خطا: {result.error}")

    # ─── /email welcome [email] ───
    elif action == "welcome":
        if not args or "@" not in args:
            await safe_reply(message, "👋 فرمت: `/email welcome user@example.com`")
            return

        result = await engine.send_template("welcome", args.strip(), {
            "customer_name": "دوست عزیز",
            "welcome_message": "محصولات ویژه ما رو ببینید!",
        })

        if result.success:
            await safe_reply(message, f"✅ ایمیل خوش‌آمد ارسال شد به `{args.strip()}`")
        else:
            await safe_reply(message, f"❌ خطا: {result.error}")

    # ─── /email winback [email] | [discount%] ───
    elif action == "winback":
        fields = [f.strip() for f in args.split("|")]
        email = fields[0] if fields else ""
        discount = fields[1].replace("%", "") if len(fields) > 1 else "15"

        if not email or "@" not in email:
            await safe_reply(message, "💕 فرمت: `/email winback user@example.com | 15`")
            return

        result = await engine.send_template("win_back", email, {
            "customer_name": "دوست عزیز",
            "discount": discount,
            "discount_code": f"COMEBACK{discount}",
            "expiry_date": "یک هفته آینده",
        })

        if result.success:
            await safe_reply(message, f"✅ ایمیل بازگشت ({discount}% تخفیف) ارسال شد به `{email}`")
        else:
            await safe_reply(message, f"❌ خطا: {result.error}")

    # ─── /email promo [email] | [title] | [message] ───
    elif action == "promo":
        fields = [f.strip() for f in args.split("|")]
        if len(fields) < 2:
            await safe_reply(message, "🔥 فرمت: `/email promo user@email.com | عنوان | پیام`")
            return

        email = fields[0]
        title = fields[1]
        promo_msg = fields[2] if len(fields) > 2 else ""

        result = await engine.send_template("promotion", email, {
            "customer_name": "دوست عزیز",
            "promo_title": title,
            "promo_message": promo_msg,
            "promo_url": "",
            "cta_text": "مشاهده",
            "product_showcase": "",
        })

        if result.success:
            await safe_reply(message, f"✅ ایمیل پروموشن ارسال شد به `{email}`")
        else:
            await safe_reply(message, f"❌ خطا: {result.error}")

    # ─── /email test [email] ───
    elif action == "test":
        email = args.strip()
        if not email or "@" not in email:
            await safe_reply(message, "🧪 فرمت: `/email test your@email.com`")
            return

        result = await engine.send(EmailMessage(
            to=email,
            subject="تست ایمیل مارکتینگ — Arki Engine",
            html_body=(
                "<div style='direction:rtl;font-family:Tahoma;padding:20px;'>"
                "<h2>✅ ایمیل تست</h2>"
                "<p>اگر این ایمیل رو می‌بینی، سیستم ایمیل مارکتینگ درست کار می‌کنه!</p>"
                "</div>"
            ),
        ))

        if result.success:
            await safe_reply(message, f"✅ ایمیل تست ارسال شد به `{email}` via {result.provider}")
        else:
            await safe_reply(message, f"❌ خطا: {result.error}")

    # ─── /email bulk [template] ───
    elif action == "bulk":
        template = args.strip() or "follow_up"
        await safe_reply(message,
            f"📋 ارسال گروهی `{template}` به تمام مشتریان CRM...\n"
            "⏳ این کار ممکنه چند دقیقه طول بکشه.\n"
            "بعد از اتمام نتیجه رو می‌فرستم."
        )

        # Load contacts from CRM
        try:
            from arki_project.database.connection import get_session
            from arki_project.database.models import Customer
            from sqlalchemy import select
            from arki_project.utils.email_engine import EmailContact

            async with get_session() as session:
                result = await session.execute(
                    select(Customer).where(
                        Customer.owner_id == message.from_user.id
                    )
                )
                customers = result.scalars().all()

            contacts = [
                EmailContact(
                    email=c.email, name=c.name,
                    tags=c.tags.split(",") if c.tags else [],
                )
                for c in customers if getattr(c, "email", "")
            ]

            if not contacts:
                await safe_reply(message,
                    "⚠️ هیچ مشتری با ایمیل در CRM نیست.\n"
                    "`/crm add نام | تلفن | ایمیل` برای افزودن"
                )
                return

            results = await engine.send_bulk(template, contacts, {})
            success = sum(1 for r in results if r.success)
            failed = len(results) - success

            await safe_reply(message,
                f"📋 *نتیجه ارسال گروهی:*\n"
                f"✅ موفق: {success}\n"
                f"❌ ناموفق: {failed}\n"
                f"📊 کل: {len(results)}"
            )

        except Exception as exc:
            await safe_reply(message, f"❌ خطا: {exc}")

    else:
        await safe_reply(message,
            "❓ دستور نامعتبر.\n"
            "`/email` رو بدون آرگومان بزن تا راهنما رو ببینی."
        )


