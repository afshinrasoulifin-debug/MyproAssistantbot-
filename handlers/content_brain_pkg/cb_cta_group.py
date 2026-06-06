
"""content_brain_pkg.cb_cta_group — sub-module of content_brain"""

from __future__ import annotations
from arki_project.exceptions import CallbackError, HandlerError


import logging

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import *  # auto-fixed

__all__ = ['cb_cta', 'cmd_contentaudit', 'cmd_benchmark', 'cmd_schedule', 'cmd_abtest']

async def cb_cta(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        goals = {
            "buy": "purchase/sales", "comment": "comments/engagement",
            "save": "saves/bookmarks", "share": "shares/viral",
            "follow": "follows/growth", "link": "link clicks/traffic",
            "email": "email signups", "all": "ALL goals combined",
        }
        t = callback.data.split(":")[1]
        await safe_reply(callback.message, f"✍️ محصول/موضوع بنویس:\n`/cta [محصول]`\n_هدف: {goals.get(t, t)}_")

    except HandlerError as exc:
        logger.error("cb_cta error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except CallbackError as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /contentaudit — Content Strategy Audit
# ═══════════════════════════════════════

@router.message(Command("contentaudit"))
async def cmd_contentaudit(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/contentaudit")

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    extra = ""
    if raw:
        extra = f"\nAdditional context from user: {raw}\n"

    body = await _ai(
        message, ai_client, settings,
        system=(
            "You are a senior content marketing auditor. You analyze brand content strategies "
            "and identify gaps, opportunities, and improvements with brutal honesty. "
            "Specialize in artisan/handmade brands. Write in Persian."
        ),
        user=(
            "Perform a COMPLETE CONTENT STRATEGY AUDIT.\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n"
            f"{extra}\n"
            f"Business: {brand_ctx(message.chat.id)}\n"
            "AUDIT SECTIONS:\n\n"
            "📊 *BRAND POSITIONING SCORE* (1-10):\n"
            "- Clarity, differentiation, target audience fit\n\n"
            "📱 *PLATFORM COVERAGE AUDIT:*\n"
            "For each platform (Instagram, TikTok, Pinterest, Etsy, Facebook):\n"
            "- Should you be there? (Yes/No/Later)\n"
            "- Priority level (1-5)\n"
            "- Content fit score\n"
            "- Growth potential\n\n"
            "📝 *CONTENT MIX ANALYSIS:*\n"
            "- Current likely content types\n"
            "- MISSING content types (critical gaps)\n"
            "- Ideal content mix ratio\n\n"
            "🏷 *SEO & DISCOVERY AUDIT:*\n"
            "- Are you targeting right keywords?\n"
            "- Hashtag strategy assessment\n"
            "- Discovery opportunities missed\n\n"
            "💰 *MONETIZATION AUDIT:*\n"
            "- Revenue streams (current vs potential)\n"
            "- Pricing strategy check\n"
            "- Sales funnel gaps\n\n"
            "🎯 *TOP 10 IMPROVEMENTS* ranked by impact:\n"
            "For each: what, why, how, effort level, expected impact\n\n"
            "📅 *90-DAY ACTION PLAN:*\n"
            "Month 1, 2, 3 — specific milestones\n\n"
            "Be brutally honest. This is a professional audit."
        ),
    )

    for chunk in split_for_telegram(f"📋 *آدیت استراتژی محتوا:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except HandlerError as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


# ═══════════════════════════════════════════════
# /benchmark — Competitor Content Benchmark
# ═══════════════════════════════════════════════

@router.message(Command("benchmark"))
async def cmd_benchmark(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = (message.text or "").split(maxsplit=1)
    args = raw[1].strip() if len(raw) > 1 else ""

    if not args:
        await safe_reply(message, "📊 *بنچمارک رقبا — Competitor Benchmark*\n\n"
            "`/benchmark [رقیب یا حوزه]`\n\n"
            "*مثال:*\n"
            "`/benchmark handmade candles Finland`\n"
            "`/benchmark @competitor_instagram`\n"
            "`/benchmark etsy concrete candle shops`\n\n"
            "*تحلیل می‌کنه:*\n"
            "📈 استراتژی محتوای رقبا\n"
            "🎨 سبک بصری و برندینگ\n"
            "⏰ زمان‌بندی انتشار\n"
            "📊 مقایسه با شما\n"
            "💡 فرصت‌های رشد")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("📊 دارم تحلیل بنچمارک رقبا رو انجام می‌دم...")

    try:
        body = await _ai(
            message, ai_client, settings,
            system_prompt=(
                "You are a competitive intelligence analyst specializing in artisan "
                "e-commerce content strategy. You know Instagram, TikTok, Etsy, and "
                "Pinterest algorithms inside-out. Provide data-driven comparisons "
                "and actionable gaps. Write analysis in Persian."
            ),
            user_prompt=(
                "Perform a competitive content benchmark analysis:\n"
                f"Competitor/Niche: {args}\n"
                f"{brand_ctx(message.chat.id)}\n"
                f"{products_ctx(message.chat.id)}\n\n"
                "Analyze and compare:\n\n"
                "═══ 📊 CONTENT STRATEGY COMPARISON ═══\n"
                "- Posting frequency (daily/weekly)\n"
                "- Content mix (% product, lifestyle, educational, UGC)\n"
                "- Platform focus priority\n"
                "- Average caption length & style\n\n"
                "═══ 🎨 VISUAL BENCHMARK ═══\n"
                "- Photography style\n"
                "- Color palette patterns\n"
                "- Video vs Photo ratio\n"
                "- Reel/Story format usage\n\n"
                "═══ 📈 ENGAGEMENT ANALYSIS ═══\n"
                "- Expected engagement rates by content type\n"
                "- Best performing content types in niche\n"
                "- Hashtag strategy comparison\n"
                "- Caption hooks that work\n\n"
                "═══ 💡 GAP ANALYSIS ═══\n"
                "- What competitors do that you don't\n"
                "- What you could do BETTER\n"
                "- Untapped content opportunities\n"
                "- Unique selling points to highlight\n\n"
                "═══ 🎯 ACTION PLAN ═══\n"
                "- 5 immediate content ideas inspired by competitors\n"
                "- 3 differentiation strategies\n"
                "- Weekly content upgrade checklist"
            ),
        )
        await safe_delete(status)
        for chunk in split_for_telegram(f"📊 *بنچمارک رقبا — {args}:*\n\n{body}"):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /schedule — Smart Posting Schedule
# ═══════════════════════════════════════════════

@router.message(Command("contentschedule"))
async def cmd_schedule(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = (message.text or "").split(maxsplit=1)
    args = raw[1].strip() if len(raw) > 1 else ""

    if not args:
        await safe_reply(message, "⏰ *زمان‌بندی هوشمند — Smart Schedule*\n\n"
            "`/schedule [پلتفرم]`\n\n"
            "*مثال:*\n"
            "`/schedule instagram`\n"
            "`/schedule all`\n"
            "`/schedule tiktok | reels`\n\n"
            "*تولید می‌کنه:*\n"
            "⏰ بهترین ساعات انتشار\n"
            "📅 بهترین روزها\n"
            "📊 زمان‌بندی بر اساس نوع محتوا\n"
            "🌍 بهینه برای مخاطب اروپایی/فنلاندی")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("⏰ دارم زمان‌بندی بهینه محاسبه می‌کنم...")

    try:
        body = await _ai(
            message, ai_client, settings,
            system_prompt=(
                "You are a social media timing expert. You know the optimal posting "
                "times for every platform based on audience timezone, content type, "
                "and algorithm behavior. Focus on European (especially Finnish/Nordic) "
                "audiences. Write in Persian with clear schedules."
            ),
            user_prompt=(
                f"Create an optimal posting schedule for: {args}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "Target market: Finland, EU, Nordic countries\n\n"
                "Provide:\n\n"
                "═══ ⏰ OPTIMAL POSTING TIMES ═══\n"
                "For each day of the week:\n"
                "- Best time for Feed posts\n"
                "- Best time for Stories\n"
                "- Best time for Reels/TikTok\n"
                "- Best time for Pinterest pins\n\n"
                "═══ 📊 CONTENT TYPE SCHEDULE ═══\n"
                "| نوع محتوا | بهترین روز | بهترین ساعت | پلتفرم |\n\n"
                "═══ 🌍 TIMEZONE STRATEGY ═══\n"
                "- Finnish audience peak times (EET/EEST)\n"
                "- EU audience peak times\n"
                "- Global/US audience overlap times\n\n"
                "═══ 📅 WEEKLY TEMPLATE ═══\n"
                "Mon-Sun complete schedule:\n"
                "Each day: what to post, when, where, what type\n\n"
                "═══ 🎯 ALGORITHM TIPS ═══\n"
                "- Instagram algorithm timing hacks\n"
                "- TikTok best posting patterns\n"
                "- Pinterest optimal pin frequency\n"
                "- Etsy listing renewal timing"
            ),
        )
        await safe_delete(status)
        for chunk in split_for_telegram(f"⏰ *زمان‌بندی هوشمند — {args}:*\n\n{body}"):
            try:
                await safe_reply(message, chunk)
            except HandlerError as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════
# /abtest — A/B Testing for Content
# ═══════════════════════════════════════

@router.message(Command("abtest"))
async def cmd_abtest(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Generate A/B test variants for captions, CTAs, and content."""
    raw = extract_args(message.text or "", "/abtest")

    if not raw:
        await safe_reply(message, "🔬 *A/B تست محتوا:*\n\n"
            "`/abtest [متن یا کپشن فعلی]`\n\n"
            "*تولید می‌شه:*\n"
            "  ✅ نسخه A (اصلی بهینه‌شده)\n"
            "  ✅ نسخه B (احساسی/داستانی)\n"
            "  ✅ نسخه C (فوریت/FOMO)\n"
            "  ✅ تحلیل مقایسه‌ای\n"
            "  ✅ پیشنهاد تست با معیارها\n\n"
            "*مثال:*\n"
            "`/abtest شمع لاوندر دست‌ساز ما بهترین کیفیت رو داره`\n"
            "`/abtest Buy our handmade candles`")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        bctx = brand_ctx(message.chat.id)
        body = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": (
                    "You are a conversion rate optimization expert. Write in Persian. "
                    "Take the user's original text and create 3 optimized A/B test variants:\n\n"
                    "Version A — Optimized Original: Same messaging, better wording\n"
                    "Version B — Emotional/Story: Storytelling approach\n"
                    "Version C — Urgency/FOMO: Scarcity & fear of missing out\n\n"
                    "For each version provide:\n"
                    "- The full text (ready to post)\n"
                    "- Psychology behind it\n"
                    "- Expected CTR improvement %\n"
                    "- Best use case (feed/story/ad/DM)\n\n"
                    "Then give:\n"
                    "- 📊 Comparison table\n"
                    "- 🏆 Recommended winner with reasoning\n"
                    "- 📋 Testing methodology (sample size, duration, metrics)"
                )},
                {"role": "user", "content": f"Original text: {raw}\n{f'Brand: {bctx}' if bctx else ''}"},
            ],
            model_key=mk, temperature=0.85, max_tokens=8192,
        )

        for chunk in split_for_telegram(f"🔬 *A/B تست — ۳ نسخه بهینه:*\n\n{body}"):
            await safe_reply(message, chunk)
    except HandlerError as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))

