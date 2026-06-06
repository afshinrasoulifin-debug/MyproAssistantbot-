
from __future__ import annotations
"""
from typing import Any, Optional
tg_bot/handlers/automation.py
─────────────────────────────
🤖 Automation Hub — 10 practical automation agents:

  /auto       — automation menu
  /remind     — set timed reminders (asyncio scheduler)
  /qr         — QR code generator
  /short      — URL shortener (is.gd / TinyURL)
  /weather    — weather forecasts (wttr.in)
  /currency   — exchange rates + converter
  /rss        — RSS/news feed reader
  /note       — personal notes/memos (SQLite)
  /caption    — AI social media caption writer
  /hashtag    — AI hashtag generator
  /quote      — random inspirational quote
  /password   — secure password generator
"""


import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import delete, select

from arki_project.config import Settings
from arki_project.database.connection import get_session
from arki_project.database.models import Reminder, UserNote
from arki_project.utils.ai_client import AIClient
from arki_project.utils.automation_tools import (
    convert_currency,
    fetch_rss,
    generate_password,
    generate_qr_code,
    get_popular_rates,
    get_random_quote,
    get_weather,
    shorten_url,
)
from arki_project.utils.models_registry import (
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.handlers.shared import extract_args
from arki_project.utils.v7_core import store_result

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]


logger = logging.getLogger(__name__)
router = Router(name="automation")


# ═══════════════════════════════════════
# /auto — Main Automation Menu
# ═══════════════════════════════════════

def _auto_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="⏰ یادآوری", callback_data="auto:remind"),
            InlineKeyboardButton(text="📱 QR Code", callback_data="auto:qr"),
        ],
        [
            InlineKeyboardButton(text="🔗 کوتاه‌کن URL", callback_data="auto:short"),
            InlineKeyboardButton(text="🌤 آب‌و‌هوا", callback_data="auto:weather"),
        ],
        [
            InlineKeyboardButton(text="💱 نرخ ارز", callback_data="auto:currency"),
            InlineKeyboardButton(text="📰 خبرخوان RSS", callback_data="auto:rss"),
        ],
        [
            InlineKeyboardButton(text="📝 یادداشت", callback_data="auto:note"),
            InlineKeyboardButton(text="✍️ کپشن‌ساز", callback_data="auto:caption"),
        ],
        [
            InlineKeyboardButton(text="#️⃣ هشتگ‌ساز", callback_data="auto:hashtag"),
            InlineKeyboardButton(text="💬 جمله انگیزشی", callback_data="auto:quote"),
        ],
        [
            InlineKeyboardButton(text="🔐 رمزساز", callback_data="auto:password"),
            InlineKeyboardButton(text="🔙 برگشت", callback_data="menu:back"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("auto"))
async def cmd_auto(message: Message) -> None:
    await safe_reply(message, "🤖 *بخش اتوماسیون — ۱۱ ابزار رایگان:*\n\n"
        "⏰ `/remind` — یادآوری زمان‌دار\n"
        "📱 `/qr` — ساخت QR Code\n"
        "🔗 `/short` — کوتاه‌کردن لینک\n"
        "🌤 `/weather` — آب‌و‌هوا\n"
        "💱 `/currency` — نرخ ارز و تبدیل\n"
        "📰 `/rss` — خوان‌دن فید خبری\n"
        "📝 `/note` — یادداشت شخصی\n"
        "✍️ `/caption` — کپشن سوشال مدیا\n"
        "#️⃣ `/hashtag` — هشتگ هوشمند\n"
        "💬 `/quote` — جمله انگیزشی\n"
        "🔐 `/password` — رمز عبور امن\n\n"
        "یکی رو انتخاب کن:",
        reply_markup=_auto_menu_keyboard())


# ── Auto menu callbacks ──

@router.callback_query(F.data.startswith("auto:"))
async def cb_auto_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    action = callback.data.split(":")[1]  # type: ignore[union-attr]

    # ── "back to menu" button ──
    if action == "menu":
        await safe_edit_text(callback.message,  # type: ignore[union-attr]
            "🤖 *بخش اتوماسیون:*\nیکی رو انتخاب کن:",
            reply_markup=_auto_menu_keyboard())
        return

    helps = {
        "remind": "⏰ *یادآوری:*\n\n`/remind 30m چای بذار`\n`/remind 2h جلسه`\n`/remind 1d تولد`\n\nزمان: `Xm` (دقیقه)، `Xh` (ساعت)، `Xd` (روز)",
        "qr": "📱 *QR Code:*\n\n`/qr https://example.com`\n`/qr متن دلخواه`\n`/qr شماره تلفن`",
        "short": "🔗 *کوتاه‌کن:*\n\n`/short https://example.com/long-url`",
        "weather": "🌤 *آب‌و‌هوا:*\n\n`/weather تهران`\n`/weather London`\n`/weather Istanbul`",
        "currency": "💱 *ارز:*\n\n`/currency` — نرخ‌های محبوب\n`/currency 100 USD EUR` — تبدیل\n`/currency 50 EUR TRY`",
        "rss": "📰 *RSS:*\n\n`/rss https://example.com/feed`\n\nفیدهای پیشنهادی:\n`/rss https://rss.nytimes.com/services/xml/rss/nyt/World.xml`",
        "note": "📝 *یادداشت:*\n\n`/note add عنوان | متن` — اضافه\n`/note list` — لیست\n`/note del 1` — حذف",
        "caption": "✍️ *کپشن:*\n\n`/caption شمع دکوری لاکچری`\n`/caption پست اینستا برای تخفیف ویژه`",
        "hashtag": "#️⃣ *هشتگ:*\n\n`/hashtag شمع معطر دست‌ساز`\n`/hashtag candle decoration luxury`",
        "quote": "💬 *جمله انگیزشی:*\n\n`/quote` — یه جمله الهام‌بخش",
        "password": "🔐 *رمزساز:*\n\n`/password` — ۱۶ کاراکتر\n`/password 32` — ۳۲ کاراکتر",
    }
    text = helps.get(action, "")
    if text:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 منوی اتوماسیون", callback_data="auto:menu")],
        ])
        await safe_edit_text(callback.message, # type: ignore[union-attr]
            text, reply_markup=back_kb)


