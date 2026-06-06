
from __future__ import annotations
"""
tg_bot/handlers/sales_brain.py
────────────────────────────────
💰 Sales Intelligence Engine — the *brain* behind sales strategy.

Goes beyond basic funnels into deep sales intelligence: upselling,
bundling, retention, forecasting, loyalty programs, and customer psychology.

Every command is:
- Inline-keyboard driven
- Context-aware (brand, products, sales data)
- Candle/decor niche specialized
- Bilingual (EN/FI)
- Meticulous in detail

Commands:
  /salesai     — AI sales advisor: what to focus on right now
  /upsell      — Upsell/cross-sell strategy for each product
  /bundle      — Smart bundle creator
  /retention   — Customer retention campaign generator
  /winback     — Win-back sequences for lost customers
  /loyalty     — Loyalty program designer
  /forecast    — Sales forecast based on data + market
  /objection   — Customer objection handler (FAQ scripts)
  /giftguide   — Occasion-based gift guide generator
  /profit      — Profit calculator & margin optimizer
"""


import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
from arki_project.handlers.shared import brand_ctx, extract_args, products_ctx
from arki_project.utils.data_store import store
from arki_project.utils.v7_core import (
    enhance_system_prompt, store_result,
)

logger = logging.getLogger(__name__)
# v9.3: Service layer

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]

# v9.2: Marketing engine integration
try:
    from arki_project.utils.v7_core import get_marketing_engine
    _marketing = get_marketing_engine()
except Exception as exc:
    logger.error("Error in handler: %s", exc)
    _marketing = None
router = Router(name="sales_brain")


# ── helpers ──






def _sales_ctx(chat_id: int) -> str:
    """Sales context using persistent store."""
    sales = store.get_sales(chat_id)
    if sales:
        total = sum(float(s.get("amount", 0)) for s in sales)
        by_plat: dict[str, float] = {}
        for s in sales:
            by_plat[s.get("platform", "?")] = by_plat.get(s.get("platform", "?"), 0) + float(s.get("amount", 0))
        plat_str = ", ".join(f"{k}: €{v:.0f}" for k, v in by_plat.items())
        return f"Sales data: {len(sales)} transactions, €{total:.0f} total\nBy platform: {plat_str}"
    return "Sales data: Early stage, building first sales"


async def _ai(
    message: Message, ai_client: AIClient, settings: Settings,
    system: str, user: str, temp: float = 0.85, max_tokens: int = 4096,
) -> str:
    import time as _t
    _t0 = _t.time()
    uid = str(message.from_user.id) if message.from_user else "0"
    cfg = await ai_client.get_user_config(message.from_user.id)
    mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)
    # v8: Enhance system prompt with RAG + prompt engineering
    enhanced_sys = enhance_system_prompt(system, user_text=user, user_id=uid)
    result = await ai_client.ask_raw(
        messages=[{"role": "system", "content": enhanced_sys}, {"role": "user", "content": user}],
        model_key=mk, temperature=temp, max_tokens=max_tokens,
    )
    # v8: Store + telemetry with real timing
    store_result(int(uid) if uid.isdigit() else 0, user[:300], result[:500] if result else "", "sales_brain", duration_s=_t.time()-_t0)
    return result


_SYSTEM_SALES = (
    "You are a WORLD-CLASS e-commerce sales strategist specializing in handmade/artisan "
    "brands in Europe. You know customer psychology, pricing strategy, conversion optimization, "
    "and the specifics of selling on Etsy, Tori.fi, Amazon Handmade, Instagram, and Nordic "
    "marketplaces. You think like both a data scientist and a seasoned merchant. "
    "You write fluently in English AND Finnish. "
    "Write explanations in Persian. Sales materials in EN+FI. "
    "Be meticulous, structured, and brutally practical."
)


# ═══════════════════════════════════════
# /salesai — AI Sales Advisor
# ═══════════════════════════════════════

