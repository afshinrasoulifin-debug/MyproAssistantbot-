
from __future__ import annotations
"""


tg_bot/handlers/create.py
─────────────────────────
File & Document Creation Engine:

  /create    — Generate files (html, csv, json, py, txt, md, etc.)
  /htmlpage  — Complete landing page generator
  /exportcsv — Export CRM/sales data to CSV
"""


import csv
import io
import logging
import re

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from arki_project.config import Settings
from arki_project.utils.ai_client import AIClient
from arki_project.utils.models_registry import (
    user_friendly_error,
    working_model_key,
)
from arki_project.utils.safe_send import safe_delete, safe_reply
from arki_project.handlers.shared import extract_args, brand_ctx, products_ctx
from arki_project.utils.data_store import store
from arki_project.utils.v7_core import (


# ── Infrastructure access (injected by middleware) ──

# Access via data["infra_registry"], data["infra_event_bus"], data["infra_config"]

    enhance_system_prompt, store_result,
)

logger = logging.getLogger(__name__)
router = Router(name="create")

_EXT_MAP = {
    "html": "html", "htm": "html", "css": "css", "js": "javascript",
    "py": "python", "python": "python", "csv": "csv", "json": "json",
    "xml": "xml", "txt": "txt", "md": "markdown", "sql": "sql",
    "sh": "sh", "yaml": "yaml", "yml": "yaml", "java": "java",
    "cpp": "cpp", "c": "c",
}


