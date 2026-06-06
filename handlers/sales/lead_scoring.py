
from __future__ import annotations
"""
tg_bot/handlers/sales/lead_scoring.py — Lead Scoring Handler v2.0
═══════════════════════════════════════════════════════════════════
Automatic behavioral lead scoring.

Commands:
  /leads                — Dashboard: tier breakdown + top leads
  /leads hot            — Show hot + ready leads
  /leads attention      — Leads needing follow-up
  /leads score [user_id] — Show specific user score
  /leads report         — AI-generated insights
"""


import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from arki_project.utils.safe_send import safe_reply
from typing import Any


logger = logging.getLogger(__name__)
router = Router(name="sales_lead_scoring")


def _extract_args(text: str, command: str) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


@router.message(Command("leads"))
async def cmd_leads(message: Message, **kwargs) -> Any:
    """Lead scoring dashboard."""
    raw = _extract_args(message.text or "", "/leads")

    try:
        from arki_project.utils.lead_scoring_engine import get_lead_scoring_engine, LeadTier
        engine = get_lead_scoring_engine()
    except ImportError:
        await safe_reply(message, "⚠️ `lead_scoring_engine.py` پیدا نشد.")
        return

    if not raw:
        # Dashboard
        summary = engine.get_summary()
        tiers = summary["tiers"]

        text = (
            "🎯 *Lead Scoring Dashboard*\n\n"
            f"📊 کل لیدها: *{summary['total_leads']}*\n"
            f"💰 کل درآمد: *€{summary['total_revenue']:,.2f}*\n"
            f"📈 میانگین امتیاز: *{summary['avg_score']:.1f}*\n"
            f"⚠️ نیاز به پیگیری: *{summary['needs_attention']}*\n\n"
            "━━━━━━━━━━━━━━━\n"
            f"🔵 Cold (0-20): {tiers.get('cold', 0)}\n"
            f"🟡 Warm (21-50): {tiers.get('warm', 0)}\n"
            f"🟠 Hot (51-80): {tiers.get('hot', 0)}\n"
            f"🔴 Ready (81+): {tiers.get('ready', 0)}\n\n"
            "*دستورات:*\n"
            "🔥 `/leads hot` — لیدهای داغ\n"
            "⚠️ `/leads attention` — نیاز به پیگیری\n"
            "🏆 `/leads top` — برترین لیدها\n"
            "👤 `/leads score [user_id]` — امتیاز کاربر\n"
        )

        top_leads = engine.get_top_leads(5)
        if top_leads:
            text += "\n*برترین ۵ لید:*\n"
            for i, lead in enumerate(top_leads, 1):
                emoji = {"cold": "🔵", "warm": "🟡", "hot": "🟠", "ready": "🔴"}.get(lead.tier.value, "⚪")
                text += f"  {i}. {emoji} {lead.name or lead.user_id} — *{lead.score:.0f}* pts"
                if lead.total_spent > 0:
                    text += f" | €{lead.total_spent:.2f}"
                text += "\n"

        await safe_reply(message, text)
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    # ─── /leads hot ───
    if action == "hot":
        hot = engine.get_leads_by_tier(LeadTier.HOT)
        ready = engine.get_leads_by_tier(LeadTier.READY)
        all_hot = ready + hot

        if not all_hot:
            await safe_reply(message, "🔥 هنوز لید داغی نداری. وقتی کاربرها بیشتر فعالیت کنن، اینجا نشون داده می‌شن.")
            return

        text = "🔥 *لیدهای داغ + آماده خرید:*\n\n"
        for lead in all_hot[:15]:
            emoji = "🔴" if lead.tier == LeadTier.READY else "🟠"
            text += (
                f"{emoji} *{lead.name or lead.user_id}*\n"
                f"   امتیاز: {lead.score:.0f} | سفارش: {lead.total_orders}"
                f" | درآمد: €{lead.total_spent:.2f}\n"
                f"   آخرین فعالیت: {lead.days_since_last_active:.0f} روز پیش\n\n"
            )

        await safe_reply(message, text)

    # ─── /leads attention ───
    elif action == "attention":
        needs = engine.get_leads_needing_attention()

        if not needs:
            await safe_reply(message, "✅ همه لیدها اوکی هستن!")
            return

        text = "⚠️ *لیدهای نیازمند پیگیری:*\n\n"
        for lead in needs[:10]:
            reason = ""
            if lead.tier == LeadTier.READY:
                reason = "آماده خرید!"
            elif lead.tier == LeadTier.HOT and lead.days_since_last_active > 3:
                reason = f"داغ ولی {lead.days_since_last_active:.0f} روزه غیرفعال"
            elif lead.tier == LeadTier.WARM and lead.days_since_last_active > 7:
                reason = f"داره سرد می‌شه ({lead.days_since_last_active:.0f} روز غیرفعال)"

            text += f"• *{lead.name or lead.user_id}* — {reason}\n"
            text += f"  امتیاز: {lead.score:.0f} | درآمد: €{lead.total_spent:.2f}\n\n"

        await safe_reply(message, text)

    # ─── /leads top ───
    elif action == "top":
        top = engine.get_top_leads(15)
        if not top:
            await safe_reply(message, "📊 هنوز لیدی ثبت نشده.")
            return

        text = "🏆 *برترین لیدها:*\n\n"
        for i, lead in enumerate(top, 1):
            emoji = {"cold": "🔵", "warm": "🟡", "hot": "🟠", "ready": "🔴"}.get(lead.tier.value, "⚪")
            text += (
                f"{i}. {emoji} *{lead.name or lead.user_id}*\n"
                f"   امتیاز: {lead.score:.0f} | {lead.tier.value}\n"
                f"   سفارش: {lead.total_orders} | درآمد: €{lead.total_spent:.2f}\n\n"
            )

        await safe_reply(message, text)

    # ─── /leads score [user_id] ───
    elif action == "score" and args:
        try:
            uid = int(args)
        except ValueError:
            await safe_reply(message, "❓ user_id باید عدد باشه.")
            return

        profile = engine.get_profile(uid)
        if not profile:
            await safe_reply(message, f"❓ کاربر {uid} پیدا نشد.")
            return

        emoji = {"cold": "🔵", "warm": "🟡", "hot": "🟠", "ready": "🔴"}.get(profile.tier.value, "⚪")
        recent_events = profile.events[-5:] if profile.events else []

        text = (
            f"👤 *پروفایل لید: {profile.name or profile.user_id}*\n\n"
            f"{emoji} Tier: *{profile.tier.value}*\n"
            f"📊 امتیاز: *{profile.score:.0f}*\n"
            f"🛒 سفارش‌ها: {profile.total_orders}\n"
            f"💰 کل خرید: €{profile.total_spent:.2f}\n"
            f"📅 عضویت: {profile.days_since_first_seen:.0f} روز\n"
            f"🕐 آخرین فعالیت: {profile.days_since_last_active:.1f} روز پیش\n"
        )

        if recent_events:
            text += "\n*آخرین رویدادها:*\n"
            for ev in reversed(recent_events):
                text += f"  • {ev['type']}"
                if ev.get('amount'):
                    text += f" (€{ev['amount']})"
                text += "\n"

        await safe_reply(message, text)

    else:
        await safe_reply(message,
            "❓ دستور نامعتبر.\n"
            "`/leads` رو بدون آرگومان بزن."
        )