@router.message(Command("salesai"))
async def cmd_salesai(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_SALES,
        user=(
            "Act as my PERSONAL SALES ADVISOR. Analyze my business and tell me "
            "EXACTLY what to do right now.\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n"
            f"{_sales_ctx(message.chat.id)}\n"
            f"Date: {datetime.now().strftime('%A, %B %d, %Y')}\n\n"
            "Provide:\n\n"
            "🎯 *TODAY'S #1 PRIORITY:*\n"
            "The single most impactful thing to do TODAY for sales\n\n"
            "💰 *REVENUE OPPORTUNITIES* (top 5):\n"
            "For each: what, expected revenue, effort level, timeline\n\n"
            "⚠️ *REVENUE LEAKS* (things losing you money):\n"
            "What's broken in the sales process\n\n"
            "📊 *PERFORMANCE SCORECARD:*\n"
            "- Product range: score /10\n"
            "- Pricing strategy: score /10\n"
            "- Platform coverage: score /10\n"
            "- Marketing effectiveness: score /10\n"
            "- Customer experience: score /10\n"
            "- Overall: score /10\n\n"
            "🔥 *QUICK WINS* (3 actions, under 30 min each):\n"
            "Specific, immediate revenue impact\n\n"
            "📈 *30-DAY SALES TARGET:*\n"
            "Realistic target + daily actions to hit it\n\n"
            "Write in Persian. Be specific, no generic advice."
        ),
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💡 آپسل/کراس‌سل", callback_data="sai:upsell"),
            InlineKeyboardButton(text="📦 باندل‌ها", callback_data="sai:bundle"),
        ],
        [
            InlineKeyboardButton(text="🎁 گیفت گاید", callback_data="sai:gift"),
            InlineKeyboardButton(text="💵 سود محاسبه", callback_data="sai:profit"),
        ],
    ])

    for chunk in split_for_telegram(f"💰 *مشاور فروش AI:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)
    await message.answer("⬇️ ابزارهای فروش:", reply_markup=kb)


@router.callback_query(F.data.startswith("sai:"))
async def cb_salesai(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        cmds = {"upsell": "/upsell", "bundle": "/bundle", "gift": "/giftguide", "profit": "/profit"}
        c = callback.data.split(":")[1]
        await safe_reply(callback.message, f"دستور رو بزن: `{cmds.get(c, '/salesai')}`")
    except Exception as exc:
        logger.error("cb_salesai error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)


# ═══════════════════════════════════════
# /upsell — Upsell / Cross-sell Strategy
# ═══════════════════════════════════════

@router.message(Command("upsell"))
async def cmd_upsell(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/upsell")
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_SALES,
        user=(
            "Create a COMPLETE UPSELL & CROSS-SELL STRATEGY.\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n"
            f"{'Extra context: ' + raw if raw else ''}\n\n"
            "🔺 *UPSELL MATRIX:*\n"
            "For each product, create upsell paths:\n"
            "- What to suggest as upgrade (bigger/premium version)\n"
            "- Price anchor strategy\n"
            "- Upsell message (EN + FI)\n"
            "- Where to show it (product page, cart, email)\n\n"
            "↔️ *CROSS-SELL MATRIX:*\n"
            "Which products go together:\n"
            "- Natural pairs (candle + holder, set + gift box)\n"
            "- 'Customers also bought' suggestions\n"
            "- Cross-sell message (EN + FI)\n\n"
            "📧 *POST-PURCHASE UPSELL SEQUENCE:*\n"
            "5-email sequence after first purchase:\n"
            "- Day 1: Thank you\n"
            "- Day 3: Care tips + cross-sell\n"
            "- Day 7: Review request + upsell\n"
            "- Day 14: New product tease\n"
            "- Day 30: Reorder reminder\n"
            "Each email: subject line + body (EN + FI)\n\n"
            "💬 *UPSELL SCRIPTS:*\n"
            "- DM response when someone asks about a product\n"
            "- Comment reply that leads to upsell\n"
            "- Story reply upsell\n"
            "(EN + FI)\n\n"
            "📊 *REVENUE IMPACT:*\n"
            "Expected average order value increase %\n\n"
            "Write in Persian. Sales materials in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"🔺 *استراتژی آپسل و کراس‌سل:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


# ═══════════════════════════════════════
# /bundle — Smart Bundle Creator
# ═══════════════════════════════════════

@router.message(Command("bundle"))
async def cmd_bundle(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/bundle")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎁 باندل هدیه", callback_data="bun:gift"),
                InlineKeyboardButton(text="🏠 باندل دکور", callback_data="bun:decor"),
            ],
            [
                InlineKeyboardButton(text="💍 باندل عروسی", callback_data="bun:wedding"),
                InlineKeyboardButton(text="🏢 باندل شرکتی", callback_data="bun:corporate"),
            ],
            [
                InlineKeyboardButton(text="🌟 باندل لاکچری", callback_data="bun:luxury"),
                InlineKeyboardButton(text="📦 باندل استارتر", callback_data="bun:starter"),
            ],
            [
                InlineKeyboardButton(text="🔥 همه باندل‌ها", callback_data="bun:all"),
            ],
        ])
        await safe_reply(message, "📦 *باندل‌ساز هوشمند:*\n\n"
            "ترکیب محصولات = *ارزش بالاتر + فروش بیشتر*\n\n"
            "`/bundle [نوع باندل]`\n"
            "_یا انتخاب کن:_",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_SALES,
        user=(
            f"Create SMART PRODUCT BUNDLES for: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n\n"
            "Design 5 BUNDLES:\n\n"
            "For EACH bundle:\n"
            "📦 *Bundle Name* (catchy, EN + FI)\n"
            "📋 *What's Included:* List of items\n"
            "💰 *Pricing Strategy:*\n"
            "  - Individual total: €XX\n"
            "  - Bundle price: €XX (XX% savings)\n"
            "  - Your margin: €XX\n"
            "📝 *Bundle Description* (EN): Etsy-ready, SEO-optimized\n"
            "📝 *Bundle Description* (FI): Tori.fi-ready\n"
            "🏷 *13 Etsy Tags*\n"
            "🎯 *Target Customer:* Who buys this & why\n"
            "📅 *Best Season:* When this sells best\n"
            "📸 *Photo Direction:* How to photograph the bundle\n"
            "🎁 *Packaging Idea:* How to present it\n\n"
            "💡 *BUNDLE PSYCHOLOGY:*\n"
            "- Why bundles work\n"
            "- Optimal discount % for handmade\n"
            "- How to present 'value' not 'discount'\n\n"
            "📊 *REVENUE PROJECTION:*\n"
            "Expected monthly bundle revenue\n\n"
            "Write in Persian. Listings in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"📦 *باندل‌های هوشمند — {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("bun:"))
async def cb_bundle(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("📦 طراحی باندل...")
        types = {
            "gift": "Gift bundles for birthdays, holidays, special occasions",
            "decor": "Home decor sets for different rooms & styles",
            "wedding": "Wedding & event bundles (favors, centerpieces, decor)",
            "corporate": "Corporate gift bundles for companies & offices",
            "luxury": "Premium luxury bundles with premium packaging",
            "starter": "Starter/discovery bundles for new customers",
            "all": "ALL bundle types — complete bundle strategy",
        }
        t = callback.data.split(":")[1]
        fake_msg = callback.message.model_copy(
            update={"text": f"/bundle {types.get(t, t)}", "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_bundle(fake_msg, ai_client, settings)
    except Exception as exc:
        logger.error("cb_bundle error: %s", exc)
        try:
            await callback.message.answer("⚠️ خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        except Exception as e:
            logger.debug("Suppressed: %s", e)


# ═══════════════════════════════════════
# /retention — Customer Retention Campaigns
# ═══════════════════════════════════════

@router.message(Command("retention"))
async def cmd_retention(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    raw = extract_args(message.text or "", "/retention")

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_SALES,
        user=(
            "Create a COMPLETE CUSTOMER RETENTION SYSTEM.\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n"
            f"{'Context: ' + raw if raw else ''}\n\n"
            "🔄 *RETENTION FUNNEL:*\n"
            "Stage 1: First-time buyer → Repeat buyer\n"
            "Stage 2: Repeat buyer → Regular customer\n"
            "Stage 3: Regular → VIP / Brand advocate\n"
            "For each stage: triggers, actions, messages, timeline\n\n"
            "📧 *EMAIL SEQUENCES (EN + FI):*\n"
            "1. Welcome series (3 emails)\n"
            "2. Post-purchase nurture (5 emails over 30 days)\n"
            "3. Reorder reminder (based on candle burn time)\n"
            "4. Birthday/anniversary\n"
            "5. 'We miss you' sequence\n"
            "For each: subject line + key content + CTA\n\n"
            "📱 *SOCIAL MEDIA RETENTION:*\n"
            "- How to make first buyers follow on Instagram\n"
            "- Story engagement tactics for existing customers\n"
            "- User-generated content campaign\n"
            "- Customer spotlight series\n\n"
            "🎁 *SURPRISE & DELIGHT:*\n"
            "- Insert card ideas (drives repeat purchase)\n"
            "- Handwritten note templates\n"
            "- Surprise gift thresholds\n"
            "- Seasonal customer appreciation gestures\n\n"
            "📊 *KPIs TO TRACK:*\n"
            "- Repeat purchase rate target\n"
            "- Customer lifetime value target\n"
            "- Churn rate benchmarks\n\n"
            "Write in Persian. Email content in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"🔄 *سیستم نگهداشت مشتری:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


# ═══════════════════════════════════════
# /winback — Win-Back Sequences
# ═══════════════════════════════════════

@router.message(Command("winback"))
async def cmd_winback(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    raw = extract_args(message.text or "", "/winback")

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_SALES,
        user=(
            "Create WIN-BACK campaigns for lost/inactive customers.\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n"
            f"{'Context: ' + raw if raw else ''}\n\n"
            "📧 *WIN-BACK EMAIL SEQUENCE (5 emails):*\n"
            "Email 1 (Day 30): Gentle 'We miss you'\n"
            "Email 2 (Day 37): Value reminder (what they're missing)\n"
            "Email 3 (Day 45): Exclusive offer / incentive\n"
            "Email 4 (Day 52): Social proof / new products\n"
            "Email 5 (Day 60): Last chance / break-up email\n\n"
            "For each email:\n"
            "- Subject line (3 options, A/B testable)\n"
            "- Preview text\n"
            "- Full body (EN)\n"
            "- Full body (FI)\n"
            "- CTA button text\n"
            "- Offer/incentive (if applicable)\n\n"
            "📱 *SOCIAL MEDIA WIN-BACK:*\n"
            "- Instagram DM templates (EN + FI)\n"
            "- Retargeting ad copy ideas\n"
            "- Story content for inactive followers\n\n"
            "🎁 *INCENTIVE LADDER:*\n"
            "- Level 1: Free shipping\n"
            "- Level 2: 10% discount\n"
            "- Level 3: Gift with purchase\n"
            "- Level 4: Exclusive/early access\n"
            "When to use each level\n\n"
            "Write in Persian. Email content in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"💌 *کمپین بازگشت مشتری:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


# ═══════════════════════════════════════
# /loyalty — Loyalty Program Designer
# ═══════════════════════════════════════

@router.message(Command("loyalty"))
async def cmd_loyalty(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/loyalty")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ امتیازی", callback_data="loy:points"),
                InlineKeyboardButton(text="🎖 VIP سطح‌بندی", callback_data="loy:tier"),
            ],
            [
                InlineKeyboardButton(text="📦 اشتراک ماهانه", callback_data="loy:subscription"),
                InlineKeyboardButton(text="🤝 معرفی دوست", callback_data="loy:referral"),
            ],
            [
                InlineKeyboardButton(text="🔥 همه مدل‌ها", callback_data="loy:all"),
            ],
        ])
        await safe_reply(message, "🏆 *طراح برنامه وفاداری:*\n\n"
            "کدوم مدل می‌خوای?\n\n"
            "`/loyalty [مدل]`\n"
            "_یا انتخاب کن:_",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_SALES,
        user=(
            f"Design a LOYALTY PROGRAM for: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n\n"
            "📋 *PROGRAM DESIGN:*\n"
            "- Program name (catchy, branded)\n"
            "- How it works (simple rules)\n"
            "- Earning mechanism\n"
            "- Reward tiers\n"
            "- Redemption options\n\n"
            "🎖 *TIER SYSTEM* (if applicable):\n"
            "- Bronze / Silver / Gold / Platinum\n"
            "- Threshold for each tier\n"
            "- Benefits per tier\n"
            "- Visual badges/icons\n\n"
            "📧 *COMMUNICATION:*\n"
            "- Welcome to program email (EN + FI)\n"
            "- Points/tier update notification\n"
            "- Reward available notification\n"
            "- Anniversary/milestone celebration\n\n"
            "📱 *IMPLEMENTATION:*\n"
            "- How to run this with Etsy/Tori.fi (manual tracking)\n"
            "- Instagram story integration\n"
            "- Simple spreadsheet template design\n"
            "- Insert card for packaging\n\n"
            "💰 *FINANCIAL MODEL:*\n"
            "- Cost of program\n"
            "- Expected revenue increase\n"
            "- ROI calculation\n"
            "- Break-even point\n\n"
            "Write in Persian. Customer-facing content in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"🏆 *برنامه وفاداری — {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("loy:"))
async def cb_loyalty(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("🏆 طراحی برنامه...")
        types = {
            "points": "Points-based: earn points per purchase, redeem for discounts/free products",
            "tier": "VIP Tier system: Bronze→Silver→Gold→Platinum with escalating benefits",
            "subscription": "Monthly subscription/candle club with exclusive products",
            "referral": "Referral program: give €5 get €5, friend discounts",
            "all": "ALL loyalty models — complete comparison + recommendation",
        }
        t = callback.data.split(":")[1]
        fake_msg = callback.message.model_copy(
            update={"text": f"/loyalty {types.get(t, t)}", "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_loyalty(fake_msg, ai_client, settings)
    except Exception as exc:
        logger.error("cb_loyalty error: %s", exc)
        try:
            await callback.message.answer("⚠️ خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        except Exception as e:
            logger.debug("Suppressed: %s", e)


# ═══════════════════════════════════════
# /forecast — Sales Forecast
# ═══════════════════════════════════════

@router.message(Command("forecast"))
async def cmd_forecast(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    raw = extract_args(message.text or "", "/forecast")

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_SALES,
        user=(
            "Create a SALES FORECAST for this handmade candle business.\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n"
            f"{_sales_ctx(message.chat.id)}\n"
            f"{'Context: ' + raw if raw else ''}\n"
            "Location: Finland\n"
            f"Date: {datetime.now().strftime('%B %Y')}\n\n"
            "📊 *12-MONTH REVENUE FORECAST:*\n"
            "Month-by-month projection with:\n"
            "- Expected sales volume\n"
            "- Revenue target\n"
            "- Key driver (season/platform/campaign)\n"
            "- Risk level\n\n"
            "📈 *SEASONAL ANALYSIS:*\n"
            "- Peak months for candle sales in Finland/Nordics\n"
            "- Shoulder months strategy\n"
            "- Dead months — what to do\n"
            "- Holiday calendar impact\n\n"
            "🛒 *PLATFORM REVENUE SPLIT:*\n"
            "Expected revenue by platform (Etsy, Tori.fi, Instagram, etc.)\n\n"
            "📦 *PRODUCT MIX FORECAST:*\n"
            "Which products will sell most in which months\n\n"
            "🎯 *SCENARIOS:*\n"
            "Conservative / Realistic / Optimistic projections\n\n"
            "💡 *ACTIONS TO HIT TARGETS:*\n"
            "Specific monthly actions to hit realistic scenario\n\n"
            "Write in Persian. Include €€€ numbers."
        ),
    )

    for chunk in split_for_telegram(f"📊 *پیش‌بینی فروش:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


# ═══════════════════════════════════════
# /objection — Customer Objection Handler
# ═══════════════════════════════════════

@router.message(Command("objection"))
async def cmd_objection(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/objection")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 قیمت بالاست", callback_data="obj:price"),
                InlineKeyboardButton(text="🚚 ارسال گرونه", callback_data="obj:shipping"),
            ],
            [
                InlineKeyboardButton(text="🤔 چرا هندمید؟", callback_data="obj:handmade"),
                InlineKeyboardButton(text="⏰ وقت ارسال؟", callback_data="obj:time"),
            ],
            [
                InlineKeyboardButton(text="🔒 اعتماد", callback_data="obj:trust"),
                InlineKeyboardButton(text="🔥 همه اعتراضات", callback_data="obj:all"),
            ],
        ])
        await safe_reply(message, "💬 *پاسخ‌گوی اعتراضات مشتری:*\n\n"
            "رایج‌ترین اعتراض؟ اسکریپت حرفه‌ای می‌سازم:\n\n"
            "`/objection [اعتراض مشتری]`\n"
            "_یا انتخاب کن:_",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_SALES,
        user=(
            f"Create PROFESSIONAL OBJECTION HANDLING for: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n\n"
            "For this objection, provide:\n\n"
            "🧠 *PSYCHOLOGY:* Why the customer says this (real reason behind it)\n\n"
            "💬 *RESPONSE SCRIPTS (5 approaches):*\n"
            "1. Empathy + Value — acknowledge and reframe\n"
            "2. Social Proof — what others say/do\n"
            "3. Education — teach why it's worth it\n"
            "4. Comparison — vs alternatives\n"
            "5. Urgency — limited availability/special offer\n\n"
            "For EACH:\n"
            "- DM response script (EN)\n"
            "- DM response script (FI)\n"
            "- Comment reply (public, EN)\n"
            "- Comment reply (public, FI)\n"
            "- Etsy message response\n\n"
            "📝 *FAQ ENTRY:*\n"
            "Pre-emptive FAQ text for website/Etsy (EN + FI)\n\n"
            "📸 *CONTENT IDEAS:*\n"
            "3 posts that pre-emptively handle this objection\n\n"
            "Write in Persian. Scripts in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"💬 *اعتراض: {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("obj:"))
async def cb_objection(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("💬 ...")
        objs = {
            "price": "Your candles are too expensive / Why so much for a candle?",
            "shipping": "Shipping cost is too high / Do you offer free shipping?",
            "handmade": "Why should I pay more for handmade vs store-bought candles?",
            "time": "How long does shipping take? I need it by [date]",
            "trust": "How do I know the quality? Is this a real business?",
            "all": "ALL common objections for handmade candle business",
        }
        t = callback.data.split(":")[1]
        fake_msg = callback.message.model_copy(
            update={"text": f"/objection {objs.get(t, t)}", "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_objection(fake_msg, ai_client, settings)
    except Exception as exc:
        logger.error("cb_objection error: %s", exc)
        try:
            await callback.message.answer("⚠️ خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        except Exception as e:
            logger.debug("Suppressed: %s", e)


# ═══════════════════════════════════════
# /giftguide — Occasion Gift Guide Generator
# ═══════════════════════════════════════

@router.message(Command("giftguide"))
async def cmd_giftguide(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/giftguide")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎄 کریسمس", callback_data="gift:christmas"),
                InlineKeyboardButton(text="💝 ولنتاین", callback_data="gift:valentine"),
            ],
            [
                InlineKeyboardButton(text="👩 روز مادر", callback_data="gift:mothers"),
                InlineKeyboardButton(text="🎂 تولد", callback_data="gift:birthday"),
            ],
            [
                InlineKeyboardButton(text="🏡 خانه‌تکانی", callback_data="gift:housewarming"),
                InlineKeyboardButton(text="💍 عروسی", callback_data="gift:wedding"),
            ],
            [
                InlineKeyboardButton(text="🏢 شرکتی", callback_data="gift:corporate"),
                InlineKeyboardButton(text="🔥 همه مناسبت‌ها", callback_data="gift:all"),
            ],
        ])
        await safe_reply(message, "🎁 *گیفت گاید ساز:*\n\n"
            "برای هر مناسبت، راهنمای هدیه حرفه‌ای:\n"
            "• پیشنهاد محصول\n"
            "• بسته‌بندی خاص\n"
            "• کپشن + آگهی\n\n"
            "`/giftguide [مناسبت]`\n"
            "_یا انتخاب کن:_",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_SALES,
        user=(
            f"Create a PROFESSIONAL GIFT GUIDE for occasion: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n\n"
            "🎁 *GIFT GUIDE:*\n\n"
            "*Budget Tiers:*\n"
            "- Under €20: what to offer\n"
            "- €20-€40: best sellers\n"
            "- €40-€70: premium options\n"
            "- €70+: luxury sets\n\n"
            "For each tier:\n"
            "- Product recommendation\n"
            "- Why it's perfect for this occasion\n"
            "- Packaging suggestion\n"
            "- Personalization options\n"
            "- Listing title (EN + FI)\n"
            "- Gift message suggestions (5, EN + FI)\n\n"
            "📱 *MARKETING CAMPAIGN:*\n"
            "- Instagram post caption (EN + FI)\n"
            "- Story sequence (5 slides)\n"
            "- Reel concept\n"
            "- Hashtags (20)\n"
            "- Email campaign for existing customers (EN + FI)\n"
            "- Etsy listing optimization for this occasion\n\n"
            "⏰ *TIMELINE:*\n"
            "When to start promoting\n"
            "Last order date for delivery\n"
            "Content calendar (2 weeks before)\n\n"
            "Write in Persian. Marketing content in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"🎁 *گیفت گاید — {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("gift:"))
async def cb_giftguide(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("🎁 ساخت گیفت گاید...")
        occasions = {
            "christmas": "Christmas / Joulu — Finland's biggest gift season",
            "valentine": "Valentine's Day — romantic candle gifts",
            "mothers": "Mother's Day — Äitienpäivä special",
            "birthday": "Birthday gifts — all ages & relationships",
            "housewarming": "Housewarming / tupaantuliaiset — new home gifts",
            "wedding": "Wedding / häät — favors, gifts, centerpieces",
            "corporate": "Corporate gifts — company gifts, employee appreciation",
            "all": "ALL occasions — complete year-round gift guide calendar",
        }
        t = callback.data.split(":")[1]
        fake_msg = callback.message.model_copy(
            update={"text": f"/giftguide {occasions.get(t, t)}", "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_giftguide(fake_msg, ai_client, settings)
    except Exception as exc:
        logger.error("cb_giftguide error: %s", exc)
        try:
            await callback.message.answer("⚠️ خطایی رخ داد. لطفاً دوباره امتحان کنید.")
        except Exception as e:
            logger.debug("Suppressed: %s", e)


# ═══════════════════════════════════════
# /profit — Profit Calculator & Optimizer
# ═══════════════════════════════════════

@router.message(Command("profit"))
async def cmd_profit(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/profit")

    if not raw:
        await safe_reply(message, "💵 *ماشین‌حساب سود:*\n\n"
            "`/profit [قیمت فروش] | [هزینه مواد] | [هزینه ارسال] | [پلتفرم]`\n\n"
            "*مثال:*\n"
            "`/profit 35 | 8 | 5 | etsy`\n"
            "`/profit 25 | 5 | 3 | tori`\n\n"
            "_یا بدون عدد بنویس `/profit analyze` برای تحلیل کلی:_")
        return

    if raw.lower() == "analyze":
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        body = await _ai(
            message, ai_client, settings,
            system=_SYSTEM_SALES,
            user=(
                "Create a COMPLETE PROFITABILITY ANALYSIS.\n\n"
                f"{brand_ctx(message.chat.id)}\n"
                f"{products_ctx(message.chat.id)}\n"
                f"{_sales_ctx(message.chat.id)}\n"
                "Location: Finland\n\n"
                "📊 *COST STRUCTURE:*\n"
                "Typical costs for handmade candle business:\n"
                "- Raw materials (wax, wick, fragrance, concrete)\n"
                "- Packaging\n"
                "- Labor (hourly rate)\n"
                "- Platform fees (Etsy: 6.5%, Tori.fi: free, etc.)\n"
                "- Shipping costs from Finland\n"
                "- Marketing budget\n"
                "- Overhead (tools, workspace, utilities)\n\n"
                "💰 *MARGIN ANALYSIS per product type:*\n"
                "- Large candle: costs → price → margin\n"
                "- Small candle: costs → price → margin\n"
                "- Tealight: costs → price → margin\n"
                "- Accessories: costs → price → margin\n"
                "- Bundles: costs → price → margin\n\n"
                "📈 *PRICING OPTIMIZATION:*\n"
                "- Are prices too low/right/high?\n"
                "- Price elasticity analysis\n"
                "- Psychological pricing suggestions\n"
                "- Free shipping threshold (at what order size?)\n\n"
                "🎯 *BREAK-EVEN ANALYSIS:*\n"
                "- Monthly fixed costs estimate\n"
                "- Units to break even\n"
                "- Revenue to break even\n\n"
                "💡 *10 WAYS TO IMPROVE MARGINS:*\n"
                "Specific, actionable margin improvement tactics\n\n"
                "Write in Persian. Include €€€ numbers."
            ),
        )
        for chunk in split_for_telegram(f"💵 *تحلیل سودآوری:*\n\n{body}"):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)
        return

    # Parse numbers
    parts = [p.strip() for p in raw.split("|")]
    try:
        sell_price = float(parts[0])
        material_cost = float(parts[1]) if len(parts) > 1 else 0
        shipping_cost = float(parts[2]) if len(parts) > 2 else 0
        platform = parts[3] if len(parts) > 3 else "etsy"
    except (ValueError, IndexError):
        await message.answer("❌ فرمت: `/profit 35 | 8 | 5 | etsy`")
        return

    # Platform fees (2024/2025 rates)
    # Etsy: $0.20 listing (≈€0.18), 6.5% transaction, 3%+€0.25 payment processing
    # eBay: 13% final value, 2.9%+€0.30 payment processing
    # Amazon Handmade: 15% referral, no listing fee
    fees = {
        "etsy": {"name": "Etsy", "listing": 0.18, "transaction": 0.065, "payment": 0.03, "payment_fixed": 0.25, "offsite_ads": 0.15},
        "tori": {"name": "Tori.fi", "listing": 0, "transaction": 0, "payment": 0, "payment_fixed": 0, "offsite_ads": 0},
        "amazon_handmade": {"name": "Amazon Handmade", "listing": 0, "transaction": 0.15, "payment": 0, "payment_fixed": 0, "offsite_ads": 0},
        "ebay": {"name": "eBay", "listing": 0, "transaction": 0.13, "payment": 0.029, "payment_fixed": 0.30, "offsite_ads": 0},
    }

    f = fees.get(platform, fees["etsy"])
    listing_fee = f["listing"]
    transaction_fee = sell_price * f["transaction"]
    payment_fee = sell_price * f["payment"] + f["payment_fixed"]
    total_fees = listing_fee + transaction_fee + payment_fee
    total_cost = material_cost + shipping_cost + total_fees
    profit = sell_price - total_cost
    margin = (profit / sell_price * 100) if sell_price > 0 else 0

    emoji = "🟢" if margin >= 50 else "🟡" if margin >= 30 else "🔴"

    await safe_reply(message, f"💵 *ماشین‌حساب سود — {f['name']}:*\n\n"
        "```\n"
        f"💰 قیمت فروش:      €{sell_price:.2f}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧪 مواد اولیه:      €{material_cost:.2f}\n"
        f"🚚 ارسال:           €{shipping_cost:.2f}\n"
        f"🏷 کارمزد لیست:     €{listing_fee:.2f}\n"
        f"💳 کارمزد تراکنش:   €{transaction_fee:.2f}\n"
        f"💳 کارمزد پرداخت:   €{payment_fee:.2f}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 کل هزینه:        €{total_cost:.2f}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ سود خالص:        €{profit:.2f}\n"
        f"{emoji} مارجین:          {margin:.1f}%\n"
        "```\n\n"
        f"{'🟢 عالیه!' if margin >= 50 else '🟡 قابل قبوله — سعی کن مارجین بالای ۵۰٪ باشه' if margin >= 30 else '🔴 مارجین کمه — قیمت رو ببر بالا یا هزینه‌ها رو کم کن'}\n\n"
        "_⚠️ اگر فروش از Etsy Offsite Ads باشه: ۱۵٪ کارمزد اضافه_\n"
        "_برای تحلیل کامل:_ `/profit analyze`")


# ═══════════════════════════════════════════════
# /crm — Customer Relationship Management
# ═══════════════════════════════════════════════

@router.message(Command("crm"))
async def cmd_crm(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/crm")
    user_id = message.from_user.id  # type: ignore[union-attr]

    if not raw:
        # Show CRM dashboard
        from arki_project.database.connection import get_session
        from arki_project.database.models import Customer
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(Customer.owner_id == user_id)
                .order_by(Customer.created_at.desc())
            )
            customers = result.scalars().all()

        total = len(customers)
        total_orders = sum(c.total_orders for c in customers)
        total_revenue = sum(c.total_spent for c in customers)
        vip = [c for c in customers if c.total_orders >= 3]
        new_30d = [c for c in customers
                   if (datetime.now() - c.created_at.replace(tzinfo=None)).days <= 30]

        text = (
            "👥 *مدیریت مشتری — CRM*\n\n"
            f"📊 کل مشتریان: *{total}*\n"
            f"🛒 کل سفارشات: *{total_orders}*\n"
            f"💰 کل درآمد: *€{total_revenue:,}*\n"
            f"⭐ مشتریان VIP (۳+ خرید): *{len(vip)}*\n"
            f"🆕 مشتریان جدید (۳۰ روز): *{len(new_30d)}*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "*دستورات:*\n"
            "➕ `/crm add نام | تلفن | تگ` — افزودن مشتری\n"
            "📋 `/crm list` — لیست مشتریان\n"
            "🔍 `/crm search [نام/تگ]` — جستجو\n"
            "🏷 `/crm tag [شماره] [تگ]` — تگ‌گذاری\n"
            "📝 `/crm note [شماره] [یادداشت]` — افزودن یادداشت\n"
            "🛒 `/crm sale [شماره] [مبلغ €]` — ثبت خرید\n"
            "⭐ `/crm vip` — لیست مشتریان VIP\n"
            "📊 `/crm report` — گزارش هوشمند AI\n"
        )

        if customers:
            text += "\n*آخرین مشتریان:*\n"
            for c in customers[:5]:
                tags = f" [{c.tags}]" if c.tags else ""
                text += f"• `{c.id}` {c.name}{tags} — {c.total_orders} خرید، €{c.total_spent}\n"

        await safe_reply(message, text)
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    from arki_project.database.connection import get_session
    from arki_project.database.models import Customer
    from sqlalchemy import select

    if action == "add":
        # /crm add نام | تلفن | تگ
        fields = [p.strip() for p in args.split("|")]
        name = fields[0] if fields else ""
        phone = fields[1] if len(fields) > 1 else ""
        tags = fields[2] if len(fields) > 2 else ""

        if not name:
            await safe_reply(message, "❌ نام مشتری رو بده:\n`/crm add نام | تلفن | تگ`")
            return

        async with get_session() as session:
            customer = Customer(
                owner_id=user_id, name=name, phone=phone,
                tags=tags, total_orders=0, total_spent=0,
            )
            session.add(customer)
            await session.commit()
            await session.refresh(customer)

        await safe_reply(message,
            "✅ مشتری اضافه شد!\n\n"
            f"🆔 `{customer.id}` | {name}\n"
            f"📞 {phone or '—'} | 🏷 {tags or '—'}")

    elif action == "list":
        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(Customer.owner_id == user_id)
                .order_by(Customer.total_spent.desc())
            )
            customers = result.scalars().all()

        if not customers:
            await safe_reply(message, "📋 هنوز مشتری ثبت نشده.\n`/crm add نام | تلفن | تگ`")
            return

        lines = ["👥 *لیست مشتریان:*\n"]
        for c in customers:
            tags = f" [{c.tags}]" if c.tags else ""
            note_icon = "📝" if c.note else ""
            lines.append(
                f"`{c.id:>3}` | {c.name}{tags} | "
                f"{c.total_orders} خرید | €{c.total_spent} {note_icon}"
            )
        text = "\n".join(lines)
        for chunk in split_for_telegram(text):
            await safe_reply(message, chunk)

    elif action == "search":
        query = args.lower()
        if not query:
            await safe_reply(message, "🔍 `/crm search [نام یا تگ]`")
            return

        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(Customer.owner_id == user_id)
            )
            all_customers = result.scalars().all()

        found = [c for c in all_customers
                 if query in c.name.lower() or query in c.tags.lower()
                 or query in c.note.lower()]

        if not found:
            await safe_reply(message, f"🔍 نتیجه‌ای برای *{args}* پیدا نشد.")
            return

        lines = [f"🔍 *نتایج جستجو: {args}* ({len(found)} نفر)\n"]
        for c in found:
            tags = f" [{c.tags}]" if c.tags else ""
            lines.append(f"`{c.id}` | {c.name}{tags} — €{c.total_spent}")
        await safe_reply(message, "\n".join(lines))

    elif action == "tag":
        # /crm tag 5 VIP
        tag_parts = args.split(maxsplit=1)
        if len(tag_parts) < 2:
            await safe_reply(message, "🏷 `/crm tag [شماره مشتری] [تگ]`")
            return
        try:
            cid = int(tag_parts[0])
        except ValueError:
            await safe_reply(message, "❌ شماره مشتری باید عدد باشه.")
            return

        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(
                    Customer.id == cid, Customer.owner_id == user_id
                )
            )
            customer = result.scalar_one_or_none()
            if not customer:
                await safe_reply(message, f"❌ مشتری #{cid} پیدا نشد.")
                return

            existing = set(customer.tags.split(",")) if customer.tags else set()
            existing.discard("")
            existing.add(tag_parts[1].strip())
            customer.tags = ",".join(sorted(existing))
            await session.commit()

        await safe_reply(message, f"🏷 تگ *{tag_parts[1].strip()}* به {customer.name} اضافه شد.\nتگ‌ها: `{customer.tags}`")

    elif action == "note":
        note_parts = args.split(maxsplit=1)
        if len(note_parts) < 2:
            await safe_reply(message, "📝 `/crm note [شماره مشتری] [یادداشت]`")
            return
        try:
            cid = int(note_parts[0])
        except ValueError:
            await safe_reply(message, "❌ شماره مشتری باید عدد باشه.")
            return

        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(
                    Customer.id == cid, Customer.owner_id == user_id
                )
            )
            customer = result.scalar_one_or_none()
            if not customer:
                await safe_reply(message, f"❌ مشتری #{cid} پیدا نشد.")
                return

            ts = datetime.now().strftime("%m/%d")
            new_note = f"[{ts}] {note_parts[1].strip()}"
            customer.note = f"{customer.note}\n{new_note}" if customer.note else new_note
            await session.commit()

        await safe_reply(message, f"📝 یادداشت برای *{customer.name}* ثبت شد.")

    elif action == "sale":
        sale_parts = args.split(maxsplit=1)
        if len(sale_parts) < 2:
            await safe_reply(message, "🛒 `/crm sale [شماره مشتری] [مبلغ €]`")
            return
        try:
            cid = int(sale_parts[0])
            amount = int(float(sale_parts[1].replace("€", "").strip()))
        except (ValueError, IndexError):
            await safe_reply(message, "❌ فرمت: `/crm sale 5 35`")
            return

        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(
                    Customer.id == cid, Customer.owner_id == user_id
                )
            )
            customer = result.scalar_one_or_none()
            if not customer:
                await safe_reply(message, f"❌ مشتری #{cid} پیدا نشد.")
                return

            customer.total_orders += 1
            customer.total_spent += amount
            await session.commit()

        await safe_reply(message,
            "🛒 خرید ثبت شد!\n\n"
            f"👤 {customer.name}\n"
            f"💰 €{amount} | کل: €{customer.total_spent}\n"
            f"📦 سفارش #{customer.total_orders}")

    elif action == "vip":
        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(Customer.owner_id == user_id)
                .order_by(Customer.total_spent.desc())
            )
            all_c = result.scalars().all()

        vips = [c for c in all_c if c.total_orders >= 3]
        if not vips:
            await safe_reply(message, "⭐ هنوز مشتری VIP نداری.\nمشتری VIP = ۳+ خرید")
            return

        lines = ["⭐ *مشتریان VIP:*\n"]
        for c in vips:
            lines.append(f"🌟 *{c.name}* — {c.total_orders} خرید | €{c.total_spent}")
        await safe_reply(message, "\n".join(lines))

    elif action == "report":
        # AI-powered CRM report
        async with get_session() as session:
            result = await session.execute(
                select(Customer).where(Customer.owner_id == user_id)
            )
            customers = result.scalars().all()

        if not customers:
            await safe_reply(message, "📊 ابتدا مشتری اضافه کن: `/crm add`")
            return

        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        status = await message.answer("📊 دارم گزارش هوشمند CRM تولید می‌کنم...")

        customer_data = "\n".join([
            f"- {c.name}: {c.total_orders} orders, €{c.total_spent}, tags={c.tags or 'none'}"
            for c in customers
        ])

        try:
            body = await _ai(
                message, ai_client, settings,
                system_prompt=(
                    "You are a CRM analytics expert. Analyze customer data and provide "
                    "actionable insights in Persian. Include: customer segmentation (VIP, "
                    "regular, at-risk), revenue analysis, retention opportunities, "
                    "upsell suggestions, and specific follow-up actions for each segment."
                ),
                user_prompt=(
                    f"Analyze this customer database:\n{customer_data}\n\n"
                    f"Total customers: {len(customers)}\n"
                    f"Total revenue: €{sum(c.total_spent for c in customers)}\n"
                    f"Total orders: {sum(c.total_orders for c in customers)}\n\n"
                    "Provide:\n"
                    "1. 📊 Customer Segmentation (RFM analysis)\n"
                    "2. 🔥 Top customer action items\n"
                    "3. ⚠️ At-risk customers (haven't bought recently)\n"
                    "4. 💡 Upsell/cross-sell opportunities\n"
                    "5. 📧 Follow-up message templates for each segment\n"
                    "6. 📈 Revenue growth recommendations"
                ),
            )
            await safe_delete(status)
            header = f"📊 *گزارش هوشمند CRM — {len(customers)} مشتری:*"
            for chunk in split_for_telegram(f"{header}\n\n{body}"):
                await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await safe_edit_text(status, user_friendly_error(exc))
    else:
        await safe_reply(message,
            "❌ دستور شناخته نشد.\n\n"
            "`/crm` — داشبورد\n"
            "`/crm add نام | تلفن | تگ`\n"
            "`/crm list` | `/crm search` | `/crm vip`\n"
            "`/crm sale شماره مبلغ` | `/crm report`")


# ═══════════════════════════════════════════════
# /dashboard — Sales Dashboard
# ═══════════════════════════════════════════════

@router.message(Command("salesdash"))
async def cmd_dashboard(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    user_id = message.from_user.id  # type: ignore[union-attr]
    chat_id = message.chat.id

    from arki_project.database.connection import get_session
    from arki_project.database.models import Customer, FinanceRecord
    from sqlalchemy import select

    # Gather all data
    async with get_session() as session:
        cust_result = await session.execute(
            select(Customer).where(Customer.owner_id == user_id)
        )
        customers = cust_result.scalars().all()

        fin_result = await session.execute(
            select(FinanceRecord).where(FinanceRecord.user_id == user_id)
        )
        finances = fin_result.scalars().all()

    # CRM stats
    total_customers = len(customers)
    total_orders = sum(c.total_orders for c in customers)
    total_revenue = sum(c.total_spent for c in customers)
    avg_order = total_revenue / total_orders if total_orders else 0
    vip_count = sum(1 for c in customers if c.total_orders >= 3)
    top_customer = max(customers, key=lambda c: c.total_spent) if customers else None

    # Finance stats
    income = sum(f.amount for f in finances if f.amount > 0)
    expense = sum(abs(f.amount) for f in finances if f.amount < 0)
    profit = income - expense

    # Product stats
    products = store.get_products(chat_id)
    catalog = store.get_catalog(chat_id)
    sales_data = store.get_sales(chat_id)

    text = (
        "📊 *داشبورد فروش — Sales Dashboard*\n\n"
        "━━━ 👥 مشتریان ━━━\n"
        f"کل: *{total_customers}* | VIP: *{vip_count}*\n"
        f"سفارشات: *{total_orders}* | میانگین: *€{avg_order:.0f}*\n"
    )
    if top_customer:
        text += f"بهترین مشتری: *{top_customer.name}* (€{top_customer.total_spent})\n"

    text += (
        "\n━━━ 💰 مالی ━━━\n"
        f"درآمد: *€{income:,}* | هزینه: *€{expense:,}*\n"
        f"سود: *€{profit:,}*\n"
    )

    text += (
        "\n━━━ 📦 محصولات ━━━\n"
        f"کاتالوگ: *{len(catalog)}* محصول\n"
        f"فروش ثبت‌شده: *{len(sales_data)}*\n"
    )

    text += (
        "\n━━━ ⚡ اقدامات سریع ━━━\n"
        "📋 `/crm list` — لیست مشتریان\n"
        "📊 `/crm report` — گزارش AI\n"
        "📈 `/forecast` — پیش‌بینی فروش\n"
        "🎯 `/funnel` — طراحی فانل\n"
        "💡 `/upsell` — پیشنهاد upsell\n"
    )

    await safe_reply(message, text)


# ═══════════════════════════════════════
# /pipeline — Sales Pipeline Manager
# ═══════════════════════════════════════

@router.message(Command("pipeline"))
async def cmd_pipeline(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Visual sales pipeline with stage tracking."""
    raw = extract_args(message.text or "", "/pipeline")
    user_id = message.from_user.id  # type: ignore[union-attr]

    if not raw or raw == "help":
        await safe_reply(message, "📈 *پایپلاین فروش — مدیریت مراحل:*\n\n"
            "*دستورات:*\n"
            "`/pipeline add [نام مشتری] | [محصول] | [مبلغ]` — افزودن دیل\n"
            "`/pipeline view` — نمایش پایپلاین\n"
            "`/pipeline move [شماره] | [مرحله]` — جابجایی\n"
            "`/pipeline won [شماره]` — تبدیل به فروش\n"
            "`/pipeline lost [شماره]` — از دست رفته\n"
            "`/pipeline analyze` — تحلیل AI پایپلاین\n\n"
            "*مراحل:*\n"
            "  🔵 `lead` — سرنخ اولیه\n"
            "  🟡 `contact` — تماس گرفته شد\n"
            "  🟠 `proposal` — پیشنهاد ارسال شد\n"
            "  🔴 `negotiation` — مذاکره\n"
            "  🟢 `won` — فروش موفق ✅\n"
            "  ⚫ `lost` — از دست رفته ❌")
        return

    cmd = raw.split(maxsplit=1)
    action = cmd[0].lower()
    rest = cmd[1] if len(cmd) > 1 else ""

    # Get pipeline from KV store
    pipeline = store.get_kv(message.chat.id, "pipeline")
    if not pipeline:
        pipeline = {"deals": [], "next_id": 1}

    stage_emojis = {
        "lead": "🔵", "contact": "🟡", "proposal": "🟠",
        "negotiation": "🔴", "won": "🟢", "lost": "⚫",
    }

    if action == "add":
        parts = [p.strip() for p in rest.split("|")]
        if not parts or not parts[0]:
            await safe_reply(message, "❌ `/pipeline add نام | محصول | مبلغ`")
            return
        deal = {
            "id": pipeline["next_id"],
            "name": parts[0],
            "product": parts[1] if len(parts) > 1 else "",
            "amount": parts[2] if len(parts) > 2 else "0",
            "stage": "lead",
        }
        pipeline["deals"].append(deal)
        pipeline["next_id"] += 1
        await store.set_kv(message.chat.id, "pipeline", pipeline)
        await safe_reply(message,
            f"✅ دیل #{deal['id']} اضافه شد!\n\n"
            f"👤 *{deal['name']}*\n"
            f"📦 {deal['product']}\n"
            f"💰 {deal['amount']}\n"
            "🔵 مرحله: lead")
        return

    if action == "view":
        if not pipeline["deals"]:
            await safe_reply(message, "📈 پایپلاین خالیه!\n`/pipeline add نام | محصول | مبلغ`")
            return

        text = "📈 *پایپلاین فروش:*\n\n"
        for stage in ["lead", "contact", "proposal", "negotiation", "won", "lost"]:
            deals_in_stage = [d for d in pipeline["deals"] if d["stage"] == stage]
            if deals_in_stage:
                emoji = stage_emojis.get(stage, "⚪")
                text += f"━━━ {emoji} *{stage.upper()}* ({len(deals_in_stage)}) ━━━\n"
                for d in deals_in_stage:
                    text += f"  #{d['id']} {d['name']} — {d['product']} (💰{d['amount']})\n"
                text += "\n"

        total = sum(float(d.get("amount", "0").replace(",", "").replace("€", ""))
                     for d in pipeline["deals"] if d["stage"] not in ("lost",))
        won = sum(float(d.get("amount", "0").replace(",", "").replace("€", ""))
                   for d in pipeline["deals"] if d["stage"] == "won")
        text += f"💰 *ارزش کل:* €{total:,.0f} | ✅ *فروش موفق:* €{won:,.0f}"

        for chunk in split_for_telegram(text):
            await safe_reply(message, chunk)
        return

    if action == "move":
        parts = [p.strip() for p in rest.split("|")]
        if len(parts) < 2:
            await safe_reply(message, "❌ `/pipeline move شماره | مرحله`")
            return
        try:
            deal_id = int(parts[0])
        except ValueError:
            await safe_reply(message, "❌ شماره دیل نامعتبر")
            return
        new_stage = parts[1].lower()
        if new_stage not in stage_emojis:
            await safe_reply(message, f"❌ مرحله نامعتبر. انتخاب کن: {', '.join(stage_emojis.keys())}")
            return
        for d in pipeline["deals"]:
            if d["id"] == deal_id:
                old = d["stage"]
                d["stage"] = new_stage
                await store.set_kv(message.chat.id, "pipeline", pipeline)
                await safe_reply(message,
                    f"✅ دیل #{deal_id} جابجا شد!\n"
                    f"{stage_emojis[old]} {old} → {stage_emojis[new_stage]} {new_stage}")
                return
        await safe_reply(message, f"❌ دیل #{deal_id} پیدا نشد")
        return

    if action in ("won", "lost"):
        try:
            deal_id = int(rest.strip())
        except ValueError:
            await safe_reply(message, f"❌ `/pipeline {action} شماره`")
            return
        for d in pipeline["deals"]:
            if d["id"] == deal_id:
                d["stage"] = action
                await store.set_kv(message.chat.id, "pipeline", pipeline)
                emoji = "🎉" if action == "won" else "😔"
                await safe_reply(message,
                    f"{emoji} دیل #{deal_id} — *{d['name']}* → *{action.upper()}*")
                return
        await safe_reply(message, f"❌ دیل #{deal_id} پیدا نشد")
        return

    if action == "analyze":
        if not pipeline["deals"]:
            await safe_reply(message, "📈 پایپلاین خالیه!")
            return
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        try:
            cfg = await ai_client.get_user_config(user_id)
            mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)
            deals_txt = "\n".join(
                f"#{d['id']} {d['name']} | {d['product']} | €{d['amount']} | stage: {d['stage']}"
                for d in pipeline["deals"]
            )
            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content": (
                        "You are a sales analyst. Analyze this pipeline in Persian. "
                        "Give: conversion rate estimate, bottleneck identification, "
                        "recommended actions for each deal, revenue forecast, "
                        "and priority ranking."
                    )},
                    {"role": "user", "content": f"Pipeline deals:\n{deals_txt}"},
                ],
                model_key=mk, temperature=0.7, max_tokens=32768,
            )
            for chunk in split_for_telegram(f"📈 *تحلیل پایپلاین:*\n\n{body}"):
                await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(user_friendly_error(exc))
        return

    await safe_reply(message, "❌ دستور نامعتبر. `/pipeline help`")


# ═══════════════════════════════════════
# /leadscoring — AI Lead Scoring
# ═══════════════════════════════════════

@router.message(Command("leadscoring"))
async def cmd_leadscoring(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """AI-powered lead scoring for CRM contacts."""
    raw = extract_args(message.text or "", "/leadscoring")

    if not raw:
        await safe_reply(message, "🎯 *امتیازدهی سرنخ — Lead Scoring:*\n\n"
            "`/leadscoring [اطلاعات مشتری]`\n\n"
            "*مثال:*\n"
            "`/leadscoring مریم | ۳ بار سفارش داده | شمع لوکس | بودجه بالا`\n"
            "`/leadscoring Sara | asked about bulk orders | from Etsy`\n"
            "`/leadscoring auto` — امتیازدهی خودکار تمام مشتریان CRM\n\n"
            "AI امتیاز ۰-۱۰۰ + اولویت + اقدام پیشنهادی می‌ده!")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        if raw.lower().strip() == "auto":
            # Score all CRM contacts
            from arki_project.database.connection import get_session
            from arki_project.database.models import Customer
            from sqlalchemy import select

            async with get_session() as session:
                result = await session.execute(
                    select(Customer).where(
                        Customer.owner_id == message.from_user.id
                    ).limit(20)
                )
                customers = result.scalars().all()

            if not customers:
                await safe_reply(message, "📭 هنوز مشتری‌ای در CRM نیست.\n`/crm add نام | شماره`")
                return

            cust_txt = "\n".join(
                f"#{c.id} {c.name} | phone: {c.phone} | tags: {c.tags} | "
                f"orders: {c.total_orders} | spent: €{c.total_spent} | notes: {c.note}"
                for c in customers
            )
            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content": (
                        "You are a lead scoring AI. Score each customer 0-100 based on "
                        "their purchase history, engagement, and potential. "
                        "Write in Persian. For each customer give:\n"
                        "- Score (0-100) with color: 🟢 hot (80+), 🟡 warm (50-79), 🔴 cold (<50)\n"
                        "- Priority level (بالا/متوسط/پایین)\n"
                        "- Recommended action (1 specific sentence)\n"
                        "- Revenue potential estimate\n"
                        "Sort by score descending."
                    )},
                    {"role": "user", "content": f"Score these customers:\n{cust_txt}"},
                ],
                model_key=mk, temperature=0.6, max_tokens=16384,
            )
        else:
            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content": (
                        "You are a lead scoring AI expert. Analyze this lead and give:\n"
                        "- Score (0-100) with explanation\n"
                        "- 🟢 Hot / 🟡 Warm / 🔴 Cold classification\n"
                        "- Purchase probability %\n"
                        "- Recommended approach strategy\n"
                        "- Suggested follow-up message template\n"
                        "- Revenue potential estimate\n"
                        "Write in Persian. Be specific and actionable."
                    )},
                    {"role": "user", "content": f"Score this lead: {raw}"},
                ],
                model_key=mk, temperature=0.7, max_tokens=32768,
            )

        for chunk in split_for_telegram(f"🎯 *امتیازدهی سرنخ:*\n\n{body}"):
            await safe_reply(message, chunk)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════
# /pricewatch — Competitor Price Monitoring
# ═══════════════════════════════════════

@router.message(Command("pricewatch"))
async def cmd_pricewatch(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """AI pricing intelligence — competitor price analysis & recommendations."""
    raw = extract_args(message.text or "", "/pricewatch")

    if not raw:
        await safe_reply(message, "💲 *رصد قیمت رقبا — Price Watch:*\n\n"
            "`/pricewatch [محصول] | [قیمت فعلی شما]`\n\n"
            "*مثال:*\n"
            "`/pricewatch شمع سویا بتنی | €25`\n"
            "`/pricewatch handmade candle | 35`\n\n"
            "AI تحلیل می‌کنه:\n"
            "📊 محدوده قیمت رقبا\n"
            "🎯 قیمت بهینه پیشنهادی\n"
            "📈 استراتژی قیمت‌گذاری\n"
            "💡 تاکتیک‌های افزایش ارزش درک‌شده")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    current_price = parts[1] if len(parts) > 1 else "unknown"

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        bctx = brand_ctx(message.chat.id)
        body = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": (
                    "You are a pricing strategist for artisan/handmade products. "
                    "Analyze competitor pricing on platforms like Etsy, Amazon Handmade, "
                    "Tori.fi, and Instagram shops. Write in Persian. Give:\n"
                    "1. Estimated competitor price range (min/avg/max)\n"
                    "2. Your recommended price with justification\n"
                    "3. Price positioning strategy (premium/mid/budget)\n"
                    "4. Bundle pricing suggestions\n"
                    "5. Discount strategy (when/how much)\n"
                    "6. Value-add tactics to justify higher price\n"
                    "7. Seasonal pricing adjustments\n"
                    "Be specific with numbers and percentages."
                )},
                {"role": "user", "content": (
                    f"Product: {product}\n"
                    f"Current price: {current_price}\n"
                    f"{'Brand: ' + bctx if bctx else ''}"
                )},
            ],
            model_key=mk, temperature=0.7, max_tokens=32768,
        )

        for chunk in split_for_telegram(f"💲 *رصد قیمت — {product}:*\n\n{body}"):
            await safe_reply(message, chunk)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