_TIME_RE = re.compile(r"^(\d+)\s*(m|min|minute|h|hour|d|day|s|sec)\s*(.*)$", re.IGNORECASE)

# Global dict to track running reminder tasks per bot instance.
_reminder_tasks: dict[int, asyncio.Task] = {}


@router.message(Command("remind"))
async def cmd_remind(message: Message) -> None:
    raw = extract_args(message.text or "", "/remind")

    # /remind list
    if raw.lower() in ("list", "لیست", ""):
        async with get_session() as session:
            result = await session.execute(
                select(Reminder)
                .where(Reminder.user_id == message.from_user.id, Reminder.sent == False)  # type: ignore[union-attr]
                .order_by(Reminder.remind_at),
            )
            reminders = result.scalars().all()

        if not reminders:
            await safe_reply(message, "⏰ *یادآوری:*\n\nهیچ یادآوری فعالی نداری.\n\n"
                "`/remind 30m چای بذار` — ۳۰ دقیقه بعد\n"
                "`/remind 2h جلسه` — ۲ ساعت بعد\n"
                "`/remind 1d تولد` — فردا")
            return

        text = "⏰ *یادآوری‌های فعال:*\n\n"
        for r in reminders:
            dt = r.remind_at.strftime("%Y-%m-%d %H:%M")
            text += f"  🔔 *{r.id}.* {r.text} — _{dt}_\n"
        text += "\n`/remind del 1` — حذف"
        await safe_reply(message, text)
        return

    # /remind del X
    if raw.lower().startswith(("del ", "حذف ")):
        try:
            rid = int(raw.split()[1])
            async with get_session() as session:
                await session.execute(
                    delete(Reminder).where(
                        Reminder.id == rid,
                        Reminder.user_id == message.from_user.id,  # type: ignore[union-attr]
                    ),
                )
            await message.answer(f"✅ یادآوری {rid} حذف شد.")
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer("❌ شماره نامعتبر")
        return

    # Parse: /remind 30m text
    match = _TIME_RE.match(raw)
    if not match:
        await safe_reply(message, "⏰ *فرمت:* `/remind [زمان] [متن]`\n\n"
            "مثال‌ها:\n"
            "`/remind 30m چای بذار`\n"
            "`/remind 2h جلسه با مشتری`\n"
            "`/remind 1d ارسال سفارش`")
        return

    num = int(match.group(1))
    unit = match.group(2).lower()[0]
    text = match.group(3).strip() or "یادآوری!"

    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    seconds = num * multiplier.get(unit, 60)

    if seconds < 10:
        await message.answer("❌ حداقل ۱۰ ثانیه")
        return
    if seconds > 30 * 86400:
        await message.answer("❌ حداکثر ۳۰ روز")
        return

    remind_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)

    async with get_session() as session:
        reminder = Reminder(
            user_id=message.from_user.id,  # type: ignore[union-attr]
            chat_id=message.chat.id,
            text=text,
            remind_at=remind_at,
        )
        session.add(reminder)
        await session.flush()
        rid = reminder.id

    # Schedule the asyncio task.
    unit_names = {"s": "ثانیه", "m": "دقیقه", "h": "ساعت", "d": "روز"}
    await safe_reply(message, f"✅ یادآوری ثبت شد! (#{rid})\n\n"
        f"🔔 *{text}*\n"
        f"⏰ {num} {unit_names.get(unit, '')} بعد\n"
        f"📅 {remind_at.strftime('%Y-%m-%d %H:%M UTC')}")

    # Fire the async reminder.
    async def _fire_reminder() -> None:
        await asyncio.sleep(seconds)
        try:
            await message.bot.send_message(  # type: ignore[union-attr]
                chat_id=message.chat.id,
                text=f"🔔 *یادآوری!*\n\n{text}",
                parse_mode="Markdown",
            )
            async with get_session() as session:
                result = await session.execute(
                    select(Reminder).where(Reminder.id == rid),
                )
                r = result.scalar_one_or_none()
                if r:
                    r.sent = True
                    await session.flush()
        except Exception as exc:
            logger.error("Reminder %d failed: %s", rid, exc)

    task = asyncio.create_task(_fire_reminder())
    _reminder_tasks[rid] = task


