
from __future__ import annotations
"""
tg_bot/handlers/sales/funnel.py — Sales Funnel Handler v2.0
═══════════════════════════════════════════════════════════
Visual funnel + real conversion tracking.

Commands:
  /funnel              — Show current funnel
  /funnel add [stage] [name]  — Add lead to stage
  /funnel move [name] [stage] — Move lead between stages
  /funnel stats        — Conversion rates
"""


import logging
from collections import defaultdict
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from arki_project.utils.safe_send import safe_reply
from typing import Any

logger = logging.getLogger(__name__)
router = Router(name="sales_funnel")

# Funnel stages in order
FUNNEL_STAGES = [
    ("awareness", "👁 آگاهی"),
    ("interest", "💡 علاقه"),
    ("consideration", "🤔 بررسی"),
    ("intent", "🎯 قصد خرید"),
    ("evaluation", "📋 ارزیابی"),
    ("purchase", "🛒 خرید"),
    ("loyalty", "⭐ وفاداری"),
]


def _extract_args(text: str, command: str) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


@router.message(Command("funnel"))
async def cmd_funnel(message: Message, **kwargs) -> Any:
    """Sales funnel visualization + management."""
    raw = _extract_args(message.text or "", "/funnel")

    if not raw:
        # Show funnel with real data from lead scoring
        try:
            from arki_project.utils.lead_scoring_engine import get_lead_scoring_engine, LeadTier
            engine = get_lead_scoring_engine()

            # Map lead tiers to funnel stages
            tier_to_stages = {
                LeadTier.COLD: ["awareness", "interest"],
                LeadTier.WARM: ["consideration", "intent"],
                LeadTier.HOT: ["evaluation"],
                LeadTier.READY: ["purchase"],
            }

            stage_counts = defaultdict(int)
            for tier, stages in tier_to_stages.items():
                leads = engine.get_leads_by_tier(tier)
                per_stage = max(1, len(stages))
                for stage in stages:
                    stage_counts[stage] = len(leads) // per_stage

            # Loyalty = users with 3+ orders
            all_leads = engine.get_top_leads(1000)
            stage_counts["loyalty"] = sum(1 for l in all_leads if l.total_orders >= 3)

        except ImportError:
            stage_counts = defaultdict(int)

        total = max(sum(stage_counts.values()), 1)

        text = "📊 *قیف فروش (Sales Funnel)*\n\n"
        max_bar = 20

        for stage_key, stage_label in FUNNEL_STAGES:
            count = stage_counts.get(stage_key, 0)
            bar_len = max(1, int((count / total) * max_bar)) if count > 0 else 0
            bar = "█" * bar_len + "░" * (max_bar - bar_len)
            text += f"{stage_label}\n`{bar}` {count}\n\n"

        # Conversion rates
        if stage_counts.get("awareness", 0) > 0:
            conv = (stage_counts.get("purchase", 0) / stage_counts["awareness"]) * 100
            text += f"\n📈 *نرخ تبدیل:* {conv:.1f}%"

        text += (
            "\n\n━━━━━━━━━━━━━━━\n"
            "*دستورات:*\n"
            "`/funnel stats` — آمار تبدیل\n"
            "\n💡 _قیف از امتیازدهی خودکار لیدها پر می‌شه._"
        )

        await safe_reply(message, text)
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()

    # ─── /funnel stats ───
    if action == "stats":
        try:
            from arki_project.utils.lead_scoring_engine import get_lead_scoring_engine, LeadTier
            engine = get_lead_scoring_engine()
            summary = engine.get_summary()

            tiers = summary["tiers"]
            total = summary["total_leads"] or 1

            cold_pct = (tiers.get("cold", 0) / total) * 100
            warm_pct = (tiers.get("warm", 0) / total) * 100
            hot_pct = (tiers.get("hot", 0) / total) * 100
            ready_pct = (tiers.get("ready", 0) / total) * 100

            text = (
                "📊 *آمار قیف فروش*\n\n"
                f"کل لیدها: *{summary['total_leads']}*\n\n"
                f"🔵 Cold → Warm: *{warm_pct + hot_pct + ready_pct:.1f}%*\n"
                f"🟡 Warm → Hot: *{hot_pct + ready_pct:.1f}%*\n"
                f"🟠 Hot → Ready: *{ready_pct:.1f}%*\n\n"
                f"💰 کل درآمد: *€{summary['total_revenue']:,.2f}*\n"
                f"📈 میانگین امتیاز: *{summary['avg_score']:.1f}*"
            )

        except ImportError:
            text = "⚠️ `lead_scoring_engine.py` پیدا نشد."

        await safe_reply(message, text)

    else:
        await safe_reply(message,
            "❓ دستور نامعتبر.\n"
            "`/funnel` رو بدون آرگومان بزن."
        )


