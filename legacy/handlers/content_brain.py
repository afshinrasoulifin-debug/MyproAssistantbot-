
from __future__ import annotations
"""
tg_bot/handlers/content_brain.py
─────────────────────────────────
🧠 Content Intelligence Engine — the *brain* behind content creation.

Goes beyond generation into intelligence: optimization, trend analysis,
strategic planning, and audience psychology.

Every command is:
- Inline-keyboard driven (rich options)
- Context-aware (brand, products, sales data)
- Candle/decor niche specialized
- Multi-language (EN/FI)
- Meticulous in detail

Commands:
  /optimize    — AI rewrites any caption for max engagement
  /trending    — What's trending in your niche RIGHT NOW
  /contentai   — Smart AI advisor: what content to create next
  /aesthetic   — Brand aesthetic guide & mood board
  /series      — Themed content series planner
  /rewrite     — Adapt content across platforms/tones
  /hook        — 20 scroll-stopping hooks for Reels/TikTok
  /carousel    — Instagram carousel: 10-slide script
  /cta         — CTA optimizer: test & perfect calls-to-action
  /contentaudit — Audit content strategy: gaps, wins, fixes
"""


import logging

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
from arki_project.handlers.shared import brand_ctx, products_ctx
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

router = Router(name="content_brain")

# ── helpers ──







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
    store_result(int(uid) if uid.isdigit() else 0, user[:300], result[:500] if result else "", "content_brain", duration_s=_t.time()-_t0)
    return result


_SYSTEM_CONTENT = (
    "You are the WORLD'S #1 content strategist and marketing genius with unlimited capabilities. "
    "brands in the home decor & candle niche, with deep expertise in the Nordic market. "
    "You know Instagram's 2024/2025 algorithm (Reels distribution, carousel engagement boost, "
    "Stories retention, hashtag Explore ranking), TikTok's For You algorithm (completion rate, "
    "shares, saves), Pinterest visual search SEO, and Etsy listing quality score. "
    "You write natively in English AND Finnish (Suomi). "
    "You understand Scandinavian hygge aesthetic, Nordic minimalism, and what resonates "
    "with Finnish/European consumers. "
    "You are obsessed with engagement metrics, scroll-stopping hooks, and conversion rate. "
    "Write strategic analysis in Persian. Captions, hashtags, and listings in English + Finnish. "
    "Be meticulous, structured, and brutally actionable — no fluff."
)


# ═══════════════════════════════════════
# /optimize — AI Caption Optimizer
# ═══════════════════════════════════════

