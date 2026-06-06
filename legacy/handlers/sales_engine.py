
from __future__ import annotations
"""
tg_bot/handlers/sales_engine.py
────────────────────────────────
🚀 Sales & Marketing Engine — Revolutionary automation for growing a business.

Commands:
  /funnel     — Build complete sales funnel (awareness → purchase)
  /persona    — AI customer persona generator
  /repurpose  — Turn 1 content into 10+ formats
  /launch     — Product launch campaign (pre/during/post)
  /seasonal   — Holiday & seasonal campaign planner
  /seo        — Deep SEO keyword research (Etsy + Google)
  /email      — Email marketing templates
  /pricing    — Smart pricing strategy & analysis
  /viral      — Viral content formula generator
  /collab     — Influencer outreach & collaboration templates
  /ads        — Ad copy generator (Instagram/Facebook/Pinterest)
  /social     — Social proof system (reviews, UGC, testimonials)
  /swipe      — Swipefile: ready-to-use caption/bio/CTA library
  /competitor  — Deep competitor SWOT analysis
"""


import logging

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════

try:
    from arki_project.utils.titanium.compat import secure_random as random  # v10: CSPRNG
except ImportError:
    import random
import urllib.parse

import httpx
from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    Message,
)

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.handlers.shared import extract_args, brand_ctx, products_ctx
from arki_project.utils.data_store import store
from arki_project.utils.v7_core import (
    enhance_system_prompt, store_result,
)

logger = logging.getLogger(__name__)
# v9.2: Task queue for heavy operations

# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]


# v9.1: Marketing engine integration
try:
    from arki_project.utils.v7_core import get_marketing_engine
    _marketing = get_marketing_engine()
except Exception as exc:
    logger.error("Error in handler: %s", exc)
    _marketing = None
router = Router(name="sales_engine")


# ── Shared helper ──


async def _ai_generate(
    message: Message, ai_client: AIClient, settings: Settings,
    system_prompt: str, user_prompt: str, temp: float = 0.85,
    max_tokens: int = 4096,
) -> str:
    """Shared AI generation with auto model selection + auto context injection."""
    cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
    mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

    # Auto-inject brand, product, and sales context into system prompt
    chat_id = message.chat.id
    ctx_parts = [system_prompt]
    b = brand_ctx(chat_id)
    if b:
        ctx_parts.append(f"\n\n--- BRAND CONTEXT ---\n{b}")
    p = products_ctx(chat_id)
    if p:
        ctx_parts.append(f"\n\n--- PRODUCT CATALOG ---\n{p}")
    sales = store.get_sales(chat_id)
    if sales:
        top_sales = sales[:10]
        sales_txt = "\n".join(f"- {s.get('name','?')}: {s.get('qty',0)}x €{s.get('revenue',0)}" for s in top_sales)
        ctx_parts.append(f"\n\n--- RECENT SALES ---\n{sales_txt}")

    enriched_system = "\n".join(ctx_parts)

    # v8: Enhance system prompt with RAG
    enriched_system = enhance_system_prompt(enriched_system, user_text=user_prompt, user_id=str(message.from_user.id) if message.from_user else "0")
    import time as _t
    _t0 = _t.time()
    _result = await ai_client.ask_raw(
        messages=[
            {"role": "system", "content": enriched_system},
            {"role": "user", "content": user_prompt},
        ],
        model_key=mk, temperature=temp, max_tokens=max_tokens,
    )
    # v8: Store + telemetry with real timing
    store_result(message.from_user.id if message.from_user else 0, user_prompt[:300], _result[:500] if _result else "", "sales_engine", duration_s=_t.time()-_t0)
    return _result


