
from __future__ import annotations
"""
tg_bot/handlers/market.py
─────────────────────────
🛒 Marketplace Automation:

  /listing   — AI listing generator (Etsy/Tori.fi/Instagram — FI+EN+SEO)
  /analyze   — Competitor analysis on Etsy (scrape, pricing, trends)
  /photopro  — Transform simple product photos into professional posters
"""


import asyncio
import logging
import re
import urllib.parse

import httpx
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

# ═══ TITANIUM v29.0 Integration ═══
try:
    from arki_project.utils.titanium.integration import shielded_get, shielded_post, shielded_request
    _TITANIUM_ACTIVE = True
except ImportError:
    _TITANIUM_ACTIVE = False
# ═══════════════════════════════════

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.handlers.shared import brand_ctx, extract_args
from arki_project.utils.safe_send import safe_delete, safe_edit_text, safe_reply
from arki_project.utils.v7_core import (

# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]

    enhance_system_prompt, store_result,
)

logger = logging.getLogger(__name__)
# v9.2: Marketing engine integration
try:
    from arki_project.utils.v7_core import get_marketing_engine
    _marketing = get_marketing_engine()
except Exception as exc:
    logger.error("Error in handler: %s", exc)
    _marketing = None
router = Router(name="market")


# ═══════════════════════════════════════
# /listing — Multilingual Listing Generator
# ═══════════════════════════════════════

@router.message(Command("listing"))
async def cmd_listing(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/listing")

    if not raw:
        await safe_reply(message, "📋 *آگهی‌ساز هوشمند — چند زبانه + SEO:*\n\n"
            "`/listing [نام محصول] | [قیمت €] | [توضیح]`\n\n"
            "*مثال:*\n"
            "`/listing Handmade Concrete Candle | 35 | Soy wax, 40h burn time, minimalist`\n"
            "`/listing شمع بتنی دست‌ساز | 35 | سویا، مینیمال`\n\n"
            "AI خودکار *۴ آگهی بهینه* تولید می‌کنه:\n"
            "🇬🇧 *Etsy* (English + SEO tags)\n"
            "🇫🇮 *Tori.fi* (Finnish)\n"
            "📱 *Instagram* (English + hashtags)\n"
            "📱 *Instagram* (Finnish + hashtags)\n\n"
            "_آماده کپی‌پیست برای هر پلتفرم!_")
        return

    parts = [p.strip() for p in raw.split("|")]
    product = parts[0]
    price = parts[1] if len(parts) > 1 else ""
    extra = parts[2] if len(parts) > 2 else ""

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await message.answer("📋 دارم ۴ آگهی حرفه‌ای + SEO تولید می‌کنم...")

    try:
        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        prompt = (
            "Create 4 professional, SEO-optimized marketplace listings for this product:\n"
            f"Product: {product}\n"
            f"Price: €{price}\n"
            f"Details: {extra}\n"
            f"{brand_ctx(message.chat.id)}\n"
            "Generate ALL 4 listings below:\n\n"
            "═══════════════════════════\n"
            "📌 LISTING 1 — ETSY (English)\n"
            "═══════════════════════════\n"
            "- Title (max 140 chars, keyword-rich for Etsy SEO)\n"
            "- Description (3-4 paragraphs: intro, features, materials, shipping)\n"
            "- 13 Etsy tags (max 20 chars each, long-tail keywords)\n"
            "- Materials list\n"
            "- Shipping note (Ships from Finland, EU)\n\n"
            "═══════════════════════════\n"
            "📌 LISTING 2 — TORI.FI (Finnish)\n"
            "═══════════════════════════\n"
            "- Otsikko (title in Finnish)\n"
            "- Kuvaus (description in Finnish, natural, friendly tone)\n"
            "- Hinta: €\n"
            "- Sijainti: Finland\n"
            "- Toimitustapa\n\n"
            "═══════════════════════════\n"
            "📌 LISTING 3 — INSTAGRAM POST (English)\n"
            "═══════════════════════════\n"
            "- Caption (engaging, storytelling, with CTA)\n"
            "- 30 hashtags (mix of popular + niche: #handmadecandles etc)\n"
            "- Best posting time suggestion\n\n"
            "═══════════════════════════\n"
            "📌 LISTING 4 — INSTAGRAM POST (Finnish)\n"
            "═══════════════════════════\n"
            "- Caption in Finnish (engaging, with CTA)\n"
            "- 20 hashtags (Finnish + international mix)\n\n"
            "Make each listing READY TO COPY-PASTE directly to the platform. "
            "Use emojis in Instagram listings. "
            "Etsy listing must be highly SEO-optimized."
        )

        import time as _t; _t0 = _t.time()
        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": enhance_system_prompt(
                    "You are an expert e-commerce copywriter and SEO specialist. "
                    "You create marketplace listings that rank high and convert well. "
                    "You know Etsy SEO, Finnish market, and Instagram marketing.",
                    user_text=message.text or "", user_id=str(message.from_user.id) if message.from_user else "0")},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.8, max_tokens=16384,
        )

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)

        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:300], answer[:500] if answer else "", "market", duration_s=_t.time()-_t0)
        for chunk in split_for_telegram(f"📋 *آگهی‌های «{product}»:*\n\n{answer}"):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