# ═══════════════════════════════════════
# 2. /qr — QR Code Generator
# ═══════════════════════════════════════

@router.message(Command("qr"))
async def cmd_qr(message: Message) -> None:
    data = extract_args(message.text or "", "/qr")
    if not data:
        await safe_reply(message, "📱 *QR Code:*\n\n"
            "`/qr https://example.com`\n"
            "`/qr متن دلخواه`\n"
            "`/qr 09123456789`")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO,
    )

    try:
        img_bytes = generate_qr_code(data)
        photo = BufferedInputFile(img_bytes, filename="qrcode.png")
        await message.answer_photo(
            photo=photo,
            caption=f"📱 *QR Code:*\n`{data[:100]}`",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ {exc}")


# ═══════════════════════════════════════
# 3. /short — URL Shortener
# ═══════════════════════════════════════

@router.message(Command("short"))
async def cmd_short(message: Message) -> None:
    url = extract_args(message.text or "", "/short")
    if not url or not url.startswith("http"):
        await safe_reply(message, "🔗 *کوتاه‌کن:*\n\n`/short https://example.com/long-url`")
        return

    try:
        short = await shorten_url(url)
        await safe_reply(message, f"🔗 *لینک کوتاه:*\n\n{short}\n\n_اصلی:_ `{url[:80]}`")
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ {exc}")


# ═══════════════════════════════════════
# 4. /weather — Weather
# ═══════════════════════════════════════

@router.message(Command("weather"))
async def cmd_weather(message: Message) -> None:
    city = extract_args(message.text or "", "/weather")
    if not city:
        await safe_reply(message, "🌤 *آب‌و‌هوا:*\n\n"
            "`/weather تهران`\n"
            "`/weather Istanbul`\n"
            "`/weather London`")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        text = await get_weather(city)
        await safe_reply(message, text)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ {exc}")


# ═══════════════════════════════════════
# 5. /currency — Exchange Rates
# ═══════════════════════════════════════

@router.message(Command("currency"))
async def cmd_currency(message: Message) -> None:
    raw = extract_args(message.text or "", "/currency")

    if not raw:
        # Show popular rates.
        await message.bot.send_chat_action(  # type: ignore[union-attr]
            chat_id=message.chat.id, action=ChatAction.TYPING,
        )
        try:
            text = await get_popular_rates()
            await safe_reply(message, text)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(f"❌ {exc}")
        return

    # Parse: /currency 100 USD EUR
    parts = raw.split()
    if len(parts) >= 3:
        try:
            amount = float(parts[0].replace(",", ""))
            from_cur = parts[1]
            to_cur = parts[2]
            text = await convert_currency(amount, from_cur, to_cur)
            await safe_reply(message, text)
        except ValueError:
            await safe_reply(message, "❌ فرمت: `/currency 100 USD EUR`")
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(f"❌ {exc}")
    else:
        await safe_reply(message, "💱 *تبدیل ارز:*\n\n"
            "`/currency` — نرخ‌های محبوب\n"
            "`/currency 100 USD EUR` — تبدیل ۱۰۰ دلار به یورو\n"
            "`/currency 50 EUR TRY` — تبدیل ۵۰ یورو به لیر")


# ═══════════════════════════════════════
# 6. /rss — RSS Feed Reader
# ═══════════════════════════════════════

@router.message(Command("rss"))
async def cmd_rss(message: Message) -> None:
    url = extract_args(message.text or "", "/rss")
    if not url:
        await safe_reply(message, "📰 *خبرخوان RSS:*\n\n"
            "`/rss [آدرس فید]`\n\n"
            "مثال‌ها:\n"
            "`/rss https://rss.nytimes.com/services/xml/rss/nyt/World.xml`\n"
            "`/rss https://www.reddit.com/r/technology/.rss`")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )

    try:
        text = await fetch_rss(url, max_items=5)
        for chunk in split_for_telegram(text):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ {exc}")