@router.message(Command("create"))
async def cmd_create(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip():
        await safe_reply(message, "✍️ *ساخت فایل — حرفه‌ای:*\n\n"
            "`/create [نوع فایل] توضیح محتوا`\n\n"
            "*انواع فایل:*\n"
            "  `html` — صفحه وب / لندینگ\n"
            "  `css` — استایل‌شیت\n"
            "  `js` — جاوااسکریپت\n"
            "  `py` — اسکریپت پایتون\n"
            "  `csv` — جدول داده\n"
            "  `json` — داده ساختاریافته\n"
            "  `md` — مقاله مارک‌داون\n"
            "  `txt` — متن ساده\n"
            "  `sql` — دیتابیس\n\n"
            "*مثال‌ها:*\n"
            "`/create html لندینگ پیج شمع با طرح لوکس`\n"
            "`/create csv لیست ۲۰ ایده محتوای اینستاگرام`\n"
            "`/create py اسکریپت وب اسکرپر ساده`\n"
            "`/create json منوی رستوران با ۱۰ آیتم`\n"
            "`/create md مقاله درباره فواید شمع سویا`")
        return

    body = raw[1].strip()
    user_id = message.from_user.id  # type: ignore[union-attr]

    words = body.split(maxsplit=1)
    first_word = words[0].lower().strip(".")
    if first_word in _EXT_MAP and len(words) >= 2:
        ext = _EXT_MAP[first_word]
        description = words[1]
    else:
        ext = "txt"
        description = body

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT,
    )

    try:
        cfg = await ai_client.get_user_config(user_id)
        mk = working_model_key(
            cfg["model"], settings.ai_api_key, settings.groq_api_key,
        )

        # Enhanced system prompt based on file type
        type_hints = {
            "html": "Create a complete, modern, responsive HTML page with inline CSS and JS. Use Tailwind CDN if needed. Make it visually stunning.",
            "csv": "Generate a CSV with headers. Use comma separator. Make realistic, useful data.",
            "json": "Generate valid JSON. Make it well-structured with realistic data.",
            "python": "Write clean, documented Python code with type hints. Include if __name__ == '__main__' block.",
            "markdown": "Write well-formatted Markdown with headers, lists, and emphasis.",
        }

        sys_prompt = (
            f"Generate ONLY the file content for a .{ext} file. "
            "No explanations, no markdown code blocks around the content. "
            "Just the raw file content, ready to save. "
            f"{type_hints.get(ext, 'Make it professional and complete.')} "
            "Make it professional, complete, and production-ready."
        )

        # Inject brand context for relevant file types
        user_prompt = description
        bctx = brand_ctx(message.chat.id)
        if bctx and ext in ("html", "markdown", "txt", "csv"):
            user_prompt = f"{description}\n\nBrand context:\n{bctx}"

        import time as _t; _t0 = _t.time()
        content = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": enhance_system_prompt(sys_prompt, user_text=message.text or "", user_id=str(message.from_user.id) if message.from_user else "0")},
                {"role": "user", "content": user_prompt},
            ],
            model_key=mk,
            temperature=0.3,
            max_tokens=8192,
        )

        # Strip any markdown code fences
        content = re.sub(r"^```\w*\n?", "", content.strip())
        content = re.sub(r"\n?```$", "", content.strip())

        filename = f"arki_output.{ext}"
        doc = BufferedInputFile(
            content.encode("utf-8"), filename=filename,
        )

        store_result(message.from_user.id if message.from_user else 0, (message.text or "")[:300], content[:500] if content else "", "create", duration_s=_t.time()-_t0)
        await message.answer_document(
            document=doc,
            caption=f"✍️ *{filename}* — ساخته شد!\n_{description[:100]}_",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════
# /htmlpage — Complete Landing Page Generator
# ═══════════════════════════════════════

@router.message(Command("htmlpage"))
async def cmd_htmlpage(
    message: Message, ai_client: AIClient, settings: Settings,
) -> None:
    """Generate a complete landing page HTML file."""
    raw = extract_args(message.text or "", "/htmlpage")

    if not raw:
        await safe_reply(message, "🌐 *لندینگ‌پیج‌ساز — صفحه فروش کامل:*\n\n"
            "`/htmlpage [محصول/برند] | [نوع]`\n\n"
            "*انواع صفحه:*\n"
            "  `product` — صفحه محصول\n"
            "  `landing` — لندینگ فروش\n"
            "  `portfolio` — نمونه‌کار\n"
            "  `catalog` — کاتالوگ محصولات\n"
            "  `coming` — به‌زودی (Coming Soon)\n\n"
            "*مثال:*\n"
            "`/htmlpage شمع ارکی | landing`\n"
            "`/htmlpage Arki Candles | product`\n"
            "`/htmlpage all شمع ارکی` برای *همه ۵ نوع*")
        return

    parts = [p.strip() for p in raw.split("|")]
    brand = parts[0]
    page_type = parts[1].lower().strip() if len(parts) > 1 else "landing"

    gen_all = brand.lower().startswith("all ")
    if gen_all:
        brand = brand[4:].strip()

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT,
    )

    cfg = await ai_client.get_user_config(message.from_user.id)  # type: ignore[union-attr]
    mk = working_model_key(cfg["model"], settings.ai_api_key, settings.groq_api_key)

    page_types = {
        "product": "single product page with hero image, features, testimonials, buy CTA",
        "landing": "high-converting sales landing page with hero, benefits, social proof, pricing, FAQ, CTA",
        "portfolio": "portfolio/showcase page with gallery grid, about section, contact form",
        "catalog": "product catalog page with filter/sort, product cards grid, cart button",
        "coming": "beautiful coming soon page with countdown timer, email signup, social links",
    }

    bctx = brand_ctx(message.chat.id)
    pctx = products_ctx(message.chat.id)

    async def _gen_page(ptype: str) -> None:
        pdesc = page_types.get(ptype, page_types["landing"])
        html = await ai_client.ask_raw(
            messages=[
                {"role": "system", "content": (
                    "You are an expert web designer. Generate a COMPLETE, beautiful, responsive HTML page. "
                    "Use Tailwind CSS via CDN. Include all CSS inline or via CDN. "
                    "Make it modern, professional, and visually stunning. "
                    "Include smooth scroll, hover effects, gradient backgrounds. "
                    "Use Persian text for content, English for brand names. "
                    "Add Font Awesome icons via CDN. "
                    "Output ONLY the HTML — no explanations, no markdown fences."
                )},
                {"role": "user", "content": (
                    f"Create a {pdesc} for brand '{brand}'.\n"
                    f"{f'Brand info: {bctx}' if bctx else ''}\n"
                    f"{f'Products: {pctx}' if pctx else ''}\n"
                    "Make it ready to deploy. Include realistic content."
                )},
            ],
            model_key=mk, temperature=0.4, max_tokens=8192,
        )
        html = re.sub(r"^```\w*\n?", "", html.strip())
        html = re.sub(r"\n?```$", "", html.strip())

        fname = f"arki_{ptype}.html"
        doc = BufferedInputFile(html.encode("utf-8"), filename=fname)
        await message.answer_document(
            document=doc,
            caption=f"🌐 *{fname}* — {ptype}\n_صفحه {brand}_",
            parse_mode="Markdown",
        )

    try:
        if gen_all:
            status = await message.answer("🌐 دارم ۵ صفحه وب می‌سازم...")
            for pt in page_types:
                try:
                    await _gen_page(pt)
                except Exception as exc:
                    await message.answer(f"❌ {pt}: {exc}")
            try:
                await safe_delete(status)
            except Exception as e:
                logger.debug("Suppressed: %s", e)
        else:
            status = await message.answer(f"🌐 ساخت صفحه {page_type}...")
            await _gen_page(page_type)
            try:
                await safe_delete(status)
            except Exception as e:
                logger.debug("Suppressed: %s", e)
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(user_friendly_error(exc))