# ═══════════════════════════════════════
# /analyze — Etsy Competitor Analysis
# ═══════════════════════════════════════

@router.message(Command("analyze"))
async def cmd_analyze(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/analyze")

    if not raw:
        await safe_reply(message, "🔍 *آنالیز رقبا — Etsy & بازار:*\n\n"
            "`/analyze concrete candle`\n"
            "`/analyze soy wax candle minimalist`\n"
            "`/analyze handmade candle holder Finland`\n\n"
            "_AI رقبا رو تحلیل می‌کنه:_\n"
            "📊 قیمت‌گذاری رقبا\n"
            "🏷 تگ‌های پرفروش\n"
            "💡 ایده‌های بهبود\n"
            "📈 ترندها و فرصت‌ها")
        return

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.TYPING,
    )
    status = await message.answer(f"🔍 دارم بازار Etsy رو برای «{raw}» آنالیز می‌کنم...")

    try:
        # Step 1: Scrape Etsy search results
        etsy_data = await _scrape_etsy_search(raw)

        cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

        # Step 2: AI analysis
        prompt = (
            f"I searched Etsy for '{raw}' and found these results:\n\n"
            f"{etsy_data}\n\n"
            "Based on this market data, provide a COMPREHENSIVE competitive analysis:\n\n"
            "📊 *1. PRICE ANALYSIS:*\n"
            "- Price range (min/max/average)\n"
            "- Recommended pricing strategy\n"
            "- Sweet spot price point\n\n"
            "🏷 *2. TOP-PERFORMING TAGS & KEYWORDS:*\n"
            "- Most common tags used by successful listings\n"
            "- Long-tail keywords to target\n"
            "- Recommended Etsy tags (13 tags)\n\n"
            "🏆 *3. WHAT BESTSELLERS DO RIGHT:*\n"
            "- Common features of top listings\n"
            "- Photo style that works\n"
            "- Description patterns\n\n"
            "💡 *4. OPPORTUNITIES & GAPS:*\n"
            "- Underserved niches\n"
            "- Differentiation ideas\n"
            "- Seasonal opportunities\n\n"
            "📈 *5. ACTION PLAN:*\n"
            "- 5 specific steps to compete effectively\n"
            "- Listing optimization tips\n"
            "- Marketing strategy\n\n"
            "Write in a mix of Persian (for the seller) and English (for keywords/tags). "
            "Be specific with numbers and examples."
        )

        answer = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "You are an expert Etsy seller consultant and e-commerce analyst. "
                    "You help sellers optimize their listings and pricing strategy. "
                    "The seller makes handmade concrete/stone candles in Finland. "
                    "Provide actionable, data-driven insights."},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.7, max_tokens=16384,
        )

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)

        header = f"🔍 *آنالیز رقبا — «{raw}»:*\n\n"
        for chunk in split_for_telegram(header + answer):
            try:
                await safe_reply(message, chunk)
            except Exception:
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Analyze failed: %s", exc)
        await safe_edit_text(status, f"❌ خطا: {exc}")