# ═══════════════════════════════════════
# 7. /note — Personal Notes
# ═══════════════════════════════════════

@router.message(Command("note"))
async def cmd_note(message: Message) -> None:
    raw = extract_args(message.text or "", "/note")
    user_id = message.from_user.id  # type: ignore[union-attr]

    # /note list
    if not raw or raw.lower() in ("list", "لیست"):
        async with get_session() as session:
            result = await session.execute(
                select(UserNote)
                .where(UserNote.user_id == user_id)
                .order_by(UserNote.created_at.desc())
                .limit(20),
            )
            notes = result.scalars().all()

        if not notes:
            await safe_reply(message, "📝 *یادداشت:*\n\nهنوز یادداشتی نداری.\n\n"
                "`/note add عنوان | متن یادداشت`\n"
                "`/note list` — لیست\n"
                "`/note del 1` — حذف")
            return

        text = "📝 *یادداشت‌های تو:*\n\n"
        for n in notes:
            dt = n.created_at.strftime("%m-%d %H:%M") if n.created_at else ""
            preview = n.content[:60].replace("\n", " ")
            text += f"  *{n.id}.* {n.title or '(بدون عنوان)'} — _{preview}_  ({dt})\n"
        text += "\n`/note show 1` — نمایش کامل\n`/note del 1` — حذف"
        await safe_reply(message, text)
        return

    # /note add title | content
    if raw.lower().startswith(("add ", "اضافه ")):
        body = raw.split(maxsplit=1)[1] if " " in raw else ""
        if "|" in body:
            title, content = body.split("|", 1)
        else:
            title, content = "", body
        title = title.strip()
        content = content.strip()
        if not content:
            await safe_reply(message, "❌ `/note add عنوان | متن`")
            return

        async with get_session() as session:
            note = UserNote(user_id=user_id, title=title, content=content)
            session.add(note)
            await session.flush()
            nid = note.id

        await message.answer(f"✅ یادداشت #{nid} ذخیره شد!")
        return

    # /note show X
    if raw.lower().startswith(("show ", "نمایش ")):
        try:
            nid = int(raw.split()[1])
            async with get_session() as session:
                result = await session.execute(
                    select(UserNote).where(
                        UserNote.id == nid, UserNote.user_id == user_id,
                    ),
                )
                note = result.scalar_one_or_none()
            if note:
                await safe_reply(message, f"📝 *{note.title or f'یادداشت #{nid}'}*\n\n{note.content}")
            else:
                await message.answer("❌ یادداشت پیدا نشد")
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer("❌ شماره نامعتبر")
        return

    # /note del X
    if raw.lower().startswith(("del ", "حذف ")):
        try:
            nid = int(raw.split()[1])
            async with get_session() as session:
                await session.execute(
                    delete(UserNote).where(
                        UserNote.id == nid, UserNote.user_id == user_id,
                    ),
                )
            await message.answer(f"✅ یادداشت #{nid} حذف شد.")
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer("❌ شماره نامعتبر")
        return

    await safe_reply(message, "📝 *یادداشت:*\n\n"
        "`/note add عنوان | متن` — اضافه\n"
        "`/note list` — لیست\n"
        "`/note show 1` — نمایش\n"
        "`/note del 1` — حذف")


