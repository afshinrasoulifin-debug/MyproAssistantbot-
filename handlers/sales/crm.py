
from __future__ import annotations
from arki_project.exceptions import HandlerError
"""
from typing import Any
tg_bot/handlers/sales/crm.py — CRM Handler v2.0
════════════════════════════════════════════════
Bridges to the real CRM in sales_brain.py + adds lead scoring.
Also provides standalone CRM commands when sales_brain is unavailable.
"""


import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.safe_send import safe_reply
from arki_project.handlers.shared import extract_args

try:
    from arki_project.database.connection import get_session
    from arki_project.database.models import Customer
    from sqlalchemy import select, func
    _DB_AVAILABLE = True
except ImportError:
    _DB_AVAILABLE = False


logger = logging.getLogger(__name__)
router = Router(name="sales_crm_v2")


async def _get_customer_count(uid: int) -> int:
    """Get customer count from DB."""
    if not _DB_AVAILABLE:
        return 0
    try:
        async with get_session() as session:
            result = await session.execute(
                select(func.count()).select_from(Customer).where(Customer.user_id == uid)
            )
            return result.scalar() or 0
    except HandlerError:
        return 0


async def _add_customer_to_db(uid: int, name: str, phone: str = "", email: str = "", tag: str = "") -> bool:
    """Add a customer to the database."""
    if not _DB_AVAILABLE:
        return False
    try:
        async with get_session() as session:
            session.add(Customer(
                user_id=uid,
                name=name,
                phone=phone,
                email=email,
                tag=tag,
                created_at=datetime.now(timezone.utc),
            ))
            await session.commit()
        return True
    except HandlerError as e:
        logger.error("Failed to add customer: %s", e)
        return False


async def _list_customers_from_db(uid: int, limit: int = 20) -> list:
    """Fetch customers from DB."""
    if not _DB_AVAILABLE:
        return []
    try:
        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(Customer.user_id == uid).order_by(Customer.id).limit(limit)
            )
            return list(result.scalars().all())
    except HandlerError as e:
        logger.error("Failed to list customers: %s", e)
        return []


@router.message(Command("crm"))
async def cmd_crm(message: Message, ai_client: AIClient = None, settings: Settings = None, **kwargs) -> None:
    """CRM command — routes to sales_brain or handles directly."""
    # Track lead scoring event
    try:
        from arki_project.utils.lead_scoring_engine import get_lead_scoring_engine
        engine = get_lead_scoring_engine()
        engine.record_event(
            message.from_user.id, "crm_action",
            name=message.from_user.full_name if message.from_user else "",
        )
    except (ImportError, Exception):
        pass

    # Try routing to sales_brain first
    try:
        from arki_project.handlers.sales_brain import cmd_crm as real_crm
        if ai_client and settings:
            await real_crm(message, ai_client, settings)
            return
    except (ImportError, Exception):
        pass

    # Standalone CRM handling
    raw = extract_args(message.text or "", "/crm")
    uid = message.from_user.id
    parts = raw.strip().split(maxsplit=1)

    if not parts:
        count = await _get_customer_count(uid)
        await safe_reply(message,
            f"👥 *CRM — مدیریت مشتری*\n\n"
            f"📊 مشتریان: *{count}*\n\n"
            "*دستورات:*\n"
            "  `/crm add نام | تلفن | ایمیل | تگ`\n"
            "  `/crm list` — لیست مشتریان\n"
            "  `/crm search نام` — جستجو\n"
            "  `/crm vip` — مشتریان VIP\n"
            "  `/crm report` — گزارش"
        )
        return

    action = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if action == "add" and args:
        fields = [f.strip() for f in args.split("|")]
        name = fields[0]
        phone = fields[1] if len(fields) > 1 else ""
        email = fields[2] if len(fields) > 2 else ""
        tag = fields[3] if len(fields) > 3 else ""
        ok = await _add_customer_to_db(uid, name, phone, email, tag)
        if ok:
            await safe_reply(message, f"✅ مشتری *{name}* ثبت شد.")
        else:
            await safe_reply(message, f"📝 مشتری *{name}* — ذخیره موقت (بدون DB)")
        return

    if action == "list":
        customers = await _list_customers_from_db(uid)
        if not customers:
            await safe_reply(message, "📭 مشتری ثبت نشده.")
            return
        lines = []
        for c in customers:
            tag = f" 🏷{c.tag}" if c.tag else ""
            lines.append(f"  {c.id}. *{c.name}*{tag} — {c.phone or '—'}")
        await safe_reply(message, f"👥 *مشتریان:*\n\n" + "\n".join(lines))
        return

    if action == "report":
        count = await _get_customer_count(uid)
        await safe_reply(message, f"📊 *گزارش CRM*\n\nکل مشتریان: *{count}*")
        return

    await safe_reply(message, "⚠️ دستور نامعتبر. `/crm` را ببینید.")


@router.callback_query(F.data.startswith("crm:"))
async def cb_crm(callback: CallbackQuery) -> Any:
    """Handle CRM callbacks."""
    await callback.answer("✅")


