
from __future__ import annotations
"""
tg_bot/handlers/sales/seo.py — Real SEO Handler v2.0
═════════════════════════════════════════════════════
Uses seo_engine for actual web data — not just AI text.

Commands:
  /seo [keyword]          — Full SEO analysis
  /seo keywords [query]   — Keyword research
  /seo hashtags [topic]   — Hashtag generation
  /seo score [title] | [description] | [tags]  — SEO score
  /seo etsy [query]       — Etsy competitor analysis
"""


import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from arki_project.utils.safe_send import safe_reply
from arki_project.utils.models_registry import split_for_telegram
from typing import Any


logger = logging.getLogger(__name__)
router = Router(name="sales_seo")


def _extract_args(text: str, command: str) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


@router.message(Command("seo"))
async def cmd_seo(message: Message, **kwargs) -> Any:
    """SEO analysis with real data."""
    raw = _extract_args(message.text or "", "/seo")

    if not raw:
        await safe_reply(message,
            "🔍 *SEO Engine*\n\n"
            "*دستورات:*\n"
            "📊 `/seo [keyword]` — تحلیل کامل\n"
            "🔑 `/seo keywords [query]` — تحقیق کلمات کلیدی\n"
            "# `/seo hashtags [topic]` — تولید هشتگ\n"
            "📈 `/seo score عنوان | توضیحات | تگ۱,تگ۲`\n"
            "🏪 `/seo etsy [query]` — تحلیل رقبا در Etsy"
        )
        return

    try:
        from arki_project.utils.seo_engine import get_seo_engine
        engine = get_seo_engine()
    except ImportError:
        await safe_reply(message, "⚠️ `seo_engine.py` پیدا نشد.")
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()
    args = parts[1].strip() if len(parts) > 1 else ""

    # ─── /seo keywords [query] ───
    if action == "keywords" and args:
        await safe_reply(message, "⏳ تحقیق کلمات کلیدی...")
        lang = "fa" if any('\u0600' <= c <= '\u06FF' for c in args) else "en"
        keywords = await engine.get_keywords(args, lang)

        text = f"🔑 *کلمات کلیدی: {args}*\n\n"
        for i, kw in enumerate(keywords[:10], 1):
            text += f"*{i}.* `{kw.keyword}`\n"
            text += f"   رقابت: {kw.competition} | امتیاز: {kw.score}\n"
            if kw.long_tails:
                text += f"   لانگ‌تیل: {', '.join(kw.long_tails[:3])}\n"
            text += "\n"

        for chunk in split_for_telegram(text):
            await safe_reply(message, chunk)

    # ─── /seo hashtags [topic] ───
    elif action == "hashtags" and args:
        await safe_reply(message, "⏳ تولید هشتگ...")
        lang = "fa" if any('\u0600' <= c <= '\u06FF' for c in args) else "en"
        hashtags = await engine.generate_hashtags(args, 30, lang)

        text = f"# *هشتگ‌های پیشنهادی: {args}*\n\n"
        text += " ".join(hashtags[:30])
        text += f"\n\n📊 تعداد: {len(hashtags)}"

        await safe_reply(message, text)

    # ─── /seo score [title] | [desc] | [tags] ───
    elif action == "score":
        fields = [f.strip() for f in args.split("|")] if args else []
        if len(fields) < 2:
            await safe_reply(message,
                "📈 فرمت:\n"
                "`/seo score عنوان محصول | توضیحات کامل | تگ۱,تگ۲,تگ۳`"
            )
            return

        title = fields[0]
        desc = fields[1]
        tags = [t.strip() for t in fields[2].split(",")] if len(fields) > 2 else []

        result = engine.calculate_seo_score(title, desc, tags)
        grade_emoji = {"A": "🟢", "B": "🟡", "C": "🟠", "D": "🔴"}.get(result["grade"], "⚪")

        text = (
            f"📈 *SEO Score*\n\n"
            f"{grade_emoji} نمره: *{result['score']}/100* (گرید {result['grade']})\n\n"
        )

        if result["issues"]:
            text += "*مشکلات:*\n"
            for issue in result["issues"]:
                text += f"  ❌ {issue}\n"

        if result["tips"]:
            text += "\n*پیشنهادات:*\n"
            for tip in result["tips"]:
                text += f"  💡 {tip}\n"

        await safe_reply(message, text)

    # ─── /seo etsy [query] ───
    elif action == "etsy" and args:
        await safe_reply(message, "⏳ تحلیل رقبا در Etsy...")
        competitors = await engine.analyze_etsy(args)

        if not competitors:
            await safe_reply(message, "⚠️ نتیجه‌ای پیدا نشد. ممکنه Etsy بلاک کرده باشه.")
            return

        text = f"🏪 *رقبای Etsy: {args}*\n\n"
        for i, c in enumerate(competitors[:10], 1):
            text += f"*{i}.* {c.title[:60]}\n"
            if c.price:
                text += f"   💰 €{c.price:.2f}\n"
            if c.url:
                text += f"   🔗 {c.url}\n"
            text += "\n"

        prices = [c.price for c in competitors if c.price > 0]
        if prices:
            avg = sum(prices) / len(prices)
            text += f"\n📊 *میانگین قیمت:* €{avg:.2f}\n"
            text += f"📊 *بازه قیمت:* €{min(prices):.2f} — €{max(prices):.2f}"

        for chunk in split_for_telegram(text):
            await safe_reply(message, chunk)

    # ─── /seo [query] — Full analysis ───
    else:
        query = raw
        await safe_reply(message, f"⏳ تحلیل SEO کامل: `{query}`...")
        lang = "fa" if any('\u0600' <= c <= '\u06FF' for c in query) else "en"
        report = await engine.full_analysis(query, lang)

        text = f"🔍 *تحلیل SEO: {query}*\n\n"
        text += f"📊 امتیاز کلی: *{report.score}/100*\n\n"

        if report.keywords:
            text += "*کلمات کلیدی:*\n"
            for kw in report.keywords[:5]:
                text += f"  • `{kw.keyword}` ({kw.competition})\n"

        if report.hashtags:
            text += f"\n*هشتگ‌ها ({len(report.hashtags)}):*\n"
            text += " ".join(report.hashtags[:15]) + "\n"

        if report.competitors:
            text += f"\n*رقبا ({len(report.competitors)}):*\n"
            for c in report.competitors[:3]:
                text += f"  • {c.title[:50]}"
                if c.price:
                    text += f" — €{c.price:.2f}"
                text += "\n"

        if report.suggestions:
            text += "\n*پیشنهادات:*\n"
            for s in report.suggestions:
                text += f"  💡 {s}\n"

        for chunk in split_for_telegram(text):
            await safe_reply(message, chunk)


