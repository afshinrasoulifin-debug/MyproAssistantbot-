
from __future__ import annotations
"""
tg_bot/handlers/platform_auto.py
─────────────────────────────────
🤖 Platform Automation Engine — fully automated e-commerce pipeline.

Turns the multi-platform hub into a self-managing system:
- Product database (SQLite)
- Content queue with scheduling
- Auto-generate all platform listings from one product
- Multi-platform sales tracker
- Weekly smart suggestions
- Batch operations

Commands:
  /addproduct   — Add product to database
  /products     — List all products
  /editproduct  — Edit a product
  /delproduct   — Remove a product
  /autopipeline — 🔥 Full auto: product → photos, posters, captions, listings, schedule
  /queue        — Content queue: see/manage scheduled content
  /postqueue    — Mark queue item as posted
  /sales        — Log a sale (platform, amount, product)
  /dashboard    — Cross-platform analytics dashboard
  /weeklytasks  — AI-generated weekly action plan
  /templates    — Save/load reusable listing templates
"""


import json
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
from datetime import datetime, timedelta

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

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    split_for_telegram,
    user_friendly_error,
    working_model_key,
)
from arki_project.handlers.shared import extract_args
from arki_project.utils.data_store import store
from arki_project.utils.safe_send import safe_edit_text, safe_reply
from arki_project.utils.v7_core import (

# ── Infrastructure access (injected by middleware) ──
# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]

    enhance_system_prompt, store_result,
)

logger = logging.getLogger(__name__)
router = Router(name="platform_auto")

_product_counters: dict[int, int] = {}
_queue_counters: dict[int, int] = {}
_templates: dict[int, dict[str, str]] = {}


# _extract_args → use shared extract_args


async def _ai_gen(
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
    store_result(int(uid) if uid.isdigit() else 0, user[:300], result[:500] if result else "", "platform_auto", duration_s=_t.time()-_t0)
    return result


def _get_brand(chat_id: int) -> str:
    b = store.get_brand(chat_id)
    if b:
        return f"Brand: {b.get('name','')}, {b.get('tagline','')}, style: {b.get('style','')}"
    return brand_ctx(chat_id)


def _get_platforms(chat_id: int) -> dict:
    from arki_project.handlers.platforms import PLATFORMS
    connected = store.get_shop_profiles(chat_id)
    return {k: PLATFORMS[k] for k in connected if k in PLATFORMS}


# ═══════════════════════════════════════
# /addproduct — Add Product to Database
# ═══════════════════════════════════════

@router.message(Command("addproduct"))
async def cmd_addproduct(message: Message) -> None:
    raw = extract_args(message.text or "", "/addproduct")

    if not raw:
        await safe_reply(message, "📦 *افزودن محصول:*\n\n"
            "`/addproduct [نام] | [قیمت €] | [توضیحات] | [مواد]`\n\n"
            "*مثال:*\n"
            "`/addproduct Nordic Stone Candle | 35 | Handmade soy wax in raw concrete vessel, lavender scent | concrete, soy wax, lavender oil, cotton wick`\n\n"
            "`/addproduct Mini Concrete Tealight | 12 | Minimalist tealight holder | concrete, tealight`\n\n"
            "_محصول ذخیره می‌شه و برای همه دستورات اتوماسیون استفاده می‌شه._")
        return

    parts = [p.strip() for p in raw.split("|")]
    name = parts[0]
    price = parts[1] if len(parts) > 1 else ""
    desc = parts[2] if len(parts) > 2 else ""
    materials = parts[3] if len(parts) > 3 else ""

    cid = message.chat.id
    # Derive counter from existing products in store (survives restart)
    if cid not in _product_counters:
        existing = store.get_products(cid)
        _product_counters[cid] = max((int(k) for k in existing), default=0) if existing else 0
    _product_counters[cid] += 1
    pid = _product_counters[cid]

    await store.set_product(cid, pid, {
        "name": name,
        "price": price,
        "description": desc,
        "materials": materials,
        "created": datetime.now().isoformat(),
        "photos_generated": False,
        "listings_generated": False,
    })

    # Build quick-action keyboard
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 پایپلاین کامل", callback_data=f"pauto:pipeline:{pid}"),
            InlineKeyboardButton(text="📋 آگهی‌ها", callback_data=f"pauto:listings:{pid}"),
        ],
        [
            InlineKeyboardButton(text="📸 عکس", callback_data=f"pauto:photos:{pid}"),
            InlineKeyboardButton(text="✍️ کپشن", callback_data=f"pauto:captions:{pid}"),
        ],
    ])

    await safe_reply(message, f"✅ *محصول #{pid} ذخیره شد:*\n\n"
        f"📦 *{name}*\n"
        f"💰 €{price}\n"
        f"📝 {desc[:100]}{'...' if len(desc) > 100 else ''}\n"
        f"🧪 {materials[:80]}{'...' if len(materials) > 80 else ''}\n\n"
        "_از دکمه‌ها استفاده کن یا:_\n"
        f"`/autopipeline {pid}`",
        reply_markup=kb)


# ═══════════════════════════════════════
# /products — List All Products
# ═══════════════════════════════════════