async def _scrape_etsy_search(query: str, max_results: int = 15) -> str:
    """Scrape Etsy search results for competitive analysis."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.etsy.com/search?q={encoded}&ref=search_bar"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        await asyncio.sleep(1.5)  # Rate limit Etsy requests to avoid IP ban
        # v10.1: TITANIUM shielded fetch
        if _TITANIUM_ACTIVE:
            _ti = await shielded_get(url, headers=headers, timeout=60.0)
            html = _ti.text
        else:
            async with httpx.AsyncClient(
                timeout=60.0, follow_redirects=True,
            ) as client:
                resp = await client.get(url, headers=headers)
                html = resp.text

        # Extract listing data from HTML
        listings = []

        # Find prices
        prices = re.findall(r'(?:€|EUR\s*)(\d+[.,]\d{2})', html)
        # Find titles
        titles = re.findall(r'data-listing-card-v2.*?alt="([^"]{10,100})"', html, re.DOTALL)
        if not titles:
            titles = re.findall(r'<h3[^>]*>([^<]{10,100})</h3>', html)
        # Find review counts
        reviews = re.findall(r'(\d+(?:,\d+)?)\s*(?:reviews|sales)', html, re.IGNORECASE)

        # Build report
        result_lines = []
        for i in range(min(max_results, max(len(titles), len(prices)))):
            line = f"#{i+1}:"
            if i < len(titles):
                line += f" Title: {titles[i].strip()}"
            if i < len(prices):
                line += f" | Price: €{prices[i]}"
            if i < len(reviews):
                line += f" | Reviews: {reviews[i]}"
            result_lines.append(line)

        if result_lines:
            return "\n".join(result_lines)

        # Fallback: extract any useful text
        # Clean HTML and get key snippets
        clean = re.sub(r'<[^>]+>', ' ', html)
        clean = re.sub(r'\s+', ' ', clean)

        # Find price patterns
        all_prices = re.findall(r'€\s*(\d+(?:[.,]\d{2})?)', clean)
        if all_prices:
            return (
                f"Found {len(all_prices)} price points on Etsy for '{query}':\n"
                f"Prices: {', '.join(all_prices[:20])}\n"
                "Note: Could not parse individual listing details, "
                "but price data is available for analysis."
            )

        return (
            f"Etsy search for '{query}' returned results but HTML parsing was limited. "
            "Please analyze based on your knowledge of the concrete/handmade candle market "
            "on Etsy, including typical pricing in €15-€60 range, popular tags, and trends."
        )

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        return (
            f"Could not scrape Etsy directly ({exc}). "
            "Please analyze based on your extensive knowledge of the Etsy marketplace "
            "for handmade candles, concrete candle holders, and similar products. "
            f"Search query was: '{query}'. "
            "Include typical pricing, popular tags, and market trends."
        )


# ═══════════════════════════════════════
# /photopro — Product Photo Enhancement
# ═══════════════════════════════════════

@router.message(Command("photopro"))
async def cmd_photopro(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/photopro")

    if not raw and not message.photo:
        await safe_reply(message, "📸 *تبدیل عکس ساده به پوستر حرفه‌ای:*\n\n"
            "`/photopro [توضیح محصول] [استایل]`\n\n"
            "*مثال‌ها:*\n"
            "`/photopro concrete candle dark`\n"
            "`/photopro lavender soy candle cozy`\n"
            "`/photopro stone vessel candle nordic`\n\n"
            "*۸ استایل عکاسی:*\n"
            "🌑 `dark` — تیره دراماتیک (مثل نمونه‌ات!)\n"
            "☀️ `light` — روشن اسکاندیناوی\n"
            "🌿 `natural` — طبیعی، گل خشک\n"
            "✨ `luxury` — لاکچری، مخمل\n"
            "🕯 `cozy` — هیگه، گرم، دنج\n"
            "🇫🇮 `nordic` — مینیمال فنلاندی\n"
            "🪵 `rustic` — روستیک، چوبی\n"
            "📐 `flat` — فلت‌لی، نمای بالا")
        return

    # Build the image generation prompt
    product_desc = raw or "handmade concrete candle"

    # Detect style keywords — candle-specific
    style_prompts = {
        "dark": "dark moody photography, dramatic side lighting, dark walnut wood surface, "
                "deep shadows, warm candlelight glow, concrete saucer underneath, "
                "dried baby's breath flowers, linen fabric, Kinfolk magazine style",
        "light": "bright airy photography, soft natural window light, white marble surface, "
                 "minimalist Scandinavian interior, clean negative space, cotton fabric, "
                 "morning light, Nordic design aesthetic",
        "natural": "natural organic photography, wooden table, dried eucalyptus and lavender, "
                   "linen napkin, warm golden hour sunlight, botanical styling, "
                   "earthy tones, wabi-sabi aesthetic",
        "luxury": "luxury product photography, dark velvet fabric, gold leaf accents, "
                  "soft rim lighting, premium black background, sophisticated shadows, "
                  "high-end cosmetics ad style",
        "cozy": "cozy hygge photography, warm blanket, fairy lights bokeh background, "
                "soft warm tones, reading corner setting, autumn vibes, "
                "cup of coffee nearby, intimate atmosphere",
        "nordic": "Scandinavian design photography, light birch wood, white and grey tones, "
                  "geometric shapes, clean lines, Muuto/Ferm Living style, "
                  "soft diffused northern light, minimalist Finnish interior",
        "rustic": "rustic farmhouse photography, raw wood plank surface, "
                  "dried wildflowers, burlap fabric, vintage brass tray, "
                  "warm window light, artisan workshop feel",
        "flat": "flat lay photography, top-down view, styled arrangement, "
                "concrete background, scattered dried petals, matches, cotton, "
                "Instagram-ready composition, #flatlay aesthetic",
    }

    # Default to dark moody (like the reference image)
    style = "dark"
    for s in style_prompts:
        if s in product_desc.lower():
            style = s
            product_desc = product_desc.lower().replace(s, "").strip()
            break

    full_prompt = (
        f"Professional product photography of {product_desc}, "
        "handmade artisan candle in a textured raw concrete stone vessel, "
        f"natural soy wax, {style_prompts[style]}, "
        "8k resolution, commercial grade, shallow depth of field, "
        "magazine cover quality, beautifully styled with complementary props"
    )

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_PHOTO,
    )
    status = await message.answer("📸 دارم عکس محصول حرفه‌ای می‌سازم... (۲۰-۴۰ ثانیه)")

    try:
        # Use Pollinations Flux for image generation
        encoded_prompt = urllib.parse.quote(full_prompt)
        img_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width=1024&height=1024&model=flux&seed={__import__('os').urandom(4).hex()}"
        )

        # v10.1: Route through TITANIUM
        if _TITANIUM_ACTIVE:
            _resp = await shielded_get(img_url, timeout=90.0, provider_name="pollinations_img")
            if not _resp.success:
                raise ValueError(f"Image generation failed: HTTP {_resp.status_code}")
            img_data = _resp.content
        else:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(img_url)
                if resp.status_code != 200:
                    raise ValueError(f"Image generation failed: HTTP {resp.status_code}")
                img_data = resp.content

        try:
            await safe_delete(status)
        except Exception as e:
            logger.debug("Suppressed: %s", e)

        photo = BufferedInputFile(img_data, filename="product_pro.png")

        style_names = {
            "dark": "🌑 تیره دراماتیک",
            "light": "☀️ روشن مینیمال",
            "natural": "🌿 طبیعی",
            "luxury": "✨ لاکچری",
        }

        # Offer other styles
        desc_short = product_desc[:30]
        other_styles_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌑 Dark", callback_data=f"ppro:dark:{desc_short}"),
                InlineKeyboardButton(text="☀️ Light", callback_data=f"ppro:light:{desc_short}"),
            ],
            [
                InlineKeyboardButton(text="🌿 Natural", callback_data=f"ppro:natural:{desc_short}"),
                InlineKeyboardButton(text="✨ Luxury", callback_data=f"ppro:luxury:{desc_short}"),
            ],
            [
                InlineKeyboardButton(text="🕯 Cozy", callback_data=f"ppro:cozy:{desc_short}"),
                InlineKeyboardButton(text="🇫🇮 Nordic", callback_data=f"ppro:nordic:{desc_short}"),
            ],
            [
                InlineKeyboardButton(text="🪵 Rustic", callback_data=f"ppro:rustic:{desc_short}"),
                InlineKeyboardButton(text="📐 Flat lay", callback_data=f"ppro:flat:{desc_short}"),
            ],
        ])

        await message.answer_photo(
            photo=photo,
            caption=(
                f"📸 *عکس حرفه‌ای — {style_names.get(style, style)}*\n\n"
                f"📝 {product_desc}\n\n"
                "_استایل دیگه می‌خوای؟ 👇_"
            ),
            reply_markup=other_styles_kb,
            parse_mode="Markdown",
        )

    except Exception as exc:
        logger.error("PhotoPro failed: %s", exc)
        try:
            await safe_edit_text(status, f"❌ خطا: {exc}")
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await message.answer(f"❌ {exc}")


@router.callback_query(F.data.startswith("ppro:"))
async def cb_photopro_style(callback: CallbackQuery) -> None:
    await callback.answer("📸 در حال ساخت...")
    parts = callback.data.split(":", 2)  # type: ignore[union-attr]
    style = parts[1]
    product_desc = parts[2] if len(parts) > 2 else "handmade concrete candle"

    style_prompts = {
        "dark": "dark moody photography, dramatic side lighting, dark walnut wood surface, "
                "deep shadows, warm candlelight glow, dried flowers, Kinfolk style",
        "light": "bright airy photography, soft natural window light, white marble, "
                 "minimalist Scandinavian, Nordic design aesthetic",
        "natural": "natural organic photography, wooden table, dried eucalyptus, "
                   "warm golden hour sunlight, earthy tones, wabi-sabi",
        "luxury": "luxury product photography, dark velvet, gold leaf accents, "
                  "soft rim lighting, premium black background",
        "cozy": "cozy hygge photography, warm blanket, fairy lights bokeh, "
                "autumn vibes, cup of coffee nearby",
        "nordic": "Scandinavian design, light birch wood, white grey tones, "
                  "soft diffused northern light, Finnish interior",
        "rustic": "rustic farmhouse, raw wood plank, dried wildflowers, "
                  "burlap fabric, warm window light",
        "flat": "flat lay top-down view, concrete background, scattered dried petals, "
                "matches, cotton, Instagram flatlay",
    }

    try:
        import os
        import urllib.parse as up

        full_prompt = (
            f"Professional product photography of {product_desc}, "
            "handmade artisan candle in textured raw concrete stone vessel, "
            f"natural soy wax, {style_prompts.get(style, style_prompts['dark'])}, "
            "8k resolution, commercial grade, shallow depth of field, magazine cover quality"
        )

        encoded_prompt = up.quote(full_prompt)
        img_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width=1024&height=1024&model=flux&seed={os.urandom(4).hex()}"
        )

        # v10.1: TITANIUM shielded image fetch
        if _TITANIUM_ACTIVE:
            _ti = await shielded_get(img_url, timeout=60.0, provider_name="pollinations_img")
            img_data = _ti.content
        else:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(img_url)
                img_data = resp.content

        photo = BufferedInputFile(img_data, filename=f"product_{style}.png")

        style_names = {
            "dark": "🌑 تیره دراماتیک", "light": "☀️ روشن مینیمال",
            "natural": "🌿 طبیعی", "luxury": "✨ لاکچری",
        }

        await callback.message.answer_photo(
            photo=photo,
            caption=f"📸 *{style_names.get(style, style)}* — {product_desc}",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await callback.message.answer(f"❌ {exc}")  # type: ignore[union-attr]


# ═══════════════════════════════════════



# ═══════════════════════════════════════
# /reviews — Review Management & Generator
# ═══════════════════════════════════════

@router.message(Command("reviews"))
async def cmd_reviews(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/reviews")

    if not raw:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 ساخت پاسخ ریویو", callback_data="rev:reply"),
             InlineKeyboardButton(text="⭐ ساخت درخواست ریویو", callback_data="rev:request")],
            [InlineKeyboardButton(text="📊 تحلیل ریویوها", callback_data="rev:analyze"),
             InlineKeyboardButton(text="🛡 مدیریت ریویو منفی", callback_data="rev:negative")],
        ])
        await safe_reply(message, "⭐ *مدیریت ریویو — Review Manager*\n\n"
            "`/reviews [محصول]` — ابزار کامل مدیریت ریویو\n\n"
            "*یا مستقیم:*\n"
            "`/reviews reply [متن ریویو]` — پاسخ حرفه‌ای\n"
            "`/reviews request [محصول]` — پیام درخواست ریویو\n"
            "`/reviews analyze [URL یا متن]` — تحلیل ریویوها\n"
            "`/reviews negative [متن]` — مدیریت ریویوی منفی\n\n"
            "👇 یا از دکمه‌ها استفاده کن:",
            reply_markup=kb)
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    prompts = {
        "reply": (
            "Generate 3 professional, warm review response templates:\n"
            f"Review text: {args or 'a positive 5-star review about product quality'}\n"
            f"{brand_ctx(message.chat.id)}\n\n"
            "For each response:\n"
            "1. Thank the customer by feeling (not just 'thanks')\n"
            "2. Reference specific product detail they mentioned\n"
            "3. Add a personal touch from the maker\n"
            "4. Include a soft CTA (new collection, follow, etc.)\n\n"
            "Provide 3 versions:\n"
            "- 🎯 Short & Sweet (2 sentences)\n"
            "- 💎 Detailed & Personal (1 paragraph)\n"
            "- 🌟 Story-driven (behind-the-scenes angle)\n\n"
            "All in English. Add Finnish (Suomi) version for each."
        ),
        "request": (
            f"Create review request messages for: {args or 'handmade product'}\n"
            f"{brand_ctx(message.chat.id)}\n\n"
            "Generate:\n"
            "1. 📦 Post-delivery message (sent 3 days after delivery)\n"
            "2. ⏰ Follow-up reminder (sent 7 days after if no review)\n"
            "3. 💝 Thank-you + review request (with incentive hint)\n"
            "4. 📱 Instagram DM version (casual, friendly)\n"
            "5. 📧 Email version (professional but warm)\n\n"
            "Each should:\n"
            "- Feel personal, not automated\n"
            "- Include specific product mention\n"
            "- Make leaving a review EASY (link placeholder)\n"
            "- EN + FI versions"
        ),
        "analyze": (
            f"Analyze these reviews and provide actionable insights:\n{args}\n\n"
            "Provide:\n"
            "1. 📊 Sentiment score (1-10)\n"
            "2. ✅ What customers love (top 3 themes)\n"
            "3. ⚠️ What needs improvement\n"
            "4. 💡 Product improvement ideas from feedback\n"
            "5. 📝 Keywords to use in marketing (from reviews)\n"
            "6. 🎯 Response priority list\n\n"
            "Write analysis in Persian."
        ),
        "negative": (
            f"Handle this negative review professionally:\n{args}\n\n"
            f"{brand_ctx(message.chat.id)}\n\n"
            "Generate:\n"
            "1. 🛡 Public response (empathetic, solution-focused)\n"
            "2. 📩 Private follow-up message\n"
            "3. 🔄 Recovery offer template\n"
            "4. ✅ Internal action checklist\n"
            "5. 📝 Prevent-recurrence plan\n\n"
            "Rules:\n"
            "- NEVER be defensive\n"
            "- Acknowledge the issue\n"
            "- Offer concrete solution\n"
            "- Turn negative into positive\n"
            "EN + FI versions"
        ),
    }

    # If action is not a known sub-command, treat entire input as product
    if action not in prompts:
        # Treat as product name → full review toolkit
        product = raw
        status = await message.answer("⭐ دارم ابزار کامل ریویو تولید می‌کنم...")
        try:
            cfg = await ai_client.get_user_config(message.from_user.id)
            mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)
            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content":
                        "You are a review management expert for artisan e-commerce. "
                        "Write in Persian for explanations, English for templates."},
                    {"role": "user", "content": (
                        f"Create a complete review management toolkit for: {product}\n"
                        f"{brand_ctx(message.chat.id)}\n\n"
                        "Include ALL of these:\n"
                        "1. 📝 Review request templates (3 versions)\n"
                        "2. 🌟 Positive review response templates (3 versions)\n"
                        "3. ⚠️ Negative review response templates (2 versions)\n"
                        "4. 📱 Instagram story template to showcase reviews\n"
                        "5. 📧 Email follow-up sequence (3 emails over 2 weeks)\n"
                        "6. 🎯 Review-boosting strategy (5 tactics)\n"
                    )},
                ],
                model_key=mk, temperature=0.8, max_tokens=16384,
            )
            await safe_delete(status)
            for chunk in split_for_telegram(f"⭐ *ابزار مدیریت ریویو — {product}:*\n\n{body}"):
                await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await safe_edit_text(status, user_friendly_error(exc))
        return

    prompt = prompts[action]
    header_map = {
        "reply": "📝 *پاسخ ریویو:*",
        "request": "⭐ *درخواست ریویو:*",
        "analyze": "📊 *تحلیل ریویوها:*",
        "negative": "🛡 *مدیریت ریویوی منفی:*",
    }

    status = await message.answer(f"⭐ {header_map[action].strip('*')} در حال تولید...")
    try:
        cfg = await ai_client.get_user_config(message.from_user.id)
        mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)
        body = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content":
                    "You are a review management expert for artisan e-commerce brands. "
                    "Write in Persian for explanations, English + Finnish for templates."},
                {"role": "user", "content": prompt},
            ],
            model_key=mk, temperature=0.8, max_tokens=16384,
        )
        await safe_delete(status)
        for chunk in split_for_telegram(f"{header_map[action]}\n\n{body}"):
            await safe_reply(message, chunk)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_edit_text(status, user_friendly_error(exc))


@router.callback_query(F.data.startswith("rev:"))
async def cb_reviews(callback: CallbackQuery) -> None:
    await callback.answer()
    action = callback.data.split(":")[1]  # type: ignore[misc]
    hints = {
        "reply": "📝 *پاسخ ریویو*\n\nمتن ریویو رو بده:\n`/reviews reply [متن ریویو مشتری]`",
        "request": "⭐ *درخواست ریویو*\n\nاسم محصول رو بده:\n`/reviews request [محصول]`",
        "analyze": "📊 *تحلیل ریویوها*\n\nریویوها رو کپی‌پیست کن:\n`/reviews analyze [متن ریویوها]`",
        "negative": "🛡 *ریویوی منفی*\n\nمتن ریویو منفی رو بده:\n`/reviews negative [متن]`",
    }
    text = hints.get(action, "❌ دستور نامعتبر")
    try:
        await safe_edit_text(callback.message, text)
    except Exception as e:
        logger.debug("Suppressed: %s", e)


# ═══════════════════════════════════════
# /inventory — Product Inventory Tracker
# ═══════════════════════════════════════

@router.message(Command("inventory"))
async def cmd_inventory(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/inventory")
    chat_id = message.chat.id

    from arki_project.utils.data_store import store as ds

    # Get existing inventory from KV store (stored in shop_profiles under 'inventory' key)
    profiles = ds.get_shop_profiles(chat_id)
    inventory = profiles.get("_inventory", {}).get("items", {})

    if not raw:
        text = "📦 *مدیریت موجودی — Inventory*\n\n"

        if inventory:
            total_items = sum(v.get("qty", 0) for v in inventory.values())
            low_stock = [(k, v) for k, v in inventory.items() if v.get("qty", 0) <= v.get("alert", 3)]

            text += f"📊 *{len(inventory)}* محصول | *{total_items}* عدد موجودی\n\n"

            if low_stock:
                text += "🔴 *موجودی کم:*\n"
                for name, info in low_stock:
                    text += f"  ⚠️ {name}: *{info.get('qty', 0)}* عدد\n"
                text += "\n"

            text += "*لیست موجودی:*\n"
            for name, info in sorted(inventory.items()):
                qty = info.get("qty", 0)
                icon = "🟢" if qty > 5 else ("🟡" if qty > 2 else "🔴")
                text += f"{icon} {name}: *{qty}* عدد"
                if info.get("price"):
                    text += f" (€{info['price']})"
                text += "\n"
        else:
            text += "هنوز محصولی ثبت نشده.\n"

        text += (
            "\n━━━━━━━━━━━━━━━\n"
            "*دستورات:*\n"
            "`/inventory add [نام] | [تعداد] | [قیمت]` — اضافه\n"
            "`/inventory update [نام] | [تعداد جدید]` — آپدیت\n"
            "`/inventory sell [نام] | [تعداد]` — ثبت فروش\n"
            "`/inventory alert [نام] | [حداقل]` — هشدار کمبود\n"
            "`/inventory report` — گزارش AI\n"
        )
        await safe_reply(message, text)
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if action == "add":
        fields = [p.strip() for p in args.split("|")]
        name = fields[0] if fields else ""
        qty = int(fields[1]) if len(fields) > 1 and fields[1].isdigit() else 0
        price = fields[2] if len(fields) > 2 else ""

        if not name:
            await safe_reply(message, "❌ `/inventory add نام | تعداد | قیمت`")
            return

        inventory[name] = {"qty": qty, "price": price, "alert": 3}
        profiles["_inventory"] = {"items": inventory}
        await ds.set_shop_profile(chat_id, "_inventory", profiles.get("_inventory", {}))
        await safe_reply(message, f"✅ *{name}* اضافه شد — {qty} عدد" + (f" (€{price})" if price else ""))

    elif action == "update":
        fields = [p.strip() for p in args.split("|")]
        name = fields[0] if fields else ""
        qty = int(fields[1]) if len(fields) > 1 and fields[1].isdigit() else None

        if not name or qty is None:
            await safe_reply(message, "❌ `/inventory update نام | تعداد جدید`")
            return

        if name in inventory:
            old_qty = inventory[name].get("qty", 0)
            inventory[name]["qty"] = qty
            profiles["_inventory"] = {"items": inventory}
            await ds.set_shop_profile(chat_id, "_inventory", profiles.get("_inventory", {}))
            await safe_reply(message, f"✅ *{name}*: {old_qty} → *{qty}* عدد")
        else:
            await safe_reply(message, f"❌ محصول *{name}* یافت نشد.\n`/inventory add {name} | {qty}`")

    elif action == "sell":
        fields = [p.strip() for p in args.split("|")]
        name = fields[0] if fields else ""
        qty = int(fields[1]) if len(fields) > 1 and fields[1].isdigit() else 1

        if name in inventory:
            current = inventory[name].get("qty", 0)
            if current >= qty:
                inventory[name]["qty"] = current - qty
                profiles["_inventory"] = {"items": inventory}
                await ds.set_shop_profile(chat_id, "_inventory", profiles.get("_inventory", {}))

                new_qty = inventory[name]["qty"]
                alert_icon = " ⚠️ *کمبود موجودی!*" if new_qty <= inventory[name].get("alert", 3) else ""
                await safe_reply(message,
                    "🛒 فروش ثبت شد!\n"
                    f"📦 *{name}*: {current} → *{new_qty}* عدد{alert_icon}")
            else:
                await safe_reply(message, f"❌ موجودی کافی نیست! فقط *{current}* عدد دارید.")
        else:
            await safe_reply(message, f"❌ محصول *{name}* یافت نشد.")

    elif action == "alert":
        fields = [p.strip() for p in args.split("|")]
        name = fields[0] if fields else ""
        threshold = int(fields[1]) if len(fields) > 1 and fields[1].isdigit() else 3

        if name in inventory:
            inventory[name]["alert"] = threshold
            profiles["_inventory"] = {"items": inventory}
            await ds.set_shop_profile(chat_id, "_inventory", profiles.get("_inventory", {}))
            await safe_reply(message, f"🔔 هشدار برای *{name}*: وقتی زیر *{threshold}* عدد بشه.")
        else:
            await safe_reply(message, f"❌ محصول *{name}* یافت نشد.")

    elif action == "report":
        if not inventory:
            await safe_reply(message, "📊 ابتدا محصول اضافه کن: `/inventory add`")
            return

        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        status = await message.answer("📊 دارم گزارش موجودی تولید می‌کنم...")

        inv_text = "\n".join([
            f"- {name}: {info.get('qty', 0)} units, €{info.get('price', '?')}"
            for name, info in inventory.items()
        ])

        try:
            cfg = await ai_client.get_user_config(message.from_user.id)
            mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)
            body = await ai_client.ask_raw(
                messages=[
                    {"role": "system", "content":
                        "You are an inventory management expert for artisan businesses. "
                        "Analyze inventory and give actionable recommendations. Persian."},
                    {"role": "user", "content": (
                        f"Analyze this inventory:\n{inv_text}\n\n"
                        f"{brand_ctx(chat_id)}\n\n"
                        "Provide:\n"
                        "1. 📊 Inventory health score (1-10)\n"
                        "2. 🔴 Items needing restock\n"
                        "3. 💰 Total inventory value estimate\n"
                        "4. 📈 Production priority list\n"
                        "5. 🎯 Restocking schedule recommendation\n"
                        "6. 💡 Slow-moving items strategy\n"
                        "7. 🛒 Bundle suggestions to move inventory"
                    )},
                ],
                model_key=mk, temperature=0.7, max_tokens=32768,
            )
            await safe_delete(status)
            for chunk in split_for_telegram(f"📊 *گزارش موجودی:*\n\n{body}"):
                await safe_reply(message, chunk)
        except Exception as exc:
            logger.error("Error in handler: %s", exc)
            await safe_edit_text(status, user_friendly_error(exc))
    else:
        await safe_reply(message,
            "❌ دستور نامعتبر.\n`/inventory` — داشبورد\n"
            "`/inventory add` | `update` | `sell` | `alert` | `report`")