@router.message(Command("optimize"))
async def cmd_optimize(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/optimize")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📈 بیشترین انگیجمنت", callback_data="opt:engagement"),
                InlineKeyboardButton(text="🛒 بیشترین فروش", callback_data="opt:sales"),
            ],
            [
                InlineKeyboardButton(text="💬 بیشترین کامنت", callback_data="opt:comments"),
                InlineKeyboardButton(text="💾 بیشترین سیو", callback_data="opt:saves"),
            ],
            [
                InlineKeyboardButton(text="🔄 بیشترین شیر", callback_data="opt:shares"),
                InlineKeyboardButton(text="👥 بیشترین فالوور", callback_data="opt:followers"),
            ],
        ])
        await safe_reply(message, "🧠 *آپتیمایزر کپشن:*\n\n"
            "`/optimize [کپشن فعلیت رو بنویس]`\n\n"
            "من با AI تحلیل می‌کنم و *۵ نسخه بهینه‌شده* می‌دم:\n"
            "• Hook قوی‌تر\n"
            "• CTA بهتر\n"
            "• هشتگ استراتژیک\n"
            "• فرمت بهینه برای الگوریتم\n\n"
            "_یا هدف رو انتخاب کن:_",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_CONTENT,
        user=(
            "OPTIMIZE this Instagram caption for MAXIMUM ENGAGEMENT.\n\n"
            f"Original caption:\n\"\"\"\n{raw}\n\"\"\"\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{brand_ctx(message.chat.id)}\n"
            "Provide EXACTLY:\n\n"
            "📊 *ANALYSIS* of the original (score 1-10 for: hook, emotional pull, CTA, "
            "hashtag strategy, readability, algorithm-friendliness)\n\n"
            "✍️ *5 OPTIMIZED VERSIONS:*\n"
            "1. 🔥 Maximum Engagement (likes+comments+saves)\n"
            "2. 🛒 Sales-Focused (drives purchases)\n"
            "3. 💬 Comment Magnet (questions, debates, polls)\n"
            "4. 💾 Save-Worthy (educational/inspirational)\n"
            "5. 🔄 Share-Bait (relatable, viral potential)\n\n"
            "For EACH version:\n"
            "- The full caption (EN)\n"
            "- Finnish version (FI)\n"
            "- 15 strategic hashtags\n"
            "- Best posting time (Helsinki)\n"
            "- Expected engagement boost %\n\n"
            "🎯 *WINNER RECOMMENDATION:* Which version & why"
        ),
    )

    for chunk in split_for_telegram(f"🧠 *کپشن بهینه‌شده:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("opt:"))
async def cb_optimize_goal(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        goals = {
            "engagement": "انگیجمنت", "sales": "فروش", "comments": "کامنت",
            "saves": "سیو", "shares": "شیر", "followers": "فالوور",
        }
        goal = callback.data.split(":")[1]
        await safe_reply(callback.message, "✍️ کپشن فعلیت رو بنویس بعد از `/optimize`:\n\n"
            "`/optimize [کپشنت اینجا]`\n\n"
            f"_هدف: بیشترین {goals.get(goal, '')}_ 🎯")

    except Exception as exc:
        logger.error("cb_optimize_goal error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /trending — Niche Trend Analysis
# ═══════════════════════════════════════

@router.message(Command("trending"))
async def cmd_trending(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/trending")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🕯 شمع و دکور", callback_data="trend:candles"),
                InlineKeyboardButton(text="📸 اینستاگرام", callback_data="trend:instagram"),
            ],
            [
                InlineKeyboardButton(text="🎵 تیک‌تاک", callback_data="trend:tiktok"),
                InlineKeyboardButton(text="📌 پینترست", callback_data="trend:pinterest"),
            ],
            [
                InlineKeyboardButton(text="🛒 Etsy", callback_data="trend:etsy"),
                InlineKeyboardButton(text="🇫🇮 فنلاند", callback_data="trend:finland"),
            ],
            [
                InlineKeyboardButton(text="🌍 همه!", callback_data="trend:all"),
            ],
        ])
        await safe_reply(message, "📈 *ترند آنالایزر:*\n\n"
            "کدوم حوزه رو تحلیل کنم?\n"
            "_یا:_ `/trending [موضوع]`",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_CONTENT,
        user=(
            f"Analyze CURRENT TRENDS for: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{brand_ctx(message.chat.id)}\n\n"
            "Provide EXACTLY:\n\n"
            "🔥 *TOP 10 TRENDING TOPICS* in this niche right now:\n"
            "For each: topic, why it's trending, how to use it, example content idea\n\n"
            "📱 *TRENDING FORMATS:*\n"
            "- Instagram: trending Reel formats, audio trends, carousel styles\n"
            "- TikTok: trending sounds, challenges, formats\n"
            "- Pinterest: trending pin styles, popular searches\n\n"
            "🏷 *TRENDING HASHTAGS:* 30 hashtags sorted by momentum (↑ rising fast)\n\n"
            "🎨 *TRENDING AESTHETICS:*\n"
            "Colors, textures, photography styles that are hot right now\n\n"
            "📅 *UPCOMING OPPORTUNITIES:*\n"
            "Events, holidays, seasons to prepare for in the next 30 days\n\n"
            "💡 *5 CONTENT IDEAS* you should create THIS WEEK based on these trends\n\n"
            "Write in Persian. Be specific and actionable."
        ),
    )

    for chunk in split_for_telegram(f"📈 *ترندهای {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("trend:"))
async def cb_trending(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("📈 در حال تحلیل ترندها...")
        topic = callback.data.split(":")[1]
        topics = {
            "candles": "handmade candles, home decor, interior design",
            "instagram": "Instagram content trends for artisan brands",
            "tiktok": "TikTok trends for small businesses & handmade",
            "pinterest": "Pinterest trends for home decor & candles",
            "etsy": "Etsy search trends & bestselling candle keywords",
            "finland": "Finland market trends, Scandinavian design, Nordic lifestyle",
            "all": "ALL platforms + candles + Finland + home decor + artisan",
        }
        fake_msg = callback.message.model_copy(
            update={"text": f"/trending {topics.get(topic, topic)}", "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_trending(fake_msg, ai_client, settings)

    except Exception as exc:
        logger.error("cb_trending error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /contentai — Smart Content Advisor
# ═══════════════════════════════════════

@router.message(Command("contentai"))
async def cmd_contentai(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_CONTENT,
        user=(
            "Act as my personal CONTENT STRATEGIST.\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n\n"
            "Based on my brand, products, and current market:\n\n"
            "🎯 *CONTENT STRATEGY BRIEF:*\n"
            "- Content pillars (4-5 themes I should always create around)\n"
            "- Content mix ratio (% educational / entertaining / sales / community)\n"
            "- Posting frequency recommendation per platform\n\n"
            "📱 *THIS WEEK — 7 SPECIFIC CONTENT IDEAS:*\n"
            "For each:\n"
            "- Platform (IG Post/Reel/Story, TikTok, Pinterest, Etsy listing refresh)\n"
            "- Content type (tutorial, behind-the-scenes, product showcase, etc.)\n"
            "- Exact concept description\n"
            "- Hook/first line\n"
            "- Best day & time to post\n"
            "- Expected performance (high/medium engagement)\n"
            "- Difficulty to produce (easy/medium/hard)\n\n"
            "📊 *CONTENT GAPS:*\n"
            "What content types are MISSING that could boost growth?\n\n"
            "🏆 *QUICK WINS:*\n"
            "3 easy content pieces you can create in under 15 minutes each\n\n"
            "Write in Persian. Be extremely specific — no generic advice."
        ),
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 برنامه هفتگی", callback_data="cai:weekly"),
            InlineKeyboardButton(text="📅 برنامه ماهانه", callback_data="cai:monthly"),
        ],
        [
            InlineKeyboardButton(text="🔥 ایده‌های وایرال", callback_data="cai:viral"),
            InlineKeyboardButton(text="📸 ایده‌های آسان", callback_data="cai:easy"),
        ],
    ])

    for chunk in split_for_telegram(f"🧠 *مشاور هوشمند محتوا:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)
    await message.answer("⬇️ ادامه:", reply_markup=kb)


@router.callback_query(F.data.startswith("cai:"))
async def cb_contentai(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    await callback.answer("⏳ ...")
    cat = callback.data.split(":")[1]
    prompts = {
        "weekly": "Create a detailed 7-day content calendar with EXACT posts for each day",
        "monthly": "Create a 30-day content calendar organized by weeks & themes",
        "viral": "Give me 10 VIRAL content ideas with full scripts for Reels/TikTok",
        "easy": "Give me 10 EASY content ideas I can create in under 15 minutes each",
    }
    await callback.message.bot.send_chat_action(
        chat_id=callback.message.chat.id, action=ChatAction.TYPING,
    )
    body = await _ai(
        callback.message, ai_client, settings,
        system=_SYSTEM_CONTENT,
        user=(
            f"{prompts.get(cat, 'Content ideas')}\n\n"
            f"{brand_ctx(callback.message.chat.id)}\n"
            f"{products_ctx(callback.message.chat.id)}\n"
            "Write in Persian. Be extremely specific."
        ),
    )
    for chunk in split_for_telegram(body):
        try:
            await safe_reply(callback.message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await callback.message.answer(chunk)


# ═══════════════════════════════════════
# /aesthetic — Brand Aesthetic Guide
# ═══════════════════════════════════════

@router.message(Command("aesthetic"))
async def cmd_aesthetic(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤍 مینیمال اسکاندیناوی", callback_data="aes:minimal"),
            InlineKeyboardButton(text="🖤 دارک و مودی", callback_data="aes:dark"),
        ],
        [
            InlineKeyboardButton(text="🧡 گرم و کوزی", callback_data="aes:cozy"),
            InlineKeyboardButton(text="✨ لاکچری", callback_data="aes:luxury"),
        ],
        [
            InlineKeyboardButton(text="🌿 طبیعی ارگانیک", callback_data="aes:organic"),
            InlineKeyboardButton(text="🎨 کامل (همه)", callback_data="aes:complete"),
        ],
    ])

    raw = extract_args(message.text or "", "/aesthetic")
    if not raw:
        await safe_reply(message, "🎨 *راهنمای زیبایی‌شناسی برند:*\n\n"
            "یه استایل انتخاب کن — من یه *راهنمای کامل بصری* می‌سازم:\n"
            "• پالت رنگ (HEX codes)\n"
            "• فونت‌های پیشنهادی\n"
            "• سبک عکاسی\n"
            "• فیلترها و تنظیمات ادیت\n"
            "• ترکیب‌بندی\n"
            "• راهنمای فید اینستاگرام\n\n"
            "_یا:_ `/aesthetic [سبک دلخواه]`",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=(
            "You are a top-tier brand designer and visual identity consultant. "
            "You specialize in artisan/handmade brands with Scandinavian aesthetics. "
            "You know color theory, typography, photography composition, and Instagram grid design. "
            "Write in Persian with technical terms in English."
        ),
        user=(
            f"Create a COMPLETE BRAND AESTHETIC GUIDE for style: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"Niche: {brand_ctx(message.chat.id)}\n"
            "🎨 *COLOR PALETTE:*\n"
            "- Primary color (HEX + name)\n"
            "- Secondary color (HEX + name)\n"
            "- Accent color (HEX + name)\n"
            "- Neutral 1 & 2 (HEX)\n"
            "- Background color (HEX)\n"
            "- Text color (HEX)\n"
            "- Color usage rules (which for what)\n\n"
            "🔤 *TYPOGRAPHY:*\n"
            "- Heading font (free Google Font)\n"
            "- Body font\n"
            "- Accent font\n"
            "- Font pairing rules\n\n"
            "📸 *PHOTOGRAPHY STYLE:*\n"
            "- Lighting (natural/studio/moody)\n"
            "- Backgrounds & surfaces\n"
            "- Props to use & avoid\n"
            "- Camera angle guide\n"
            "- Composition rules\n"
            "- DO's and DON'Ts (5 each)\n\n"
            "📱 *INSTAGRAM FEED DESIGN:*\n"
            "- Grid pattern (checkerboard/row/column)\n"
            "- Post type rotation\n"
            "- Story highlight cover style\n"
            "- Reel cover aesthetic\n\n"
            "🖼 *EDITING PRESETS:*\n"
            "- Lightroom sliders (temperature, tint, exposure, etc.)\n"
            "- VSCO filter recommendation\n"
            "- Phone editing app settings\n\n"
            "📐 *VISUAL RULES:*\n"
            "- Logo usage guidelines\n"
            "- Watermark style\n"
            "- Border/no border\n"
            "- Text overlay rules\n\n"
            "Be extremely detailed and practical."
        ),
    )

    for chunk in split_for_telegram(f"🎨 *راهنمای زیبایی‌شناسی — {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("aes:"))
async def cb_aesthetic(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("🎨 در حال طراحی...")
        styles = {
            "minimal": "Minimalist Scandinavian — white, birch, clean lines, soft light",
            "dark": "Dark Moody — black, concrete, dramatic shadows, candlelight",
            "cozy": "Warm & Cozy — amber, wood, blankets, hygge, soft focus",
            "luxury": "Luxury Premium — gold, marble, black, studio lighting",
            "organic": "Natural Organic — green, linen, plants, raw textures",
            "complete": "ALL 5 styles combined — complete multi-mood aesthetic system",
        }
        style = callback.data.split(":")[1]
        fake_msg = callback.message.model_copy(
            update={"text": f"/aesthetic {styles.get(style, style)}", "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_aesthetic(fake_msg, ai_client, settings)

    except Exception as exc:
        logger.error("cb_aesthetic error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /series — Themed Content Series Planner
# ═══════════════════════════════════════

@router.message(Command("series"))
async def cmd_series(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/series")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🕯 پشت صحنه تولید", callback_data="ser:bts"),
                InlineKeyboardButton(text="🏡 دکور خونه", callback_data="ser:decor"),
            ],
            [
                InlineKeyboardButton(text="🌿 سبک زندگی هوگه", callback_data="ser:hygge"),
                InlineKeyboardButton(text="📚 آموزش شمع‌سازی", callback_data="ser:edu"),
            ],
            [
                InlineKeyboardButton(text="🎁 گیفت گاید", callback_data="ser:gifts"),
                InlineKeyboardButton(text="🇫🇮 فنلاند+نوردیک", callback_data="ser:nordic"),
            ],
            [
                InlineKeyboardButton(text="❤️ داستان مشتری", callback_data="ser:customer"),
                InlineKeyboardButton(text="🔥 چالنج", callback_data="ser:challenge"),
            ],
        ])
        await safe_reply(message, "📚 *برنامه‌ریز سری محتوا:*\n\n"
            "یه سری محتوای منسجم ۷ روزه طراحی می‌کنم:\n"
            "• تم مشخص\n"
            "• ۷ پست مرتبط\n"
            "• هر پست با کپشن + هشتگ\n"
            "• استوری‌های روزانه\n"
            "• یه ریلز حرفه‌ای\n\n"
            "_انتخاب کن یا:_ `/series [تم دلخواه]`",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_CONTENT,
        user=(
            f"Design a THEMED CONTENT SERIES for: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{products_ctx(message.chat.id)}\n\n"
            "Create a 7-DAY CONTENT SERIES:\n\n"
            "📌 *SERIES CONCEPT:*\n"
            "- Theme name (catchy, branded)\n"
            "- Series hashtag\n"
            "- Target audience\n"
            "- Goal (awareness/engagement/sales)\n\n"
            "📅 *DAY-BY-DAY PLAN:*\n"
            "For each of 7 days:\n"
            "- Day title & theme angle\n"
            "- Content type (Post/Reel/Carousel/Story)\n"
            "- Full caption (EN)\n"
            "- Full caption (FI)\n"
            "- Hashtags (15)\n"
            "- Story companion content (3 slides)\n"
            "- Photo/video direction\n"
            "- Best posting time\n\n"
            "🎬 *REEL SCRIPT:*\n"
            "One Reel script for this series (30-60 sec), second-by-second\n\n"
            "📈 *SERIES PROMOTION PLAN:*\n"
            "- How to tease it before launch\n"
            "- How to promote during\n"
            "- How to repurpose after\n\n"
            "Write in Persian with captions in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"📚 *سری محتوا — {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("ser:"))
async def cb_series(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("📚 طراحی سری...")
        themes = {
            "bts": "Behind The Scenes: Making process, workshop tour, raw materials",
            "decor": "Home Decor Inspiration: styling candles in different rooms & settings",
            "hygge": "Hygge Lifestyle: Finnish cozy living, warmth, mindfulness with candles",
            "edu": "Candle Education: wax types, wick science, scent profiles, burn tips",
            "gifts": "Gift Guide: candles as gifts, packaging ideas, occasions, combos",
            "nordic": "Nordic Living: Finnish seasons, Scandinavian design, nature inspiration",
            "customer": "Customer Stories: reviews, unboxing, how customers use products",
            "challenge": "7-Day Challenge: interactive challenge engaging followers each day",
        }
        theme = callback.data.split(":")[1]
        fake_msg = callback.message.model_copy(
            update={"text": f"/series {themes.get(theme, theme)}", "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_series(fake_msg, ai_client, settings)

    except Exception as exc:
        logger.error("cb_series error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /rewrite — Cross-Platform Content Adapter
# ═══════════════════════════════════════

@router.message(Command("rewrite"))
async def cmd_rewrite(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/rewrite")

    if not raw:
        await safe_reply(message, "🔄 *بازنویسی محتوا:*\n\n"
            "یه محتوا بده — من برای *۸ پلتفرم مختلف* بازنویسی می‌کنم:\n\n"
            "`/rewrite [متن کپشن یا محتوات]`\n\n"
            "خروجی:\n"
            "📸 Instagram Post\n"
            "🎬 Instagram Reel script\n"
            "📖 Instagram Story (5 slides)\n"
            "🎵 TikTok script\n"
            "📌 Pinterest pin description\n"
            "🛒 Etsy listing refresh\n"
            "📘 Facebook post\n"
            "🐦 Twitter/X thread\n\n"
            "_هر نسخه با فرمت و لحن مخصوص همون پلتفرم!_")
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_CONTENT,
        user=(
            "REWRITE this content for 8 DIFFERENT PLATFORMS:\n\n"
            f"Original:\n\"\"\"\n{raw}\n\"\"\"\n\n"
            f"{brand_ctx(message.chat.id)}\n\n"
            "For EACH platform, create a COMPLETE, READY-TO-POST version:\n\n"
            "📸 *Instagram Post:* 2200 chars max, storytelling, CTA, 30 hashtags EN+FI\n"
            "🎬 *Instagram Reel:* 30-sec script (hook + content + CTA), trending audio suggestion\n"
            "📖 *Instagram Story:* 5 slides with text overlays, poll/question sticker ideas\n"
            "🎵 *TikTok:* 15-60 sec script, trending format, hook in first 1 sec\n"
            "📌 *Pinterest:* SEO-optimized pin title + description, 10 keywords\n"
            "🛒 *Etsy:* Listing refresh with 13 tags, SEO title, 3 description paragraphs\n"
            "📘 *Facebook:* Community-focused, local angle, share-worthy\n"
            "🐦 *X/Twitter:* Thread of 5 tweets, hook tweet, engagement tweet\n\n"
            "Each in ENGLISH + FINNISH. Write in Persian for explanations."
        ),
    )

    for chunk in split_for_telegram(f"🔄 *بازنویسی ۸ پلتفرم:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


# ═══════════════════════════════════════
# /hook — Scroll-Stopping Hooks
# ═══════════════════════════════════════

@router.message(Command("hook"))
async def cmd_hook(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/hook")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Reels/TikTok", callback_data="hook:reels"),
                InlineKeyboardButton(text="✍️ Caption", callback_data="hook:caption"),
            ],
            [
                InlineKeyboardButton(text="📧 Email Subject", callback_data="hook:email"),
                InlineKeyboardButton(text="🛒 Ad Copy", callback_data="hook:ads"),
            ],
            [
                InlineKeyboardButton(text="📌 Pin Title", callback_data="hook:pin"),
                InlineKeyboardButton(text="🔥 همه", callback_data="hook:all"),
            ],
        ])
        await safe_reply(message, "🪝 *هوک‌ساز حرفه‌ای:*\n\n"
            "۲۰ هوک *غیرقابل رد شدن* می‌سازم!\n\n"
            "`/hook [محصول یا موضوع]`\n\n"
            "_یا نوع هوک رو انتخاب کن:_",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_CONTENT,
        user=(
            f"Create 20 SCROLL-STOPPING HOOKS for: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n"
            f"{brand_ctx(message.chat.id)}\n"
            "For each hook:\n"
            "- The hook text (EN)\n"
            "- Finnish version (FI)\n"
            "- Psychology trigger (curiosity/fear/desire/social proof/etc)\n"
            "- Best for: (Reel/Caption/Ad/Email/Pin)\n"
            "- Strength: 🔥🔥🔥 (1-5)\n\n"
            "Categories:\n"
            "🎬 5 VIDEO HOOKS (first 1-3 seconds of Reel/TikTok)\n"
            "✍️ 5 CAPTION HOOKS (first line that makes them click 'more')\n"
            "❓ 5 QUESTION HOOKS (curiosity-driven)\n"
            "💣 5 CONTROVERSIAL/BOLD HOOKS (pattern interrupt)\n\n"
            "Write in Persian. Hooks in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"🪝 *۲۰ هوک — {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("hook:"))
async def cb_hook(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        topics = {
            "reels": "Reels/TikTok video hooks",
            "caption": "Instagram caption hooks",
            "email": "Email subject line hooks",
            "ads": "Ad copy hooks",
            "pin": "Pinterest pin title hooks",
            "all": "ALL types of hooks",
        }
        t = callback.data.split(":")[1]
        await safe_reply(callback.message, "✍️ موضوع/محصول بنویس:\n\n"
            "`/hook [محصول]`\n\n"
            f"_نوع: {topics.get(t, t)}_")

    except Exception as exc:
        logger.error("cb_hook error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /carousel — Instagram Carousel Designer
# ═══════════════════════════════════════

@router.message(Command("carousel"))
async def cmd_carousel(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/carousel")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 آموزشی", callback_data="car:edu"),
                InlineKeyboardButton(text="💡 نکات", callback_data="car:tips"),
            ],
            [
                InlineKeyboardButton(text="📖 داستان برند", callback_data="car:story"),
                InlineKeyboardButton(text="🛒 محصول", callback_data="car:product"),
            ],
            [
                InlineKeyboardButton(text="❓ قبل/بعد", callback_data="car:beforeafter"),
                InlineKeyboardButton(text="📊 آمار", callback_data="car:stats"),
            ],
        ])
        await safe_reply(message, "📱 *طراح کاروسل اینستاگرام:*\n\n"
            "۱۰ اسلاید حرفه‌ای طراحی می‌کنم:\n"
            "• متن هر اسلاید\n"
            "• دستور عکس/دیزاین\n"
            "• کپشن + هشتگ\n"
            "• تکنیک سوایپ\n\n"
            "`/carousel [موضوع]`\n"
            "_یا نوع کاروسل انتخاب کن:_",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_CONTENT,
        user=(
            f"Design a 10-SLIDE INSTAGRAM CAROUSEL for: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n\n"
            "For EACH SLIDE (1-10):\n"
            "📌 *Slide number & purpose*\n"
            "✍️ *Headline text* (what to write on the slide — EN)\n"
            "✍️ *Headline text FI*\n"
            "📝 *Body text* (supporting text on slide)\n"
            "🖼 *Visual direction* (photo type, colors, layout)\n"
            "💡 *Design tip* (font size, positioning, effect)\n\n"
            "SLIDE ROLES:\n"
            "1. HOOK slide (stops the scroll)\n"
            "2-3. PROBLEM slides (relatable pain)\n"
            "4-7. VALUE slides (education/solution)\n"
            "8-9. PROOF slides (social proof/results)\n"
            "10. CTA slide (what to do next)\n\n"
            "ALSO provide:\n"
            "✍️ *CAPTION* (EN): 500+ chars, storytelling, CTA\n"
            "✍️ *CAPTION* (FI): Finnish version\n"
            "🏷 *30 HASHTAGS*: 10 popular + 10 niche + 10 Finnish\n"
            "⏰ *Best time to post*\n"
            "💡 *Swiping techniques* to maximize reach\n\n"
            "Write in Persian, slide texts in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"📱 *کاروسل — {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("car:"))
async def cb_carousel(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("📱 طراحی کاروسل...")
        types = {
            "edu": "Educational: How handmade candles are made — from raw materials to finished product",
            "tips": "Tips: 10 tips for decorating your home with candles for hygge atmosphere",
            "story": "Brand Story: Our journey — from first candle to artisan brand in Finland",
            "product": "Product Showcase: features, materials, scents, burn time, care guide",
            "beforeafter": "Before/After: Room transformation with candle styling & decor",
            "stats": "Statistics: Fascinating facts about candles, scents, and wellbeing",
        }
        t = callback.data.split(":")[1]
        fake_msg = callback.message.model_copy(
            update={"text": f"/carousel {types.get(t, t)}", "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_carousel(fake_msg, ai_client, settings)

    except Exception as exc:
        logger.error("cb_carousel error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /cta — CTA Optimizer
# ═══════════════════════════════════════

@router.message(Command("cta"))
async def cmd_cta(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/cta")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 خرید", callback_data="cta:buy"),
                InlineKeyboardButton(text="💬 کامنت", callback_data="cta:comment"),
            ],
            [
                InlineKeyboardButton(text="💾 سیو", callback_data="cta:save"),
                InlineKeyboardButton(text="🔄 شیر", callback_data="cta:share"),
            ],
            [
                InlineKeyboardButton(text="👥 فالو", callback_data="cta:follow"),
                InlineKeyboardButton(text="🔗 لینک کلیک", callback_data="cta:link"),
            ],
            [
                InlineKeyboardButton(text="📧 ایمیل ثبت‌نام", callback_data="cta:email"),
                InlineKeyboardButton(text="🔥 همه", callback_data="cta:all"),
            ],
        ])
        await safe_reply(message, "🎯 *آپتیمایزر CTA:*\n\n"
            "هدفت از CTA چیه? ۱۰ نسخه حرفه‌ای می‌سازم:\n\n"
            "`/cta [هدف یا محصول]`\n"
            "_یا هدف انتخاب کن:_",
            reply_markup=kb)
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    body = await _ai(
        message, ai_client, settings,
        system=_SYSTEM_CONTENT,
        user=(
            f"Create 30 PROFESSIONAL CTAs for: {raw}\n\n"
            f"{brand_ctx(message.chat.id)}\n\n"
            "5 CTAs for each goal:\n"
            "🛒 PURCHASE CTAs: drive immediate sales\n"
            "💬 COMMENT CTAs: spark conversation\n"
            "💾 SAVE CTAs: bookmark-worthy value\n"
            "🔄 SHARE CTAs: make them share with friends\n"
            "👥 FOLLOW CTAs: grow audience\n"
            "🔗 LINK CLICK CTAs: drive traffic to shop\n\n"
            "For each CTA:\n"
            "- English version\n"
            "- Finnish version\n"
            "- Psychology trigger used\n"
            "- Where to use it (Bio/Caption/Story/Reel/Email)\n"
            "- Urgency level (soft/medium/strong)\n\n"
            "Write in Persian. CTAs in EN+FI."
        ),
    )

    for chunk in split_for_telegram(f"🎯 *CTA‌ها — {raw}:*\n\n{body}"):
        try:
            await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(chunk)


@router.callback_query(F.data.startswith("cta:"))
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

    except Exception as exc:
        logger.error("cb_cta error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
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
        except Exception as exc:
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
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)
    except Exception as exc:
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
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)
    except Exception as exc:
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
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