async def _send_result(message: Message, header: str, body: str) -> None:
    """Send long AI response in chunks."""
    for chunk in split_for_telegram(f"{header}\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


# Brand context helper


# ═══════════════════════════════════════════════
# /funnel — Complete Sales Funnel Builder
# ═══════════════════════════════════════════════

@router.message(Command("funnel"))
async def cmd_funnel(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/funnel")

    if not raw:
        await safe_reply(message, "🎯 *سیستم فانل فروش — Sales Funnel:*\n\n"
            "`/funnel [محصول] | [هدف فروش]`\n\n"
            "*مثال:*\n"
            "`/funnel concrete candle | 50 sales/month`\n"
            "`/funnel handmade candle collection | grow brand`\n\n"
            "*تولید می‌کنه:*\n"
            "📢 مرحله ۱: آگاهی (Awareness)\n"
            "💭 مرحله ۲: علاقه (Interest)\n"
            "❤️ مرحله ۳: تمایل (Desire)\n"
            "🛒 مرحله ۴: اقدام (Action)\n"
            "🔁 مرحله ۵: وفاداری (Loyalty)\n\n"
            "_برای هر مرحله: محتوا + پلتفرم + CTA + نمونه_")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    goal = parts[1] if len(parts) > 1 else "grow sales"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("🎯 دارم فانل فروش کامل طراحی می‌کنم...")

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a world-class digital marketing strategist and sales funnel expert "
                "who has built 7-figure funnels for artisan and DTC brands across Etsy, Shopify, "
                "and social commerce. You specialize in handmade/artisan e-commerce brands in "
                "the Nordic and European markets. You create actionable, step-by-step sales funnels "
                "with specific content, exact copy, and measurable KPIs for each stage. "
                "Write explanations in Persian. Marketing materials in English + Finnish (Suomi). "
                "Be brutally practical — no fluff, only tactics that work for small makers."
            ),
            user_prompt=(
                "Create a COMPLETE 5-stage sales funnel for:\n"
                f"Product: {product}\n"
                f"Goal: {goal}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "Platforms: Instagram, Etsy, Tori.fi, Pinterest, TikTok\n\n"
                "For EACH stage, provide:\n\n"
                "═══ STAGE 1: AWARENESS (آگاهی) 📢 ═══\n"
                "- Goal: Make people discover you\n"
                "- 3 specific content ideas with full descriptions\n"
                "- Best platforms for this stage\n"
                "- Hashtag strategy\n"
                "- Budget: €0 (organic) strategy\n"
                "- KPIs to track\n"
                "- Ready-to-use caption example (EN + FI)\n\n"
                "═══ STAGE 2: INTEREST (علاقه) 💭 ═══\n"
                "- Goal: Make them follow & engage\n"
                "- 3 content ideas (educational, behind-scenes, process)\n"
                "- Story/Reel script ideas\n"
                "- Lead magnet idea\n"
                "- Caption example (EN + FI)\n\n"
                "═══ STAGE 3: DESIRE (تمایل) ❤️ ═══\n"
                "- Goal: Make them WANT your product\n"
                "- 3 content ideas (lifestyle, social proof, urgency)\n"
                "- Emotional triggers to use\n"
                "- Product styling/photo ideas\n"
                "- Caption example (EN + FI)\n\n"
                "═══ STAGE 4: ACTION (اقدام) 🛒 ═══\n"
                "- Goal: Convert to sale\n"
                "- 3 conversion tactics\n"
                "- CTA scripts (link in bio, DM to order, Etsy link)\n"
                "- Urgency/scarcity techniques\n"
                "- Checkout optimization tips\n"
                "- Caption example (EN + FI)\n\n"
                "═══ STAGE 5: LOYALTY (وفاداری) 🔁 ═══\n"
                "- Goal: Repeat purchase + referral\n"
                "- Follow-up message templates\n"
                "- Unboxing experience ideas\n"
                "- Referral program concept\n"
                "- Re-engagement content\n\n"
                "═══ WEEKLY FUNNEL ACTION PLAN ═══\n"
                "Mon-Sun: which stage to focus on, what to post, where\n\n"
                "Make everything ACTIONABLE and SPECIFIC to handmade candles."
            ),
        )
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        await _send_result(message, f"🎯 *فانل فروش — {product}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /persona — AI Customer Persona Generator
# ═══════════════════════════════════════════════

@router.message(Command("buyer"))
async def cmd_buyer(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/buyer")

    if not raw:
        await safe_reply(message, "👤 *پرسونای مشتری — Buyer Persona:*\n\n"
            "`/buyer [محصول یا نیچ]`\n\n"
            "*مثال:*\n"
            "`/buyer handmade concrete candles`\n"
            "`/buyer luxury home decor Finland`\n\n"
            "_۳ پرسونای دقیق مشتری ایده‌آل + نحوه هدف‌گیری_")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a consumer psychology expert and market researcher. "
                "You create detailed, data-driven customer personas for artisan brands. "
                "Write in Persian with English marketing terms."
            ),
            user_prompt=(
                f"Create 3 detailed BUYER PERSONAS for: {raw}\n"
                f"Market: Finland + international (Etsy){brand_ctx(message.chat.id)}\n\n"
                "For EACH persona:\n\n"
                "👤 *PERSONA [A/B/C]: [Name]*\n"
                "📊 Demographics: Age, Gender, Location, Income, Job\n"
                "🧠 Psychographics: Values, Lifestyle, Interests\n"
                "💰 Spending: Budget range, purchase frequency\n"
                "📱 Digital: Platforms they use, content they consume\n"
                "❤️ Motivations: Why they buy handmade/artisan\n"
                "😰 Pain points: What problems they have\n"
                "🎯 How to reach them: Specific channels & tactics\n"
                "✍️ Message that resonates: Example caption/ad that would work\n"
                "🛍 Where they shop: Etsy, Instagram, markets, boutiques?\n"
                "🔑 Keywords they search: Exact search terms they use\n\n"
                "Then provide:\n"
                "🏆 *PRIMARY TARGET:* Which persona to focus on first and why\n"
                "📝 *CONTENT STRATEGY per persona:* What to post for each\n"
                "💡 *INSIGHT:* Non-obvious finding about these customers"
            ),
        )
        await _send_result(message, f"👤 *پرسوناهای مشتری — {raw}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /repurpose — Content Multiplier (1 → 10+)
# ═══════════════════════════════════════════════

@router.message(Command("repurpose"))
async def cmd_repurpose(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/repurpose")

    if not raw:
        await safe_reply(message, "♻️ *تکثیر محتوا — ۱ محتوا = ۱۲ فرمت:*\n\n"
            "`/repurpose [یک محتوا، ایده، یا محصول]`\n\n"
            "*مثال:*\n"
            "`/repurpose We hand-pour each candle in our Helsinki workshop`\n"
            "`/repurpose concrete candle making process`\n\n"
            "*از ۱ ایده می‌سازه:*\n"
            "📸 پست اینستاگرام\n"
            "🎬 اسکریپت ریلز\n"
            "📱 ۵ استوری\n"
            "🐦 توییت/ترد\n"
            "📌 پین Pinterest\n"
            "🎵 TikTok script\n"
            "📧 ایمیل\n"
            "📋 آگهی Etsy\n"
            "📝 بلاگ پست\n"
            "💬 کپشن تبلیغاتی\n"
            "🇫🇮 همه به فنلاندی هم!\n"
            "🏷 هشتگ هر پلتفرم")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("♻️ دارم ۱ محتوا رو به ۱۲ فرمت تبدیل می‌کنم...")

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a content repurposing genius. You take ONE piece of content "
                "and transform it into 12 different formats for maximum reach. "
                "Each format is fully written, ready to copy-paste. "
                "You write in English and Finnish."
            ),
            user_prompt=(
                "Take this ONE content/idea and create 12 different content pieces:\n\n"
                f"Original: {raw}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "Create ALL 12 formats below (each FULLY WRITTEN, ready to post):\n\n"
                "📸 *1. INSTAGRAM POST:* Full caption EN + 30 hashtags\n"
                "📸 *2. INSTAGRAM POST (FI):* Same in Finnish + Finnish hashtags\n"
                "🎬 *3. REELS SCRIPT:* 30-sec script, scene-by-scene\n"
                "📱 *4. STORY SEQUENCE:* 5 slides with text overlays\n"
                "📌 *5. PINTEREST PIN:* Title + description + keywords\n"
                "🎵 *6. TIKTOK SCRIPT:* Hook + content + CTA\n"
                "📧 *7. EMAIL:* Subject + body for email list\n"
                "📋 *8. ETSY LISTING UPDATE:* How to incorporate into listing\n"
                "🇫🇮 *9. TORI.FI POST:* Finnish marketplace version\n"
                "📝 *10. BLOG SNIPPET:* 200-word blog section\n"
                "💬 *11. AD COPY:* Instagram/Facebook ad version\n"
                "🗣 *12. STORY TALKING POINTS:* What to SAY on camera\n\n"
                "Make each version UNIQUE and optimized for its platform.\n"
                "Include platform-specific best practices."
            ),
        )
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        await _send_result(message, "♻️ *۱۲ فرمت محتوا:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /launch — Product Launch Campaign
# ═══════════════════════════════════════════════

@router.message(Command("launch"))
async def cmd_launch(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/launch")

    if not raw:
        await safe_reply(message, "🚀 *کمپین لانچ محصول — Product Launch:*\n\n"
            "`/launch [محصول جدید] | [تاریخ لانچ]`\n\n"
            "*مثال:*\n"
            "`/launch New Nordic Collection | June 1`\n"
            "`/launch Limited Edition Summer Candle | next week`\n\n"
            "*تولید می‌کنه:*\n"
            "📅 تقویم ۱۴ روزه (قبل/حین/بعد لانچ)\n"
            "📢 تیزرها و شمارش معکوس\n"
            "🎬 محتوای هر روز\n"
            "📧 ایمیل لانچ\n"
            "📋 آگهی‌های آماده\n"
            "🎯 استراتژی قیمت لانچ")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    date = parts[1] if len(parts) > 1 else "soon"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("🚀 دارم کمپین لانچ کامل طراحی می‌کنم...")

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a product launch strategist for artisan brands. "
                "You create buzz-building, sales-driving launch campaigns. "
                "Write in Persian with English marketing terms and full content examples."
            ),
            user_prompt=(
                "Create a COMPLETE 14-day product launch campaign:\n"
                f"Product: {product}\n"
                f"Launch date: {date}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "Platforms: Instagram, Etsy, Tori.fi, Email\n\n"
                "═══ PHASE 1: TEASER (Day -7 to -4) ═══\n"
                "Daily content plan with full captions EN+FI\n"
                "Mystery/teaser posts, behind-the-scenes\n"
                "Story countdown ideas\n\n"
                "═══ PHASE 2: BUILD-UP (Day -3 to -1) ═══\n"
                "Reveal details gradually\n"
                "Early-bird / waitlist strategy\n"
                "Influencer seeding plan\n"
                "Full captions + hashtags\n\n"
                "═══ PHASE 3: LAUNCH DAY (Day 0) ═══\n"
                "Hour-by-hour posting schedule\n"
                "Launch announcement (EN + FI)\n"
                "Etsy listing (optimized)\n"
                "Tori.fi listing\n"
                "Instagram post + stories + reel\n"
                "Email blast template\n"
                "Launch-day offer\n\n"
                "═══ PHASE 4: MOMENTUM (Day 1-7) ═══\n"
                "Social proof collection\n"
                "Customer spotlight plan\n"
                "Retargeting content\n"
                "Reviews push strategy\n"
                "Daily content with captions\n\n"
                "═══ PRICING STRATEGY ═══\n"
                "Early-bird vs regular pricing\n"
                "Bundle offers\n"
                "Free shipping threshold\n\n"
                "═══ LAUNCH CHECKLIST ═══\n"
                "Pre-launch: everything to prepare\n"
                "Launch day: step-by-step\n"
                "Post-launch: follow-up actions"
            ),
        )
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        await _send_result(message, f"🚀 *کمپین لانچ — {product}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /seasonal — Holiday & Seasonal Campaign
# ═══════════════════════════════════════════════

@router.message(Command("seasonal"))
async def cmd_seasonal(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/seasonal")

    if not raw:
        await safe_reply(message, "🎄 *کمپین فصلی و مناسبتی:*\n\n"
            "`/seasonal [مناسبت یا فصل]`\n\n"
            "*مثال‌ها:*\n"
            "`/seasonal christmas`\n"
            "`/seasonal valentine`\n"
            "`/seasonal summer`\n"
            "`/seasonal black friday`\n"
            "`/seasonal mother's day`\n"
            "`/seasonal finnish independence day`\n"
            "`/seasonal autumn cozy season`\n\n"
            "_شمع = محصول فصلی عالی! کمپین‌های مناسبتی فروش رو ۳-۵ برابر می‌کنن._")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer(f"🎄 دارم کمپین «{raw}» طراحی می‌کنم...")

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a seasonal marketing expert for handmade/artisan brands. "
                "You know Finnish holidays, international events, and seasonal buying patterns. "
                "Candles are PERFECT seasonal products. Create irresistible campaigns. "
                "Write in Persian with English content examples."
            ),
            user_prompt=(
                f"Create a COMPLETE seasonal campaign for: {raw}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "Provide:\n\n"
                "🎯 *CAMPAIGN OVERVIEW:*\n"
                "- Theme & mood\n"
                "- Duration (start → end)\n"
                "- Goals & KPIs\n\n"
                "🎨 *SPECIAL PRODUCTS/OFFERS:*\n"
                "- Limited edition product ideas\n"
                "- Special packaging concepts\n"
                "- Pricing (regular vs seasonal)\n"
                "- Bundle ideas\n\n"
                "📅 *CONTENT CALENDAR (2 weeks):*\n"
                "Day-by-day: platform, content type, full caption EN+FI, hashtags\n\n"
                "🖼 *VISUAL DIRECTION:*\n"
                "- Photography style for this season\n"
                "- Color palette\n"
                "- Props & styling\n"
                "- 5 specific photo shot ideas\n\n"
                "📧 *EMAIL SEQUENCE:*\n"
                "- Announcement email\n"
                "- Reminder email\n"
                "- Last-chance email\n\n"
                "📋 *ETSY SEASONAL SEO:*\n"
                "- Seasonal tags to add\n"
                "- Title optimization\n"
                "- Description additions\n\n"
                "🎁 *PROMOTION IDEAS:*\n"
                "- Giveaway concept\n"
                "- Gift guide inclusion strategy\n"
                "- Cross-promotion ideas\n"
                "- Gift wrapping/packaging upsell"
            ),
        )
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        await _send_result(message, f"🎄 *کمپین فصلی — {raw}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /seo — Deep SEO Keyword Research
# ═══════════════════════════════════════════════

@router.message(Command("seo"))
async def cmd_seo(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/seo")

    if not raw:
        await safe_reply(message, "🔎 *تحقیق سئو عمیق — Etsy + Google:*\n\n"
            "`/seo [محصول یا نیچ]`\n\n"
            "*مثال:*\n"
            "`/seo concrete candle holder`\n"
            "`/seo handmade soy candle Finland`\n\n"
            "*تولید می‌کنه:*\n"
            "🔑 ۵۰+ کلمه کلیدی\n"
            "📊 دسته‌بندی: High/Medium/Low competition\n"
            "🏷 ۱۳ تگ بهینه Etsy\n"
            "📝 عنوان SEO\n"
            "🌐 Google Shopping keywords\n"
            "📌 Pinterest SEO keywords")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("🔎 دارم تحقیق سئو عمیق انجام می‌دم...")

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are the world's best Etsy SEO expert and e-commerce keyword researcher. "
                "You know Etsy's 2024/2025 search algorithm in depth: query matching, listing quality "
                "score, recency boost, conversion rate ranking, and the exact tag/title optimization "
                "that drives visibility. You also master Google Shopping structured data, "
                "Pinterest visual search SEO, and Instagram Explore/Search algorithm. "
                "Your recommendations are based on actual marketplace data patterns. "
                "Write analysis in Persian. Keywords and listings in English + Finnish."
            ),
            user_prompt=(
                f"Do DEEP keyword research for: {raw}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "═══ SECTION 1: ETSY KEYWORD RESEARCH ═══\n"
                "🔥 *HIGH VOLUME keywords* (what most buyers search): 15 keywords\n"
                "📈 *MEDIUM keywords* (good balance): 15 keywords\n"
                "🎯 *LONG-TAIL keywords* (specific, easy to rank): 20 keywords\n"
                "🇫🇮 *FINNISH keywords* (for Finnish buyers on Etsy): 10 keywords\n\n"
                "For each keyword, estimate: [competition: Low/Med/High] [relevance: ⭐⭐⭐]\n\n"
                "═══ SECTION 2: OPTIMIZED ETSY LISTING ═══\n"
                "📝 *Perfect Title* (140 chars, front-loaded keywords)\n"
                "🏷 *13 Tags* (each max 20 chars, covering different search intents)\n"
                "📄 *First paragraph* of description (most important for SEO)\n"
                "📂 *Category path* recommendation\n"
                "🏗 *Attributes* to fill out\n\n"
                "═══ SECTION 3: GOOGLE SHOPPING ═══\n"
                "Keywords that work for Google Shopping integration\n\n"
                "═══ SECTION 4: PINTEREST SEO ═══\n"
                "Pin title + description optimized for Pinterest search\n"
                "Board names suggestions\n\n"
                "═══ SECTION 5: INSTAGRAM SEARCHABILITY ═══\n"
                "Name & bio optimization for Instagram search\n"
                "Alt-text strategy for posts\n\n"
                "═══ SECTION 6: STRATEGY ═══\n"
                "🏆 *TOP 5 keywords to target FIRST*\n"
                "📈 *Keyword gap:* What competitors miss\n"
                "🔄 *A/B testing plan:* How to test different titles/tags\n"
                "📊 *Tracking:* How to measure what's working"
            ),
            temp=0.7,
        )
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        await _send_result(message, f"🔎 *تحقیق سئو — {raw}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /email — Email Marketing Templates
# ═══════════════════════════════════════════════

@router.message(Command("email"))
async def cmd_email(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/email")

    types_help = (
        "*نوع‌ها:*\n"
        "👋 `welcome` — خوش‌آمد مشتری جدید\n"
        "🛒 `abandoned` — سبد رهاشده\n"
        "📦 `shipping` — ارسال شد\n"
        "⭐ `review` — درخواست نظر\n"
        "🔥 `promo` — تخفیف/پیشنهاد ویژه\n"
        "🆕 `newproduct` — محصول جدید\n"
        "💌 `newsletter` — خبرنامه ماهانه\n"
        "🎁 `loyalty` — تشکر از مشتری وفادار\n"
        "📋 `all` — *همه ۸ قالب!*"
    )

    if not raw:
        await safe_reply(message, "📧 *ایمیل مارکتینگ:*\n\n"
            "`/email [نوع] | [محصول]`\n\n"
            f"{types_help}\n\n"
            "*مثال:*\n"
            "`/email all | concrete candle`\n"
            "`/email welcome | handmade candles`")
        return

    parts = [p.strip() for p in raw.split("|")]
    email_type = parts[0].lower()
    product = parts[1] if len(parts) > 1 else "handmade concrete candle"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        type_instruction = "Create ALL 8 email templates" if email_type == "all" else f"Create a {email_type} email"

        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are an email marketing expert for e-commerce brands. "
                "You write emails that get opened, read, and convert. "
                "Write emails in BOTH English AND Finnish."
            ),
            user_prompt=(
                f"{type_instruction} for:\n"
                f"Product: {product}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "For each email:\n"
                "📧 *Subject line* (3 options, A/B testable)\n"
                "👁 *Preview text*\n"
                "📝 *Body* (full text, ready to send)\n"
                "🔘 *CTA button text*\n"
                "⏰ *Best send time*\n"
                "💡 *Pro tip* for higher conversion\n\n"
                "Write in BOTH:\n"
                "🇬🇧 English version\n"
                "🇫🇮 Finnish version\n\n"
                "Make them personal, warm, and on-brand for an artisan maker."
            ),
        )
        await _send_result(message, f"📧 *ایمیل مارکتینگ — {email_type}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /pricing — Smart Pricing Strategy
# ═══════════════════════════════════════════════

@router.message(Command("pricing"))
async def cmd_pricing(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/pricing")

    if not raw:
        await safe_reply(message, "💰 *استراتژی قیمت‌گذاری هوشمند:*\n\n"
            "`/pricing [محصول] | [هزینه تولید €] | [قیمت فعلی €]`\n\n"
            "*مثال:*\n"
            "`/pricing concrete candle small | 8 | 25`\n"
            "`/pricing large stone candle | 15 | 45`\n\n"
            "_تحلیل قیمت رقبا + استراتژی بهینه + محاسبه سود_")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    cost = parts[1] if len(parts) > 1 else "unknown"
    current = parts[2] if len(parts) > 2 else "unknown"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a pricing strategist for handmade goods and Etsy sellers. "
                "You understand value-based pricing, competitor pricing, and pricing psychology. "
                "Write in Persian with calculations."
            ),
            user_prompt=(
                "Create a PRICING STRATEGY for:\n"
                f"Product: {product}\n"
                f"Production cost: €{cost}\n"
                f"Current price: €{current}\n"
                "Market: Finland + Etsy international\n\n"
                "📊 *1. COMPETITOR PRICE ANALYSIS:*\n"
                "- Typical price range for similar items\n"
                "- Where you stand vs competitors\n\n"
                "💰 *2. COST BREAKDOWN & MARGIN:*\n"
                "- Materials, labor (hourly rate €15-25), packaging, shipping\n"
                "- Etsy fees (6.5% transaction + 3.5% payment + €0.20 listing)\n"
                "- Actual profit per sale\n\n"
                "🎯 *3. RECOMMENDED PRICING:*\n"
                "- Economy price (volume strategy)\n"
                "- Standard price (balanced)\n"
                "- Premium price (value strategy)\n"
                "- Why each works\n\n"
                "🧠 *4. PRICING PSYCHOLOGY:*\n"
                "- Charm pricing (€34.99 vs €35)\n"
                "- Anchoring (show higher price first)\n"
                "- Bundle pricing strategy\n"
                "- Free shipping threshold\n\n"
                "📈 *5. PROFIT MAXIMIZER:*\n"
                "- Upsell ideas\n"
                "- Bundle combinations\n"
                "- Volume discounts that INCREASE total revenue\n"
                "- Gift wrapping premium\n\n"
                "🔄 *6. SEASONAL PRICING:*\n"
                "- When to raise (Christmas, Valentine's)\n"
                "- When to discount\n"
                "- Flash sale strategy"
            ),
            temp=0.7,
        )
        await _send_result(message, f"💰 *استراتژی قیمت — {product}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /viral — Viral Content Formula Generator
# ═══════════════════════════════════════════════

@router.message(Command("viral"))
async def cmd_viral(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/viral")

    if not raw:
        await safe_reply(message, "🔥 *فرمول محتوای وایرال:*\n\n"
            "`/viral [محصول یا موضوع]`\n\n"
            "*مثال:*\n"
            "`/viral concrete candle making`\n"
            "`/viral handmade in Finland`\n\n"
            "_۱۰ ایده محتوای وایرال با فرمول اثبات‌شده_\n"
            "_هر کدوم با اسکریپت کامل + نکات الگوریتم_")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a viral content strategist who has reverse-engineered 10,000+ viral posts. "
                "You understand Instagram Reels algorithm (watch time, saves, shares), TikTok's "
                "For You Page ranking (completion rate, loops, engagement velocity), and Pinterest's "
                "visual discovery engine. You specialize in handmade/artisan/satisfying/ASMR content "
                "which naturally goes viral. You know trending audio patterns and hook psychology. "
                "Write strategy in Persian. Scripts and captions in English."
            ),
            user_prompt=(
                f"Create 10 VIRAL CONTENT IDEAS for: {raw}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "For each idea:\n\n"
                "🔥 *IDEA [#]: [Title]*\n"
                "📊 Viral potential: ⭐⭐⭐⭐⭐\n"
                "📱 Platform: [Instagram/TikTok/Pinterest/All]\n"
                "🎯 Format: [Reel/Carousel/Story/Photo]\n"
                "⏱ Length: [duration]\n\n"
                "🎬 *SCRIPT:*\n"
                "Hook (first 3 sec): [MOST IMPORTANT]\n"
                "Content: [scene by scene]\n"
                "CTA: [call to action]\n\n"
                "✍️ *CAPTION:* [ready to paste, EN]\n"
                "🏷 *HASHTAGS:* [optimized set]\n"
                "🎵 *AUDIO:* [trending sound suggestion]\n\n"
                "💡 *WHY IT GOES VIRAL:*\n"
                "- Psychological trigger (curiosity/satisfaction/surprise/ASMR)\n"
                "- Algorithm hack (saves, shares, watch time)\n\n"
                "Types to include:\n"
                "- Satisfying process (pouring, unmolding)\n"
                "- Before/after transformation\n"
                "- ASMR (sounds of crafting)\n"
                "- Behind-the-scenes raw moment\n"
                "- Packing order (satisfying)\n"
                "- Day in the life of a maker\n"
                "- Unexpected reveal\n"
                "- Tutorial/educational\n"
                "- Trend participation\n"
                "- Emotional storytelling"
            ),
            temp=0.95,
        )
        await _send_result(message, f"🔥 *۱۰ ایده وایرال — {raw}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /collab — Influencer & Collaboration
# ═══════════════════════════════════════════════

@router.message(Command("collab"))
async def cmd_collab(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/collab")

    if not raw:
        await safe_reply(message, "🤝 *همکاری و اینفلوئنسر مارکتینگ:*\n\n"
            "`/collab [محصول یا نیچ]`\n\n"
            "*مثال:*\n"
            "`/collab handmade candles Finland`\n"
            "`/collab home decor artisan`\n\n"
            "_پیدا کردن اینفلوئنسرها + قالب پیام + ایده همکاری_")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are an influencer marketing expert for artisan brands. "
                "You know how to find, approach, and collaborate with micro-influencers "
                "on a zero or minimal budget. Write in Persian with English templates."
            ),
            user_prompt=(
                f"Create a COMPLETE influencer & collaboration strategy for: {raw}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "Budget: €0-50 (product gifting mainly)\n\n"
                "📋 *1. IDEAL INFLUENCER PROFILES:*\n"
                "- 5 types of influencers to target\n"
                "- Follower range for each (micro: 1K-10K is best)\n"
                "- Search hashtags to find them\n"
                "- Search keywords on Instagram/TikTok\n\n"
                "✉️ *2. OUTREACH TEMPLATES:*\n"
                "- DM template (English)\n"
                "- DM template (Finnish)\n"
                "- Email pitch template\n"
                "- Follow-up message\n\n"
                "🤝 *3. COLLABORATION IDEAS:*\n"
                "- Product gifting (how to do it right)\n"
                "- Content exchange\n"
                "- Giveaway collab\n"
                "- Affiliate/discount code\n"
                "- Guest content swap\n\n"
                "📦 *4. GIFTING PLAYBOOK:*\n"
                "- How to package for influencers\n"
                "- Note to include (template)\n"
                "- Unboxing experience checklist\n"
                "- What to ask them to post\n\n"
                "📊 *5. TRACKING & ROI:*\n"
                "- How to measure success\n"
                "- Discount code strategy\n"
                "- Content repurposing from collabs\n\n"
                "🏪 *6. OTHER COLLABORATIONS:*\n"
                "- Local Finland shops/cafes to partner with\n"
                "- Markets and fairs to participate\n"
                "- Cross-brand collaborations ideas"
            ),
        )
        await _send_result(message, f"🤝 *استراتژی همکاری — {raw}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /ads — Ad Copy Generator
# ═══════════════════════════════════════════════

@router.message(Command("ads"))
async def cmd_ads(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/ads")

    if not raw:
        await safe_reply(message, "📣 *تبلیغ‌ساز حرفه‌ای — Ad Copy:*\n\n"
            "`/ads [محصول] | [هدف] | [بودجه €]`\n\n"
            "*مثال:*\n"
            "`/ads concrete candle | sales | 50`\n"
            "`/ads new collection | awareness | 20`\n\n"
            "_تبلیغات آماده برای:_\n"
            "📸 Instagram/Facebook Ads\n"
            "📌 Pinterest Ads\n"
            "🔍 Etsy Ads\n"
            "🎵 TikTok Ads")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    objective = parts[1] if len(parts) > 1 else "sales"
    budget = parts[2] if len(parts) > 2 else "50"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a paid advertising expert for small e-commerce brands. "
                "You create high-converting ad copy with minimal budgets. "
                "You know Meta Ads, Pinterest Ads, Etsy Ads, and TikTok Ads. "
                "Write in Persian with ready-to-use English and Finnish ad copy."
            ),
            user_prompt=(
                "Create AD COPY for all major platforms:\n"
                f"Product: {product}\n"
                f"Objective: {objective}\n"
                f"Budget: €{budget}/month\n"
                f"{brand_ctx(message.chat.id)}\n"
                "📸 *INSTAGRAM/FACEBOOK ADS:*\n"
                "3 ad variations:\n"
                "- Primary text (125 chars)\n"
                "- Headline\n"
                "- Description\n"
                "- CTA button suggestion\n"
                "- Audience targeting recommendation\n"
                "- Image direction\n\n"
                "📌 *PINTEREST ADS:*\n"
                "2 promoted pin variations:\n"
                "- Pin title\n"
                "- Pin description\n"
                "- Keywords to target\n"
                "- Board strategy\n\n"
                "🔍 *ETSY ADS:*\n"
                "- Budget allocation advice\n"
                "- Which listings to promote\n"
                "- Tag optimization for ads\n\n"
                "🎵 *TIKTOK/REELS AD:*\n"
                "- 15-sec ad script\n"
                "- Hook ideas\n"
                "- Trending format to use\n\n"
                "💡 *BUDGET ALLOCATION:*\n"
                f"How to split €{budget}/month across platforms for maximum ROI\n\n"
                "📊 *TARGETING:*\n"
                "Detailed audience targeting for each platform\n"
                "Lookalike audience strategy\n"
                "Retargeting plan\n\n"
                "All ad copy in BOTH English and Finnish."
            ),
        )
        await _send_result(message, f"📣 *تبلیغات — {product}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /social — Social Proof System
# ═══════════════════════════════════════════════

@router.message(Command("social"))
async def cmd_social(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/social")

    if not raw:
        await safe_reply(message, "⭐ *سیستم اعتمادسازی — Social Proof:*\n\n"
            "`/social [محصول]`\n\n"
            "*مثال:*\n"
            "`/social handmade concrete candle`\n\n"
            "_تولید می‌کنه:_\n"
            "⭐ قالب درخواست نظر از مشتری\n"
            "📸 راهنمای UGC (محتوای کاربری)\n"
            "💬 نمونه پاسخ به نظرات\n"
            "🏷 Highlight/استوری اعتمادسازی\n"
            "📊 Trust badge و گارانتی")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a social proof and trust-building expert for e-commerce brands. "
                "You know how to leverage reviews, UGC, and testimonials to boost sales. "
                "Write in Persian with English/Finnish templates."
            ),
            user_prompt=(
                f"Create a COMPLETE social proof strategy for: {raw}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "⭐ *1. REVIEW COLLECTION:*\n"
                "- Follow-up message after purchase (EN + FI)\n"
                "- Review request email template\n"
                "- Incentive ideas (without violating Etsy rules)\n"
                "- Where to collect: Etsy, Google, Instagram\n\n"
                "📸 *2. UGC (User-Generated Content):*\n"
                "- How to encourage customers to share photos\n"
                "- Hashtag for UGC collection\n"
                "- Repost template/caption\n"
                "- UGC campaign idea\n\n"
                "💬 *3. RESPONSE TEMPLATES:*\n"
                "- Reply to positive review (EN + FI)\n"
                "- Reply to negative review (EN + FI)\n"
                "- Reply to questions (EN + FI)\n"
                "- DM response to compliments\n\n"
                "📱 *4. INSTAGRAM HIGHLIGHTS:*\n"
                "- Highlight categories for trust\n"
                "- Content for each highlight\n"
                "- Story templates for reviews/testimonials\n\n"
                "🛡 *5. TRUST SIGNALS:*\n"
                "- Bio elements that build trust\n"
                "- Story highlights to create\n"
                "- Etsy shop 'About' section\n"
                "- Packaging inserts that encourage sharing\n\n"
                "📊 *6. NUMBERS STRATEGY:*\n"
                "- How to showcase social proof (X happy customers)\n"
                "- Milestone celebration posts\n"
                "- Behind-the-numbers content"
            ),
        )
        await _send_result(message, f"⭐ *اعتمادسازی — {raw}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /swipe — Ready-to-Use Caption/Bio/CTA Library
# ═══════════════════════════════════════════════

@router.message(Command("swipe"))
async def cmd_swipe(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/swipe")
    category = raw.lower() if raw else ""

    categories = {
        "bio": "Instagram bio variations",
        "cta": "Call-to-action phrases",
        "hook": "Post/Reel opening hooks",
        "close": "Closing lines for captions",
        "dm": "DM response templates",
        "faq": "FAQ answers for customers",
    }

    if category not in categories:
        lines = "\n".join(f"📝 `{k}` — {v}" for k, v in categories.items())
        await safe_reply(message, "📚 *کتابخانه آماده — Swipe File:*\n\n"
            "`/swipe [دسته]`\n\n"
            f"{lines}\n\n"
            "*مثال:*\n"
            "`/swipe bio`\n"
            "`/swipe hook`\n"
            "`/swipe cta`\n\n"
            "_مجموعه آماده کپی‌پیست!_")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    prompts = {
        "bio": (
            "Create 15 Instagram bio variations for a handmade candle brand in Finland.\n"
            "Each bio: max 150 chars, include: value prop, location, CTA.\n"
            "5 in English, 5 in Finnish, 5 bilingual.\n"
            "Also provide: best link-in-bio structure, emojis to use."
        ),
        "cta": (
            "Create 30 call-to-action phrases for an artisan candle brand.\n"
            "Categories: Shop now, Learn more, Share, Save, DM, Comment, Follow.\n"
            "In both English and Finnish.\n"
            "For: Instagram captions, Stories, Etsy listings, emails."
        ),
        "hook": (
            "Create 30 scroll-stopping opening hooks for Instagram posts/Reels.\n"
            "Categories: Question, Statement, Controversy, Secret, Number, Story.\n"
            "All tailored for handmade candles & home decor.\n"
            "In English. Mark which work best for Reels vs Posts."
        ),
        "close": (
            "Create 25 caption closing lines that drive engagement.\n"
            "Categories: Question, Poll, Challenge, Emotion, Urgency.\n"
            "In English and Finnish.\n"
            "For handmade candles & decor brand."
        ),
        "dm": (
            "Create 20 DM response templates for a candle business.\n"
            "Scenarios: new inquiry, price question, custom order, shipping, "
            "collaboration request, complaint, compliment, wholesale inquiry.\n"
            "In English and Finnish."
        ),
        "faq": (
            "Create 15 FAQ answers for a handmade candle business.\n"
            "Topics: materials, burn time, shipping, custom orders, scents, "
            "care instructions, wholesale, returns, gift wrapping.\n"
            "In English and Finnish. Ready to paste into Etsy FAQ and Instagram."
        ),
    }

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a copywriting expert for artisan brands. "
                "Create a ready-to-use swipe file library. "
                "Every item must be polished, on-brand, and ready to copy-paste."
            ),
            user_prompt=f"{prompts[category]}\n{brand_ctx(message.chat.id)}\n"
                        "Make everything READY TO COPY-PASTE. Number each item.",
        )
        emoji_map = {"bio": "🔤", "cta": "🔘", "hook": "🪝", "close": "✍️", "dm": "💬", "faq": "❓"}
        await _send_result(
            message,
            f"{emoji_map.get(category, '📚')} *Swipe File — {categories[category]}:*",
            body,
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /competitor — Deep Competitor SWOT
# ═══════════════════════════════════════════════

@router.message(Command("competitor"))
async def cmd_competitor(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/competitor")

    if not raw:
        await safe_reply(message, "🔍 *تحلیل عمیق رقبا — SWOT Analysis:*\n\n"
            "`/competitor [نیچ یا رقیب]`\n\n"
            "*مثال:*\n"
            "`/competitor concrete candle etsy sellers`\n"
            "`/competitor handmade candle market Finland`\n\n"
            "_تحلیل SWOT + فرصت‌ها + استراتژی مقابله_")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("🔍 دارم تحلیل عمیق بازار انجام می‌دم...")

    try:
        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a competitive intelligence analyst specializing in handmade/artisan "
                "e-commerce on Etsy, Amazon Handmade, and Nordic marketplaces (Tori.fi). "
                "You provide data-driven SWOT analysis with specific, actionable strategies — "
                "not generic advice. You understand the Finnish/Nordic home decor market, "
                "candle industry trends, and what differentiates winners from losers. "
                "Write in Persian with English competitive terms and benchmarks."
            ),
            user_prompt=(
                f"Do a DEEP competitive analysis for: {raw}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "📊 *1. MARKET OVERVIEW:*\n"
                "- Market size and growth\n"
                "- Key players\n"
                "- Price ranges\n"
                "- Demand trends\n\n"
                "🏢 *2. TOP 5 COMPETITOR PROFILES:*\n"
                "For each: strengths, weaknesses, pricing, USP, social media presence\n\n"
                "📋 *3. SWOT ANALYSIS (your brand):*\n"
                "- Strengths (what you do well)\n"
                "- Weaknesses (gaps to fix)\n"
                "- Opportunities (market gaps to exploit)\n"
                "- Threats (risks to watch)\n\n"
                "🎯 *4. COMPETITIVE ADVANTAGES:*\n"
                "- USP ideas for differentiation\n"
                "- Blue ocean opportunities\n"
                "- Underserved customer segments\n\n"
                "🗺 *5. BATTLE PLAN:*\n"
                "- Short-term (this month): 5 actions\n"
                "- Medium-term (3 months): 5 milestones\n"
                "- Long-term (6-12 months): 3 strategic goals\n\n"
                "💡 *6. STEAL-WORTHY IDEAS:*\n"
                "- 5 things competitors do well that you should adopt\n"
                "- 5 things they do poorly that you can exploit"
            ),
            temp=0.7,
        )
        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        await _send_result(message, f"🔍 *تحلیل رقبا — {raw}:*", body)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════════════