# ═══════════════════════════════════════
# /exportcsv — Export CRM/Sales Data
# ═══════════════════════════════════════

@router.message(Command("exportcsv"))
async def cmd_exportcsv(message: Message) -> None:
    """Export CRM customers or sales data to CSV."""
    raw = extract_args(message.text or "", "/exportcsv")

    if not raw or raw == "help":
        await safe_reply(message, "📤 *خروجی CSV — داده‌های شما:*\n\n"
            "`/exportcsv products` — لیست محصولات\n"
            "`/exportcsv sales` — گزارش فروش\n"
            "`/exportcsv catalog` — کاتالوگ کامل\n"
            "`/exportcsv all` — همه داده‌ها")
        return

    chat_id = message.chat.id
    action = raw.lower().strip()

    await message.bot.send_chat_action(  # type: ignore[union-attr]
        chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT,
    )

    try:
        if action in ("products", "all"):
            products = store.get_products(chat_id)
            if products:
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(["ID", "Name", "Price", "Description", "Category"])
                for pid, p in products.items():
                    writer.writerow([
                        pid,
                        p.get("name", ""),
                        p.get("price", ""),
                        p.get("description", ""),
                        p.get("category", ""),
                    ])
                doc = BufferedInputFile(
                    buf.getvalue().encode("utf-8-sig"),
                    filename="arki_products.csv",
                )
                await message.answer_document(
                    document=doc,
                    caption=f"📤 *محصولات* — {len(products)} آیتم",
                    parse_mode="Markdown",
                )
            elif action != "all":
                await safe_reply(message, "📭 هنوز محصولی ثبت نشده.\n`/catalog add نام | قیمت | توضیح`")

        if action in ("sales", "all"):
            sales = store.get_sales(chat_id)
            if sales:
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(["Name", "Quantity", "Revenue", "Date"])
                for s in sales:
                    writer.writerow([
                        s.get("name", ""),
                        s.get("qty", 0),
                        s.get("revenue", 0),
                        s.get("date", ""),
                    ])
                doc = BufferedInputFile(
                    buf.getvalue().encode("utf-8-sig"),
                    filename="arki_sales.csv",
                )
                await message.answer_document(
                    document=doc,
                    caption=f"📤 *فروش* — {len(sales)} رکورد",
                    parse_mode="Markdown",
                )
            elif action != "all":
                await safe_reply(message, "📭 هنوز فروشی ثبت نشده.")

        if action in ("catalog", "all"):
            catalog = store.get_catalog(chat_id)
            if catalog:
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(["Name", "Price", "Description", "Image"])
                for item in catalog:
                    writer.writerow([
                        item.get("name", ""),
                        item.get("price", ""),
                        item.get("description", ""),
                        item.get("image", ""),
                    ])
                doc = BufferedInputFile(
                    buf.getvalue().encode("utf-8-sig"),
                    filename="arki_catalog.csv",
                )
                await message.answer_document(
                    document=doc,
                    caption=f"📤 *کاتالوگ* — {len(catalog)} آیتم",
                    parse_mode="Markdown",
                )



            elif action != "all":
                await safe_reply(message, "📭 هنوز کاتالوگی نیست.\n`/catalog add نام | قیمت | توضیح`")

        if action not in ("products", "sales", "catalog", "all"):
            await safe_reply(message, "❌ نوع نامعتبر.\n`/exportcsv products|sales|catalog|all`")

    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await message.answer(f"❌ {exc}")