@router.message(Command("quote"))
async def cmd_quote(message: Message) -> None:
    try:
        text = await get_random_quote()
        await safe_reply(message, text)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ {exc}")


# ═══════════════════════════════════════
# 11. /password — Secure Password
# ═══════════════════════════════════════

@router.message(Command("password"))
async def cmd_password(message: Message) -> None:
    raw = extract_args(message.text or "", "/password")
    length = 16
    if raw.isdigit():
        length = max(8, min(int(raw), 128))
    try:
        text = await generate_password(length)
        await safe_reply(message, text)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ {exc}")


# ═══════════════════════════════════════



async def recover_reminders(bot: Any) -> int:
    """
    Recover unsent reminders after a restart.
    Schedules asyncio tasks for any reminders whose remind_at is in the future.
    Returns count of recovered reminders.
    """
    from datetime import datetime, timezone as tz
    async with get_session() as session:
        result = await session.execute(
            select(Reminder).where(Reminder.sent == False),  # noqa: E712
        )
        reminders = result.scalars().all()

    now = datetime.now(tz.utc)
    recovered = 0
    for r in reminders:
        remind_at = r.remind_at
        if remind_at.tzinfo is None:
            remind_at = remind_at.replace(tzinfo=tz.utc)
        remaining = (remind_at - now).total_seconds()
        if remaining <= 0:
            remaining = 1  # Fire nearly immediately
        rid, chat_id, text = r.id, r.chat_id, r.text

        async def _fire(rid_: Any=rid, chat_id_: Any=chat_id, text_: Any=text, secs: Any=remaining) -> Any:
            await asyncio.sleep(max(secs, 1))
            try:
                await bot.send_message(
                    chat_id=chat_id_,
                    text=f"🔔 *یادآوری!*\n\n{text_}",
                    parse_mode="Markdown",
                )
                async with get_session() as session:
                    result = await session.execute(
                        select(Reminder).where(Reminder.id == rid_),
                    )
                    rem = result.scalar_one_or_none()
                    if rem:
                        rem.sent = True
                        await session.flush()
            except Exception as exc:
                logger.error("Recovered reminder %d failed: %s", rid_, exc)

        task = asyncio.create_task(_fire())
        _reminder_tasks[rid] = task
        recovered += 1
    return recovered


# ═══════════ /autopipeline — WorkflowEngine-powered sales pipeline ═══════════