@router.message(Command("products"))
async def cmd_products(message: Message) -> None:
    prods = store.get_products(message.chat.id)

    if not prods:
        await message.answer(
            "📦 هنوز محصولی اضافه نشده.\n\n"
            "`/addproduct [نام] | [قیمت] | [توضیحات] | [مواد]`",
        )
        return

    lines = []
    buttons = []
    for pid, p in prods.items():
        status = ""
        if p.get("listings_generated"):
            status += "📋"
        if p.get("photos_generated"):
            status += "📸"
        lines.append(
            f"*#{pid}* {status} — *{p['name']}*  €{p['price']}\n"
            f"   _{p['description'][:60]}{'...' if len(p['description']) > 60 else ''}_"
        )
        buttons.append([
            InlineKeyboardButton(text=f"#{pid} {p['name'][:20]}", callback_data=f"pauto:view:{pid}"),
            InlineKeyboardButton(text="🚀", callback_data=f"pauto:pipeline:{pid}"),
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await safe_reply(message, f"📦 *محصولات ({len(prods)}):*\n\n" + "\n\n".join(lines),
        reply_markup=kb)


# ═══════════════════════════════════════
# /editproduct — Edit Product
# ═══════════════════════════════════════

@router.message(Command("editproduct"))
async def cmd_editproduct(message: Message) -> None:
    raw = extract_args(message.text or "", "/editproduct")

    if not raw:
        await safe_reply(message, "✏️ *ویرایش محصول:*\n\n"
            "`/editproduct [شماره] [فیلد]=[مقدار جدید]`\n\n"
            "*فیلدها:* `name`, `price`, `description`, `materials`\n\n"
            "*مثال:*\n"
            "`/editproduct 1 price=39`\n"
            "`/editproduct 2 name=Premium Nordic Candle`")
        return

    parts = raw.split(maxsplit=1)
    try:
        pid = int(parts[0])
    except (ValueError, IndexError):
        await message.answer("❌ شماره محصول نامعتبر. `/products` رو ببین.")
        return

    prods = store.get_products(message.chat.id)
    if pid not in prods:
        await message.answer(f"❌ محصول #{pid} وجود نداره.")
        return

    if len(parts) < 2 or "=" not in parts[1]:
        await message.answer("❌ فرمت: `/editproduct 1 price=39`")
        return

    field, value = parts[1].split("=", 1)
    field = field.strip().lower()
    value = value.strip()

    valid_fields = {"name", "price", "description", "materials"}
    if field not in valid_fields:
        await message.answer(f"❌ فیلد نامعتبر. فیلدهای مجاز: {', '.join(valid_fields)}")
        return

    prods[pid][field] = value
    await safe_reply(message, f"✅ محصول #{pid}: `{field}` = `{value}`")


# ═══════════════════════════════════════
# /delproduct — Delete Product
# ═══════════════════════════════════════

@router.message(Command("delproduct"))
async def cmd_delproduct(message: Message) -> None:
    raw = extract_args(message.text or "", "/delproduct")
    try:
        pid = int(raw)
    except (ValueError, TypeError):
        await message.answer("❌ `/delproduct [شماره]`\nشماره محصول رو بده.")
        return

    prods = store.get_products(message.chat.id)
    if pid in prods:
        name = prods[pid]["name"]
        del prods[pid]
        await message.answer(f"🗑 محصول #{pid} «{name}» حذف شد.")
    else:
        await message.answer(f"❌ محصول #{pid} وجود نداره.")


# ═══════════════════════════════════════
# /autopipeline — 🔥 FULL AUTO PIPELINE
# ═══════════════════════════════════════

@router.message(Command("autopipeline"))
async def cmd_autopipeline(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = extract_args(message.text or "", "/autopipeline")

    prods = store.get_products(message.chat.id)

    if not raw:
        if not prods:
            await safe_reply(message, "🚀 *پایپلاین اتوماتیک:*\n\n"
                "اول محصول اضافه کن:\n"
                "`/addproduct Nordic Candle | 35 | Soy wax concrete candle | concrete, soy wax`\n\n"
                "بعد:\n"
                "`/autopipeline 1`  یا  `/autopipeline all`\n\n"
                "_*یه دستور = عکس + پوستر + کپشن + آگهی ۱۶ پلتفرم + زمان‌بندی*_")
        else:
            await safe_reply(message, "🚀 *پایپلاین اتوماتیک:*\n\n"
                "`/autopipeline [شماره محصول]`\n"
                "`/autopipeline all` — *همه محصولات*\n\n"
                "_یه دستور = عکس + پوستر + کپشن + آگهی ۱۶ پلتفرم + زمان‌بندی_")
        return

    # Determine which products to process
    if raw.lower() == "all":
        target_pids = list(prods.keys())
    else:
        try:
            target_pids = [int(raw)]
        except ValueError:
            await message.answer("❌ شماره محصول نامعتبر.")
            return

    if not target_pids:
        await message.answer("❌ محصولی وجود نداره. اول `/addproduct`")
        return

    for pid in target_pids:
        if pid not in prods:
            await message.answer(f"❌ محصول #{pid} وجود نداره.")
            continue

        product = prods[pid]
        pname = product["name"]
        pprice = product["price"]
        pdesc = product["description"]
        pmaterials = product["materials"]

        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        status = await safe_reply(message, f"🚀 *پایپلاین اتومات #{pid} — {pname}*\n\n"
            "⏳ مرحله ۱/۵: عکس‌های حرفه‌ای...")

        try:
            # ═══ STEP 1: Generate 3 pro photos ═══
            photo_styles = [
                ("dark", "dark moody, dramatic side lighting, dark walnut wood surface, Kinfolk editorial"),
                ("nordic", "Scandinavian minimal, light birch, soft daylight, Finnish interior design"),
                ("lifestyle", "lifestyle setting, cozy living room, warm blanket, candle lit, evening ambiance"),
            ]
            photos_sent = 0
            for sname, sdesc in photo_styles:
                try:
                    prompt = (
                        f"Professional product photography of {pname}, "
                        f"handmade artisan candle, {pdesc}, {sdesc}, "
                        "8k, commercial photography, magazine quality"
                    )
                    encoded = urllib.parse.quote(prompt)
                    url = (
                        f"https://image.pollinations.ai/prompt/{encoded}"
                        f"?width=1024&height=1024&model=flux&seed={random.randint(1,99999)}"
                    )
                    # v10.1: Route through TITANIUM shielded client
                    if _TITANIUM_ACTIVE:
                        ti_resp = await shielded_get(url, timeout=60.0)
                        if ti_resp.success and ti_resp.status_code == 200 and len(ti_resp.content) > 5000:
                            photo = BufferedInputFile(ti_resp.content, filename=f"auto_{pid}_{sname}.png")
                            await message.answer_photo(
                                photo=photo,
                                caption=f"📸 #{pid} *{pname}* — {sname}",
                                parse_mode="Markdown",
                            )
                            photos_sent += 1
                            continue
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        resp = await client.get(url)
                        if resp.status_code == 200 and len(resp.content) > 5000:
                            photo = BufferedInputFile(resp.content, filename=f"auto_{pid}_{sname}.png")
                            await message.answer_photo(
                                photo=photo,
                                caption=f"📸 #{pid} *{pname}* — {sname}",
                                parse_mode="Markdown",
                            )
                            photos_sent += 1
                except Exception as exc:
                    logger.warning("Pipeline photo %s failed: %s", sname, exc)

            product["photos_generated"] = True

            # ═══ STEP 2: Generate posters ═══
            await safe_edit_text(status, f"🚀 *پایپلاین #{pid} — {pname}*\n\n"
                f"✅ مرحله ۱: {photos_sent} عکس\n"
                "⏳ مرحله ۲/۵: پوسترها...")
            posters_sent = 0
            try:
                from arki_project.utils.poster_gen import generate_poster
                for tpl in ["sale", "product", "minimal"]:
                    try:
                        img = generate_poster(tpl, pname, pprice, "", pdesc[:40])
                        await message.answer_photo(
                            photo=BufferedInputFile(img, f"poster_{pid}_{tpl}.png"),
                            caption=f"🎨 پوستر {tpl} — #{pid}",
                        )
                        posters_sent += 1
                    except Exception as e:
                        logger.debug("Suppressed: %s", e)
            except Exception as e:
                logger.debug("Suppressed: %s", e)

            # ═══ STEP 3: AI content — captions + hashtags ═══
            await safe_edit_text(status, f"🚀 *پایپلاین #{pid} — {pname}*\n\n"
                f"✅ مرحله ۱: {photos_sent} عکس\n"
                f"✅ مرحله ۲: {posters_sent} پوستر\n"
                "⏳ مرحله ۳/۵: کپشن‌ها و هشتگ...")

            captions = await _ai_gen(
                message, ai_client, settings,
                system=(
                    "You are a world-class social media content creator for artisan brands. "
                    "Write in both English and Finnish. Be creative, on-brand, and conversion-focused."
                ),
                user=(
                    "Create content for this product:\n"
                    f"Product: {pname}\nPrice: €{pprice}\n"
                    f"Description: {pdesc}\nMaterials: {pmaterials}\n"
                    f"{_get_brand(message.chat.id)}\n\n"
                    "Generate:\n"
                    "✍️ *5 INSTAGRAM CAPTIONS* (EN): Story, Educational, Sale, Aesthetic, Engagement\n"
                    "✍️ *5 INSTAGRAM CAPTIONS* (FI): Same 5 styles in Finnish\n"
                    "🏷 *50 HASHTAGS*: 20 popular EN + 15 niche EN + 15 Finnish\n"
                    "🎬 *REEL SCRIPT*: 30-sec, hook + content + CTA\n"
                    "📱 *5 STORY SLIDES*: text overlay for each slide\n\n"
                    "Everything READY TO COPY-PASTE."
                ),
            )

            for chunk in split_for_telegram(f"✍️ *محتوای #{pid} — {pname}:*\n\n{captions}"):
                try:
                    await safe_reply(message, chunk)
                except Exception as exc:
                    logger.error("Error in handler: %s", exc)
                    await message.answer(chunk)

            # ═══ STEP 4: Platform listings ═══
            await safe_edit_text(status, f"🚀 *پایپلاین #{pid} — {pname}*\n\n"
                f"✅ مرحله ۱: {photos_sent} عکس\n"
                f"✅ مرحله ۲: {posters_sent} پوستر\n"
                "✅ مرحله ۳: کپشن + هشتگ + ریلز\n"
                "⏳ مرحله ۴/۵: آگهی ۱۶ پلتفرم...")

            # Import platform info
            try:
                from arki_project.handlers.platforms import PLATFORMS
                profiles = store.get_shop_profiles(message.chat.id)
                target_plats = {"etsy", "tori", "huuto", "tradera", "dba", "finn",
                                "cdon", "amazon_handmade", "ebay", "faire",
                                "fruugo", "instagram_shop", "facebook_shop",
                                "pinterest_shop", "tiktok_shop"}
                target_plats.update(profiles.keys())

                plat_sections = []
                for k in sorted(target_plats):
                    p = PLATFORMS.get(k)
                    if not p:
                        continue
                    prof = profiles.get(k, {})
                    prof_str = f"\nSeller: {json.dumps(prof, ensure_ascii=False)}" if prof else ""
                    plat_sections.append(
                        f"═══ {p['flag']} {p['name']} ({p['lang']}) ═══\n"
                        f"Format: {p['listing_format']}\n"
                        f"Tips: {p['tips']}{prof_str}\n"
                    )

                listings = await _ai_gen(
                    message, ai_client, settings,
                    system=(
                        "You are a multi-platform e-commerce listing expert. You write fluently "
                        "in Finnish, Swedish, Danish, Norwegian, English, German, French. "
                        "Every listing is SEO-optimized for its specific platform."
                    ),
                    user=(
                        "Create OPTIMIZED LISTINGS for this product on ALL platforms:\n\n"
                        f"Product: {pname}\nPrice: €{pprice}\nDescription: {pdesc}\n"
                        f"Materials: {pmaterials}\n{_get_brand(message.chat.id)}\n\n"
                        "Currency conversions: €1 ≈ SEK 11.5, DKK 7.5, NOK 11.8, GBP 0.86\n\n"
                        + "\n".join(plat_sections)
                        + "\n\nEach listing: CORRECT LANGUAGE + FORMAT + SEO. Ready to paste."
                    ),
                )

                for chunk in split_for_telegram(f"📋 *آگهی‌های #{pid} — {pname}:*\n\n{listings}"):
                    try:
                        await safe_reply(message, chunk)
                    except Exception as exc:
                        logger.error("Error in handler: %s", exc)
                        await message.answer(chunk)

                product["listings_generated"] = True

            except Exception as exc:
                logger.error("Listings failed: %s", exc)
                await message.answer(f"⚠️ خطا در تولید آگهی: {user_friendly_error(exc)}")

            # ═══ STEP 5: 7-day content schedule ═══
            await safe_edit_text(status, f"🚀 *پایپلاین #{pid} — {pname}*\n\n"
                f"✅ مرحله ۱: {photos_sent} عکس\n"
                f"✅ مرحله ۲: {posters_sent} پوستر\n"
                "✅ مرحله ۳: کپشن + هشتگ + ریلز\n"
                "✅ مرحله ۴: آگهی‌های چند-پلتفرمی\n"
                "⏳ مرحله ۵/۵: برنامه هفتگی...")

            schedule = await _ai_gen(
                message, ai_client, settings,
                system="You are a social media scheduler. Create exact daily plans.",
                user=(
                    f"Create a 7-DAY CONTENT SCHEDULE for {pname} (€{pprice}):\n"
                    f"{_get_brand(message.chat.id)}\n\n"
                    "For each day (Mon-Sun):\n"
                    "⏰ Best posting time (Helsinki timezone)\n"
                    "📱 Platform (Instagram/TikTok/Pinterest/Etsy)\n"
                    "📝 Content type (Post/Reel/Story/Pin/Listing update)\n"
                    "✍️ Which caption to use (reference the captions by style)\n"
                    "📸 Which photo style to use\n"
                    "🏷 Hashtag set to use\n"
                    "💡 Extra tip for that day\n\n"
                    "Write in Persian. Include both Instagram and other platforms."
                ),
                temp=0.8,
            )

            for chunk in split_for_telegram(f"📅 *برنامه ۷ روزه #{pid} — {pname}:*\n\n{schedule}"):
                try:
                    await safe_reply(message, chunk)
                except Exception as exc:
                    logger.error("Error in handler: %s", exc)
                    await message.answer(chunk)

            # Add to content queue (persistent)
            cid = message.chat.id
            if cid not in _queue_counters:
                existing_q = store.get_queue(cid)
                _queue_counters[cid] = max((int(q.get("id", 0)) for q in existing_q), default=0) if existing_q else 0
            now = datetime.now()
            for day_offset in range(7):
                _queue_counters[cid] += 1
                await store.add_to_queue(cid, {
                    "id": _queue_counters[cid],
                    "product_id": pid,
                    "product_name": pname,
                    "day": (now + timedelta(days=day_offset)).strftime("%Y-%m-%d"),
                    "status": "pending",  # pending / posted / skipped
                })

            # ═══ STEP 6: REAL PUBLISHING ═══
            published_platforms = []
            try:
                from arki_project.utils.platform_publisher import (
                    get_publisher_manager, ContentPayload,
                )
                pm = get_publisher_manager()
                configured = pm.get_configured_platforms()

                if configured:
                    await safe_edit_text(status,
                        f"🚀 *پایپلاین #{pid} — {pname}*\n\n"
                        f"✅ مرحله ۱-۵ تکمیل\n"
                        f"⏳ مرحله ۶/۶: انتشار واقعی در {len(configured)} پلتفرم..."
                    )

                    content = ContentPayload(
                        title=pname,
                        body=pdesc,
                        caption=captions[:2200] if captions else pname,
                        price=float(pprice) if pprice else 0,
                        tags=[t.strip() for t in (pmaterials or "").split(",")],
                        image_urls=product.get("image_urls", []),
                    )

                    results = await pm.publish_all(content)
                    for r in results:
                        if r.success:
                            published_platforms.append(
                                f"✅ {r.platform.value}: {r.post_url or r.post_id}"
                            )
                        else:
                            published_platforms.append(
                                f"❌ {r.platform.value}: {r.error[:50]}"
                            )
                else:
                    published_platforms.append(
                        "ℹ️ هیچ پلتفرمی تنظیم نشده — env varها رو ست کن"
                    )

            except ImportError:
                published_platforms.append(
                    "ℹ️ platform_publisher.py — فقط متن تولید شد"
                )
            except Exception as exc:
                published_platforms.append(f"⚠️ خطا: {exc}")

            if published_platforms:
                pub_text = "\n".join(published_platforms)
                await safe_reply(message,
                    f"📡 *انتشار واقعی #{pid}:*\n{pub_text}"
                )

            # ═══ DONE! ═══
            pub_count = sum(1 for p in published_platforms if p.startswith("✅"))
            await safe_edit_text(status, f"✅ *پایپلاین #{pid} — {pname} — تمام!*\n\n"
                f"📸 {photos_sent} عکس حرفه‌ای\n"
                f"🎨 {posters_sent} پوستر\n"
                "✍️ ۱۰ کپشن (EN+FI)\n"
                "🏷 ۵۰ هشتگ\n"
                "🎬 اسکریپت ریلز\n"
                "📋 آگهی‌های ۱۶ پلتفرم\n"
                "📅 برنامه ۷ روزه\n"
                "📌 ۷ آیتم به صف محتوا اضافه شد\n"
                f"📡 انتشار واقعی: {pub_count} پلتفرم\n\n"
                "_`/queue` رو ببین + `/sales` فروش ثبت کن_")

        except Exception as exc:
            logger.error("Pipeline %s failed: %s", pid, exc)
            await safe_edit_text(status, f"❌ خطا در پایپلاین #{pid}: {user_friendly_error(exc)}")


# ═══════════════════════════════════════
# Callback handlers for inline buttons
# ═══════════════════════════════════════

@router.callback_query(F.data.startswith("pauto:pipeline:"))
async def cb_pipeline(
    callback: CallbackQuery, ai_client: AIClient, settings: Settings,
) -> None:
    try:
        await callback.answer("🚀 شروع پایپلاین...")
        pid = callback.data.split(":")[2]
        # Send command as message
        await safe_reply(callback.message, f"🚀 `/autopipeline {pid}` اجرا شد...")
        # Manually invoke — create a lightweight pseudo-message
        fake_msg = callback.message.model_copy(
            update={"text": f"/autopipeline {pid}", "from_user": callback.from_user},
        )
        fake_msg.as_(callback.message.bot)
        await cmd_autopipeline(fake_msg, ai_client, settings)

    except Exception as exc:
        logger.error("cb_pipeline error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
@router.callback_query(F.data.startswith("pauto:photos:"))
async def cb_photos(callback: CallbackQuery) -> None:
    try:
        await callback.answer("📸 از /megapost یا /photopro استفاده کن")
        pid = callback.data.split(":")[2]
        prods = store.get_products(callback.message.chat.id)
        prod = prods.get(int(pid))
        if prod:
            await safe_reply(callback.message, f"📸 عکس حرفه‌ای:\n`/photopro {prod['name']}`")

    except Exception as exc:
        logger.error("cb_photos error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
@router.callback_query(F.data.startswith("pauto:captions:"))
async def cb_captions(callback: CallbackQuery) -> None:
    try:
        await callback.answer("✍️ از /caption استفاده کن")
        pid = callback.data.split(":")[2]
        prods = store.get_products(callback.message.chat.id)
        prod = prods.get(int(pid))
        if prod:
            await safe_reply(callback.message, f"✍️ کپشن:\n`/caption {prod['name']}`")

    except Exception as exc:
        logger.error("cb_captions error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
@router.callback_query(F.data.startswith("pauto:listings:"))
async def cb_listings(callback: CallbackQuery) -> None:
    try:
        await callback.answer("📋 از /publish استفاده کن")
        pid = callback.data.split(":")[2]
        prods = store.get_products(callback.message.chat.id)
        prod = prods.get(int(pid))
        if prod:
            await safe_reply(callback.message, f"📋 آگهی‌ها:\n`/publish {prod['name']} | {prod['price']} | {prod['description'][:50]}`")

    except Exception as exc:
        logger.error("cb_listings error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
@router.callback_query(F.data.startswith("pauto:view:"))
async def cb_view_product(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
        pid = int(callback.data.split(":")[2])
        prods = store.get_products(callback.message.chat.id)
        prod = prods.get(pid)
        if not prod:
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🚀 پایپلاین", callback_data=f"pauto:pipeline:{pid}"),
                InlineKeyboardButton(text="📋 آگهی", callback_data=f"pauto:listings:{pid}"),
            ],
            [
                InlineKeyboardButton(text="📸 عکس", callback_data=f"pauto:photos:{pid}"),
                InlineKeyboardButton(text="✍️ کپشن", callback_data=f"pauto:captions:{pid}"),
            ],
        ])

        await safe_reply(callback.message, f"📦 *محصول #{pid}:*\n\n"
            f"📛 *{prod['name']}*\n"
            f"💰 €{prod['price']}\n"
            f"📝 {prod['description']}\n"
            f"🧪 {prod['materials']}\n"
            f"📸 عکس: {'✅' if prod.get('photos_generated') else '❌'}\n"
            f"📋 آگهی: {'✅' if prod.get('listings_generated') else '❌'}\n"
            f"📅 ثبت: {prod['created'][:10]}",
            reply_markup=kb)

    except Exception as exc:
        logger.error("cb_view_product error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /queue — Content Queue
# ═══════════════════════════════════════

@router.message(Command("prodqueue"))
async def cmd_queue(message: Message) -> None:
    queue = store.get_queue(message.chat.id)

    if not queue:
        await safe_reply(message, "📌 *صف محتوا خالیه.*\n\n"
            "`/autopipeline` اجرا کن تا خودکار پر بشه.\n"
            "یا دستی اضافه کن:\n"
            "`/addqueue [محصول] | [پلتفرم] | [تاریخ]`")
        return

    pending = [q for q in queue if q["status"] == "pending"]
    posted = [q for q in queue if q["status"] == "posted"]

    lines = []
    buttons = []
    for q in pending[:14]:  # Show max 14
        lines.append(
            f"{'⬜' if q['status'] == 'pending' else '✅'} "
            f"*{q['day']}* — #{q['product_id']} {q['product_name']}"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"✅ پست شد: {q['day'][:5]} #{q['product_id']}",
                callback_data=f"q:done:{q['id']}",
            ),
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons[:7])

    await safe_reply(message, "📌 *صف محتوا:*\n\n"
        f"⬜ در انتظار: {len(pending)}\n"
        f"✅ انجام شده: {len(posted)}\n\n"
        + "\n".join(lines)
        + "\n\n_دکمه رو بزن وقتی پست کردی:_",
        reply_markup=kb)


@router.callback_query(F.data.startswith("q:done:"))
async def cb_queue_done(callback: CallbackQuery) -> None:
    try:
        qid = int(callback.data.split(":")[2])
        queue = store.get_queue(callback.message.chat.id)
        for q in queue:
            if q["id"] == qid:
                q["status"] = "posted"
                await callback.answer(f"✅ {q['day']} ثبت شد!")
                # Update the message
                await cmd_queue(callback.message)
                return
        await callback.answer("❌ پیدا نشد")

    except Exception as exc:
        logger.error("cb_queue_done error: %s", exc)
        try:
            await callback.answer("⚠️ خطا رخ داد", show_alert=True)
        except Exception as e:
            logger.debug("Suppressed: %s", e)
# ═══════════════════════════════════════
# /postqueue — Mark as Posted
# ═══════════════════════════════════════

@router.message(Command("postqueue"))
async def cmd_postqueue(message: Message) -> None:
    raw = extract_args(message.text or "", "/postqueue")
    try:
        qid = int(raw)
    except (ValueError, TypeError):
        await message.answer("❌ `/postqueue [شماره]`")
        return

    queue = store.get_queue(message.chat.id)
    for q in queue:
        if q["id"] == qid:
            q["status"] = "posted"
            await message.answer(f"✅ آیتم #{qid} — پست شد!")
            return
    await message.answer("❌ پیدا نشد.")


# ═══════════════════════════════════════
# /sales — Log Sales
# ═══════════════════════════════════════

@router.message(Command("sales"))
async def cmd_sales(message: Message) -> None:
    raw = extract_args(message.text or "", "/sales")

    if not raw:
        sales = store.get_sales(message.chat.id)
        if not sales:
            await safe_reply(message, "💰 *ثبت فروش:*\n\n"
                "`/sales [پلتفرم] | [مبلغ €] | [محصول] | [یادداشت]`\n\n"
                "*مثال:*\n"
                "`/sales etsy | 35 | Nordic Candle | First sale!`\n"
                "`/sales tori | 25 | Mini Tealight`\n"
                "`/sales instagram | 40 | Custom Order | DM order`\n\n"
                "`/sales report` — گزارش فروش\n"
                "`/sales today` — فروش امروز")
            return

        # Show recent sales
        total = sum(float(s.get("amount", 0)) for s in sales)
        lines = []
        for s in sales[-10:]:
            lines.append(
                f"  {s['date'][:10]} — {s['platform']} — €{s['amount']} — {s.get('product', '')}"
            )
        await safe_reply(message, f"💰 *فروش‌ها ({len(sales)} تراکنش):*\n\n"
            + "\n".join(lines)
            + f"\n\n💵 *جمع کل: €{total:.2f}*\n\n"
            "`/sales report` — گزارش کامل\n"
            "`/sales [platform] | [amount] | [product]` — ثبت فروش جدید")
        return

    if raw.lower() == "report":
        await _sales_report(message)
        return

    if raw.lower() == "today":
        sales = store.get_sales(message.chat.id)
        today = datetime.now().strftime("%Y-%m-%d")
        todays = [s for s in sales if s["date"].startswith(today)]
        if not todays:
            await message.answer("📊 امروز فروشی ثبت نشده.")
            return
        total = sum(float(s["amount"]) for s in todays)
        lines = [f"  {s['platform']} — €{s['amount']} — {s.get('product','')}" for s in todays]
        await safe_reply(message, "📊 *فروش امروز:*\n\n" + "\n".join(lines) + f"\n\n💵 *جمع: €{total:.2f}*")
        return

    # Log new sale
    parts = [p.strip() for p in raw.split("|")]
    platform = parts[0] if len(parts) > 0 else "unknown"
    raw_amount = parts[1] if len(parts) > 1 else "0"
    try:
        amount = float(raw_amount.replace(",", ".").split()[0])
    except (ValueError, IndexError):
        amount = 0.0
    product = parts[2] if len(parts) > 2 else ""
    notes = parts[3] if len(parts) > 3 else ""

    await store.add_sale(message.chat.id, {
        "date": datetime.now().isoformat(),
        "platform": platform,
        "amount": amount,
        "product": product,
        "notes": notes,
    })

    all_sales = store.get_sales(message.chat.id)
    total = sum(float(s.get("amount", 0)) for s in all_sales)
    count = len(all_sales)

    await safe_reply(message, "✅ *فروش ثبت شد:*\n\n"
        f"🏪 {platform}\n"
        f"💰 €{amount:.2f}\n"
        f"📦 {product}\n"
        f"{'📝 ' + notes if notes else ''}\n\n"
        f"📊 *کل:* {count} فروش — €{total:.2f}")


async def _sales_report(message: Message) -> None:
    sales = store.get_sales(message.chat.id)
    if not sales:
        await message.answer("📊 هنوز فروشی ثبت نشده.")
        return

    # Group by platform
    by_platform: dict[str, list] = {}
    for s in sales:
        by_platform.setdefault(s["platform"], []).append(s)

    total = sum(float(s.get("amount", 0)) for s in sales)

    lines = []
    for plat, ss in sorted(by_platform.items(), key=lambda x: -sum(float(s["amount"]) for s in x[1])):
        plat_total = sum(float(s["amount"]) for s in ss)
        pct = (plat_total / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        lines.append(
            f"*{plat}:* {len(ss)} فروش — €{plat_total:.2f} ({pct:.0f}%)\n"
            f"`{bar}`"
        )

    # Group by product
    by_product: dict[str, float] = {}
    for s in sales:
        prod = s.get("product", "unknown")
        by_product[prod] = by_product.get(prod, 0) + float(s.get("amount", 0))

    prod_lines = []
    for prod, amt in sorted(by_product.items(), key=lambda x: -x[1]):
        prod_lines.append(f"  📦 {prod}: €{amt:.2f}")

    await safe_reply(message, "📊 *گزارش فروش:*\n\n"
        f"💰 *جمع کل: €{total:.2f}*\n"
        f"🛒 *تراکنش‌ها: {len(sales)}*\n"
        f"📊 *میانگین: €{total/len(sales):.2f}*\n\n"
        "━━━ *بر اساس پلتفرم:* ━━━\n\n"
        + "\n\n".join(lines)
        + "\n\n━━━ *بر اساس محصول:* ━━━\n\n"
        + "\n".join(prod_lines))


# ═══════════════════════════════════════
# /dashboard — Analytics Dashboard
# ═══════════════════════════════════════

@router.message(Command("dashboard_legacy_disabled"))  # Moved to sales_brain.py
async def cmd_dashboard(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    prods = store.get_products(message.chat.id)
    sales = store.get_sales(message.chat.id)
    queue = store.get_queue(message.chat.id)
    profiles = store.get_shop_profiles(message.chat.id)

    total_sales = sum(float(s.get("amount", 0)) for s in sales)
    pending_q = len([q for q in queue if q["status"] == "pending"])
    posted_q = len([q for q in queue if q["status"] == "posted"])

    # Platform performance
    by_plat: dict[str, float] = {}
    for s in sales:
        by_plat[s["platform"]] = by_plat.get(s["platform"], 0) + float(s.get("amount", 0))
    top_plat = max(by_plat.items(), key=lambda x: x[1])[0] if by_plat else "—"

    await safe_reply(message, "📊 *داشبورد Arki Engine:*\n\n"
        "━━━ *محصولات* ━━━\n"
        f"📦 {len(prods)} محصول\n"
        f"📸 {sum(1 for p in prods.values() if p.get('photos_generated'))} با عکس\n"
        f"📋 {sum(1 for p in prods.values() if p.get('listings_generated'))} با آگهی\n\n"
        "━━━ *فروش* ━━━\n"
        f"💰 €{total_sales:.2f} کل\n"
        f"🛒 {len(sales)} تراکنش\n"
        f"🏆 بهترین پلتفرم: {top_plat}\n\n"
        "━━━ *محتوا* ━━━\n"
        f"⬜ {pending_q} در صف\n"
        f"✅ {posted_q} پست شده\n\n"
        "━━━ *پلتفرم‌ها* ━━━\n"
        f"🔗 {len(profiles)} متصل\n\n"
        "💡 `/weeklytasks` — پیشنهاد هوشمند این هفته\n"
        "📊 `/sales report` — گزارش فروش کامل")


# ═══════════════════════════════════════
# /weeklytasks — AI Smart Weekly Plan
# ═══════════════════════════════════════

@router.message(Command("weeklytasks"))
async def cmd_weeklytasks(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    prods = store.get_products(message.chat.id)
    sales = store.get_sales(message.chat.id)
    queue = store.get_queue(message.chat.id)
    from arki_project.handlers.platforms import PLATFORMS
    profiles = store.get_shop_profiles(message.chat.id)

    # Build context
    products_ctx = "\n".join(
        f"- #{pid} {p['name']} €{p['price']} (photos: {p.get('photos_generated')}, listings: {p.get('listings_generated')})"
        for pid, p in prods.items()
    ) or "No products added yet"

    sales_ctx = f"{len(sales)} total sales, €{sum(float(s.get('amount', 0)) for s in sales):.2f} total"
    if sales:
        by_plat = {}
        for s in sales:
            by_plat[s["platform"]] = by_plat.get(s["platform"], 0) + float(s.get("amount", 0))
        sales_ctx += "\nPer platform: " + ", ".join(f"{k}: €{v:.2f}" for k, v in by_plat.items())

    pending = len([q for q in queue if q["status"] == "pending"])
    connected = [PLATFORMS.get(k, {}).get("name", k) for k in profiles] if profiles else []

    try:
        body = await _ai_gen(
            message, ai_client, settings,
            system=(
                "You are a personal e-commerce business coach. "
                "You analyze the current state of the business and create an actionable weekly plan. "
                "Be specific, practical, and prioritized. Write in Persian."
            ),
            user=(
                "Create a SMART WEEKLY ACTION PLAN based on this business state:\n\n"
                f"Products:\n{products_ctx}\n\n"
                f"Sales: {sales_ctx}\n\n"
                f"Content queue: {pending} pending items\n\n"
                f"Connected platforms: {', '.join(connected) if connected else 'None yet'}\n\n"
                f"{brand_ctx(message.chat.id)}\n"
                f"{_get_brand(message.chat.id)}\n\n"
                f"Today: {datetime.now().strftime('%A, %B %d, %Y')}\n\n"
                "Generate:\n"
                "📋 *TOP 5 PRIORITIES THIS WEEK* (numbered, specific actions)\n"
                "📅 *DAILY PLAN* (Mon-Sun, what to do each day)\n"
                "📈 *GROWTH TIPS* based on current performance\n"
                "⚠️ *WHAT'S MISSING* — gaps to fill urgently\n"
                "🎯 *THIS WEEK'S GOAL* — one clear KPI to hit\n\n"
                "Be brutally honest and practical. No fluff."
            ),
            temp=0.8,
        )

        for chunk in split_for_telegram(f"📋 *برنامه هوشمند این هفته:*\n\n{body}"):
            try:
                await safe_reply(message, chunk)
            except Exception as exc:
                logger.error("Error in handler: %s", exc)
                await message.answer(chunk)

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════
# /templates — Save/Load Templates
# ═══════════════════════════════════════

@router.message(Command("templates"))
async def cmd_templates(message: Message) -> None:
    raw = extract_args(message.text or "", "/templates")

    tmps = _templates.get(message.chat.id, {})

    if not raw:
        if not tmps:
            await safe_reply(message, "📄 *قالب‌ها:*\n\n"
                "ذخیره قالب آگهی/کپشن برای استفاده مجدد:\n\n"
                "`/templates save [نام] | [متن قالب]`\n"
                "`/templates list` — لیست قالب‌ها\n"
                "`/templates use [نام]` — استفاده از قالب\n"
                "`/templates delete [نام]` — حذف")
        else:
            names = "\n".join(f"  📄 `{n}` — {t[:50]}..." for n, t in tmps.items())
            await safe_reply(message, f"📄 *قالب‌ها ({len(tmps)}):*\n\n{names}\n\n"
                "`/templates use [نام]`")
        return

    parts = raw.split(maxsplit=1)
    action = parts[0].lower()

    if action == "list":
        if not tmps:
            await message.answer("📄 قالبی ذخیره نشده.")
            return
        names = "\n".join(f"  📄 `{n}` — {t[:60]}..." for n, t in tmps.items())
        await safe_reply(message, f"📄 *قالب‌ها:*\n\n{names}")

    elif action == "save":
        data = parts[1] if len(parts) > 1 else ""
        if "|" not in data:
            await message.answer("❌ فرمت: `/templates save [نام] | [متن]`")
            return
        name, text = data.split("|", 1)
        name = name.strip()
        text = text.strip()
        _templates.setdefault(message.chat.id, {})[name] = text
        await message.answer(f"✅ قالب «{name}» ذخیره شد ({len(text)} کاراکتر).")

    elif action == "use":
        name = parts[1].strip() if len(parts) > 1 else ""
        if name in tmps:
            await safe_reply(message, f"📄 *قالب «{name}»:*\n\n{tmps[name]}")
        else:
            await message.answer(f"❌ قالب «{name}» پیدا نشد.")

    elif action == "delete":
        name = parts[1].strip() if len(parts) > 1 else ""
        if name in tmps:
            del tmps[name]
            await message.answer(f"🗑 قالب «{name}» حذف شد.")
        else:
            await message.answer(f"❌ قالب «{name}» پیدا نشد.")
    else:
        await message.answer("❌ `/templates save|list|use|delete`")