# /megapost — Generate pro photo + poster + all content
# ═══════════════════════════════════════════════

@router.message(Command("megapost"))
async def cmd_megapost(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/megapost")

    if not raw:
        await safe_reply(message, "💎 *مگاپست — حداکثر محتوا از ۱ محصول:*\n\n"
            "`/megapost [محصول] | [قیمت €] | [توضیح]`\n\n"
            "*مثال:*\n"
            "`/megapost Concrete Candle | 35 | Soy wax, lavender, handmade`\n\n"
            "*تولید می‌کنه:*\n"
            "📸 ۴ عکس حرفه‌ای (۴ استایل مختلف)\n"
            "🎨 ۳ پوستر فروش\n"
            "✍️ ۵ کپشن EN + ۵ کپشن FI\n"
            "🏷 ۵۰ هشتگ\n"
            "📋 آگهی Etsy + Tori.fi\n"
            "🎬 اسکریپت ریلز\n"
            "📧 ایمیل معرفی\n"
            "📅 برنامه ۷ روزه\n\n"
            "_بمب اتمی محتوا! 💣_")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    price = parts[1] if len(parts) > 1 else ""
    desc = parts[2] if len(parts) > 2 else ""

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    status = await message.answer("💎 *مگاپست* — ساخت بمب محتوا شروع شد... (چند مرحله)\n\n⏳ مرحله ۱: عکس‌های حرفه‌ای...")

    try:
        # ── Step 1: Generate 4 professional photos ──
        styles = [
            ("dark", "dark moody, dramatic side lighting, dark walnut wood, shadows, Kinfolk style"),
            ("nordic", "Scandinavian, light birch wood, white grey tones, soft northern light, Finnish interior"),
            ("cozy", "cozy hygge, warm blanket, fairy lights bokeh, autumn vibes, intimate"),
            ("flat", "flat lay top-down, concrete background, dried petals, matches, Instagram flatlay"),
        ]

        photos_sent = 0
        for style_name, style_desc in styles:
            try:
                prompt = (
                    f"Professional product photography of {product}, "
                    "handmade artisan candle in textured raw concrete vessel, "
                    f"natural soy wax, {style_desc}, "
                    "8k resolution, commercial grade, magazine cover quality"
                )
                encoded = urllib.parse.quote(prompt)
                img_url = (
                    f"https://image.pollinations.ai/prompt/{encoded}"
                    f"?width=1024&height=1024&model=flux&seed={random.randint(1, 99999)}"
                )
                # v10.1: Route through TITANIUM shielded client
                if _TITANIUM_ACTIVE:
                    ti_resp = await shielded_get(img_url, timeout=60.0)
                    if ti_resp.success and ti_resp.status_code == 200 and len(ti_resp.content) > 1000:
                        photo = BufferedInputFile(ti_resp.content, filename=f"mega_{style_name}.png")
                        style_emojis = {"dark": "🌑", "nordic": "🇫🇮", "cozy": "🕯", "flat": "📐"}
                        await message.answer_photo(
                            photo=photo,
                            caption=f"📸 {style_emojis.get(style_name, '📸')} *{style_name}* — {product}",
                            parse_mode="Markdown",
                        )
                        photos_sent += 1
                    continue
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    resp = await client.get(img_url)
                    if resp.status_code == 200:
                        photo = BufferedInputFile(resp.content, filename=f"mega_{style_name}.png")
                        style_emojis = {"dark": "🌑", "nordic": "🇫🇮", "cozy": "🕯", "flat": "📐"}
                        await message.answer_photo(
                            photo=photo,
                            caption=f"📸 {style_emojis.get(style_name, '📸')} *{style_name}* — {product}",
                            parse_mode="Markdown",
                        )
                        photos_sent += 1
            except Exception as exc:
                logger.warning("Megapost photo %s failed: %s", style_name, exc)

        # ── Step 2: Generate posters ──
        await safe_edit_text(status, "💎 مرحله ۲: پوسترها...")
        try:
            from arki_project.utils.poster_gen import generate_poster
            for tpl in ["sale", "product", "minimal"]:
                try:
                    img_bytes = generate_poster(tpl, product, price, "", desc)
                    photo = BufferedInputFile(img_bytes, filename=f"mega_poster_{tpl}.png")
                    await message.answer_photo(photo=photo, caption=f"🎨 پوستر {tpl}")
                except Exception as e:
                    logger.debug("Suppressed: %s", e)
        except Exception as e:
            logger.debug("Suppressed: %s", e)

        # ── Step 3: AI content (everything) ──
        await safe_edit_text(status, "💎 مرحله ۳: تولید متن‌ها...")

        body = await _ai_generate(
            message, ai_client, settings,
            system_prompt=(
                "You are a complete marketing team in one: copywriter, social media manager, "
                "SEO expert, email marketer, and content strategist. "
                "Create the ULTIMATE content package. Write in English and Finnish."
            ),
            user_prompt=(
                "Create the ULTIMATE MEGA CONTENT PACKAGE for:\n"
                f"Product: {product}\n"
                f"Price: €{price}\n"
                f"Description: {desc}\n"
                f"{brand_ctx(message.chat.id)}\n"
                "Generate ALL:\n\n"
                "═══ 5 INSTAGRAM CAPTIONS (EN) ═══\n"
                "Story, Educational, Sale, Aesthetic, Engagement styles\n\n"
                "═══ 5 INSTAGRAM CAPTIONS (FI) ═══\n"
                "Same 5 styles in Finnish\n\n"
                "═══ 50 HASHTAGS ═══\n"
                "20 English popular + 15 English niche + 15 Finnish\n\n"
                "═══ ETSY LISTING (Full) ═══\n"
                "SEO title + description + 13 tags + materials\n\n"
                "═══ TORI.FI LISTING (Finnish) ═══\n"
                "Otsikko + Kuvaus + Hinta\n\n"
                "═══ REEL SCRIPT ═══\n"
                "30-sec, scene-by-scene, with hook\n\n"
                "═══ EMAIL ═══\n"
                "Subject + body (EN) for newsletter\n\n"
                "═══ 7-DAY POSTING PLAN ═══\n"
                "Which caption, when, where, what photo\n\n"
                "Everything READY TO COPY-PASTE."
            ),
        )

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        await _send_result(message, f"💎 *مگاپست کامل — {product}:*", body)

        # Summary
        await safe_reply(message, "✅ *مگاپست تمام شد!*\n\n"
            f"📸 {photos_sent} عکس حرفه‌ای\n"
            "🎨 ۳ پوستر\n"
            "✍️ ۱۰ کپشن (EN+FI)\n"
            "🏷 ۵۰ هشتگ\n"
            "📋 آگهی Etsy + Tori.fi\n"
            "🎬 اسکریپت ریلز\n"
            "📧 ایمیل\n"
            "📅 برنامه ۷ روزه\n\n"
            "_همه چیز آماده‌ — فقط پست کن! 🚀_")

    except Exception as exc:
        logger.error("Megapost failed: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