@router.message(Command("autoworkflow"))
async def cmd_autopipeline(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Auto-generate a multi-step sales/content pipeline using WorkflowEngine."""
    product = extract_args(message.text or "", "/autoworkflow")
    if not product:
        await safe_reply(message, "🔄 *پایپلاین خودکار:*\n\n"
            "`/autopipeline شمع دکوری معطر`\n\n"
            "_یک ورک‌فلو ۵ مرحله‌ای با WorkflowEngine می‌سازم و اجرا می‌کنم:_\n"
            "1️⃣ تحقیق بازار\n2️⃣ توضیح محصول\n3️⃣ کپشن + هشتگ\n"
            "4️⃣ استراتژی قیمت‌گذاری\n5️⃣ برنامه محتوا")
        return

    await message.bot.send_chat_action(
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await safe_reply(message, "🔄 *ساخت ورک‌فلو...*")

    try:
        import time as _t
        _t0 = _t.time()

        from arki_project.utils.workflow_engine import Workflow, NodeType
        wf = Workflow(name=f"autopipeline_{product[:30]}", description=f"Sales pipeline for {product}")

        # Build 5-step workflow
        wf.add_node("research", "Market Research", NodeType.TASK, parameters={"prompt": f"تحقیق بازار و رقبا برای: {product}"})
        wf.add_node("description", "Product Description", NodeType.TASK, parameters={"prompt": f"توضیح محصول حرفه‌ای: {product}"})
        wf.add_node("content", "Content Pack", NodeType.TASK, parameters={"prompt": f"۳ کپشن + ۲۰ هشتگ برای: {product}"})
        wf.add_node("pricing", "Pricing Strategy", NodeType.TASK, parameters={"prompt": f"استراتژی قیمت‌گذاری: {product}"})
        wf.add_node("plan", "Content Plan", NodeType.TASK, parameters={"prompt": f"برنامه محتوایی ۷ روزه: {product}"})

        # Add edges (sequential)
        wf.add_edge("research", "description")
        wf.add_edge("description", "content")
        wf.add_edge("content", "pricing")
        wf.add_edge("pricing", "plan")

        cfg_user = await ai_client.get_user_config(message.from_user.id)
        mk = working_model_key(cfg_user["model"], settings.ai_api_key, settings.groq_api_key)

        # Execute each node via AI
        output = f"🔄 *پایپلاین خودکار: {product}*\n\n"
        step_results = {}

        for i, (node_id, node) in enumerate(wf.nodes.items(), 1):
            try:
                await safe_edit_text(status, f"🔄 *مرحله {i}/5:* {node.name}...")
            except Exception as e:
                logger.debug("Suppressed: %s", e)

            prompt = node.parameters.get("prompt", product)
            # Inject previous results as context
            context = ""
            if step_results:
                context = "\n".join(f"[{k}]: {v[:200]}" for k, v in step_results.items())
                prompt = f"{prompt}\n\nنتایج قبلی:\n{context}"

            try:
                from arki_project.utils.v7_core import enhance_system_prompt
                sys = enhance_system_prompt(
                    "تو متخصص بازاریابی و فروش دیجیتال هستی. به فارسی پاسخ بده.",
                    user_text=prompt,
                    user_id=str(message.from_user.id) if message.from_user else "0",
                )
                result = await ai_client.ask_raw(
                    messages=[{"role": "system", "content": sys}, {"role": "user", "content": prompt}],
                    model_key=mk, temperature=0.7, max_tokens=65536,
                )
                step_results[node_id] = result
                node.status_code = "completed"
                output += f"━━ *مرحله {i}: {node.name}* ━━\n{result}\n\n"
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                node.status_code = "failed"
                output += f"❌ *مرحله {i}: {node.name}* — خطا: {exc}\n\n"

        _duration = _t.time() - _t0
        output += f"\n⏱ *زمان کل:* {_duration:.1f} ثانیه"

        store_result(
            message.from_user.id if message.from_user else 0,
            f"autopipeline:{product[:200]}", output[:500], "autopipeline",
            duration_s=_duration,
        )

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)

        for chunk in split_for_telegram(output):
            try:
                await safe_reply(message, chunk)
            except Exception:
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Autopipeline failed: %s", exc, exc_info=True)
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        await message.answer(user_friendly_error(exc))


# ═══ v9.1: Scheduler UI ═══

@router.message(Command("schedule"))
async def cmd_schedule(message: Message, db_user: Optional[Any]=None, settings: dict=None) -> None:
    """Show scheduled tasks UI."""
    try:
        from arki_project.utils.v7_core import get_autorun_engine
        engine = get_autorun_engine()

        tasks_text = "⏰ *وظایف زمان‌بندی شده*\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        if hasattr(engine, '_tasks') and engine._tasks:
            for name, task in engine._tasks.items():
                status = "🟢" if getattr(task, 'active', True) else "🔴"
                interval = getattr(task, 'interval_hours', '?')
                tasks_text += f"{status} *{name}* — هر {interval} ساعت\n"
        else:
            tasks_text += "هیچ وظیفه‌ای تنظیم نشده.\n"

        tasks_text += "\n💡 برای ایجاد وظیفه جدید: `/schedule add <نام> <ساعت>`"

        await safe_reply(message, tasks_text)
    except Exception as e:
        logger.error("Error in handler: %s", e)
        await safe_reply(message, f"❌ خطا: {e}")


