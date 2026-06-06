
"""
handlers/all_commands.py — Unified command router
Registers ALL slash commands and routes them through command_engine.
"""
import logging

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import Message

from arki_project.utils.command_engine import execute_command, PROMPTS, NO_INPUT_COMMANDS
from arki_project.utils.safe_send import safe_reply, safe_edit_text
from arki_project.utils.models_registry import split_for_telegram
from arki_project.exceptions import HandlerError

logger = logging.getLogger(__name__)
router = Router(name="all_commands")


def _extract_args(text: str, cmd: str) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


async def _handle_command(message: Message, action: str) -> None:
    """Generic command handler."""
    uid = message.from_user.id if message.from_user else 0
    text = _extract_args(message.text or "", f"/{action}")

    # For commands that need input but none given
    if not text and action not in NO_INPUT_COMMANDS and action not in ("quote", "password", "settings", "autotune"):
        result = await execute_command(uid, action, "")
        await safe_reply(message, result)
        return

    # Show typing for AI commands
    if action in PROMPTS or action in ("search", "deep", "weather", "currency", "trending", "benchmark", "rss"):
        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        status = await message.answer("🧠 در حال پردازش...")
        try:
            result = await execute_command(uid, action, text, timeout=30)
            try:
                await status.delete()
            except:
                pass
            for chunk in split_for_telegram(result):
                try:
                    await safe_reply(message, chunk)
                except:
                    await message.answer(chunk[:4000], parse_mode=None)
        except HandlerError as e:
            logger.error("Command %s error: %s", action, e)
            await safe_edit_text(status, f"❌ خطا: {str(e)[:100]}")
    else:
        result = await execute_command(uid, action, text)
        await safe_reply(message, result)


# ═══════════════════════════════════════
# Register ALL commands
# ═══════════════════════════════════════

# AI Tools
@router.message(Command("translate"))
async def cmd_translate(m: Message, **kw): await _handle_command(m, "translate")

@router.message(Command("summarize"))
async def cmd_summarize(m: Message, **kw): await _handle_command(m, "summarize")

@router.message(Command("code"))
async def cmd_code(m: Message, **kw): await _handle_command(m, "code")

@router.message(Command("explain"))
async def cmd_explain(m: Message, **kw): await _handle_command(m, "explain")

@router.message(Command("math"))
async def cmd_math(m: Message, **kw): await _handle_command(m, "math")

@router.message(Command("brainstorm"))
async def cmd_brainstorm(m: Message, **kw): await _handle_command(m, "brainstorm")

@router.message(Command("polish"))
async def cmd_polish(m: Message, **kw): await _handle_command(m, "polish")

@router.message(Command("rewrite"))
async def cmd_rewrite(m: Message, **kw): await _handle_command(m, "rewrite")

# Content Studio
@router.message(Command("brand"))
async def cmd_brand(m: Message, **kw): await _handle_command(m, "brand")

@router.message(Command("catalog"))
async def cmd_catalog(m: Message, **kw): await _handle_command(m, "catalog")

@router.message(Command("content"))
async def cmd_content(m: Message, **kw): await _handle_command(m, "content")

@router.message(Command("caption"))
async def cmd_caption(m: Message, **kw): await _handle_command(m, "caption")

@router.message(Command("hashtag"))
async def cmd_hashtag(m: Message, **kw): await _handle_command(m, "hashtag")

@router.message(Command("batch"))
async def cmd_batch(m: Message, **kw): await _handle_command(m, "batch")

@router.message(Command("story"))
async def cmd_story(m: Message, **kw): await _handle_command(m, "story")

@router.message(Command("abtest"))
async def cmd_abtest(m: Message, **kw): await _handle_command(m, "abtest")

@router.message(Command("studio"))
async def cmd_studio(m: Message, **kw): await _handle_command(m, "dashboard")

# Sales Engine
@router.message(Command("funnel"))
async def cmd_funnel(m: Message, **kw): await _handle_command(m, "funnel")

@router.message(Command("buyer"))
async def cmd_buyer(m: Message, **kw): await _handle_command(m, "buyer")

@router.message(Command("repurpose"))
async def cmd_repurpose(m: Message, **kw): await _handle_command(m, "repurpose")

@router.message(Command("launch"))
async def cmd_launch(m: Message, **kw): await _handle_command(m, "launch")

@router.message(Command("seasonal"))
async def cmd_seasonal(m: Message, **kw): await _handle_command(m, "seasonal")

@router.message(Command("seo"))
async def cmd_seo(m: Message, **kw): await _handle_command(m, "seo")

@router.message(Command("email"))
async def cmd_email(m: Message, **kw): await _handle_command(m, "email")

@router.message(Command("pricing"))
async def cmd_pricing(m: Message, **kw): await _handle_command(m, "pricing")

@router.message(Command("viral"))
async def cmd_viral(m: Message, **kw): await _handle_command(m, "viral")

@router.message(Command("collab"))
async def cmd_collab(m: Message, **kw): await _handle_command(m, "collab")

@router.message(Command("ads"))
async def cmd_ads(m: Message, **kw): await _handle_command(m, "ads")

@router.message(Command("social"))
async def cmd_social(m: Message, **kw): await _handle_command(m, "social")

@router.message(Command("swipe"))
async def cmd_swipe(m: Message, **kw): await _handle_command(m, "swipe")

@router.message(Command("competitor"))
async def cmd_competitor(m: Message, **kw): await _handle_command(m, "competitor")

@router.message(Command("megapost"))
async def cmd_megapost(m: Message, **kw): await _handle_command(m, "megapost")

# Content Brain
@router.message(Command("optimize"))
async def cmd_optimize(m: Message, **kw): await _handle_command(m, "optimize")

@router.message(Command("trending"))
async def cmd_trending(m: Message, **kw): await _handle_command(m, "trending")

@router.message(Command("contentai"))
async def cmd_contentai(m: Message, **kw): await _handle_command(m, "contentai")

@router.message(Command("aesthetic"))
async def cmd_aesthetic(m: Message, **kw): await _handle_command(m, "aesthetic")

@router.message(Command("series"))
async def cmd_series(m: Message, **kw): await _handle_command(m, "series")

@router.message(Command("hook"))
async def cmd_hook(m: Message, **kw): await _handle_command(m, "hook")

@router.message(Command("carousel"))
async def cmd_carousel(m: Message, **kw): await _handle_command(m, "carousel")

@router.message(Command("cta"))
async def cmd_cta(m: Message, **kw): await _handle_command(m, "cta")

@router.message(Command("contentaudit"))
async def cmd_contentaudit(m: Message, **kw): await _handle_command(m, "contentaudit")

# Sales Brain
@router.message(Command("salesai"))
async def cmd_salesai(m: Message, **kw): await _handle_command(m, "salesai")

@router.message(Command("upsell"))
async def cmd_upsell(m: Message, **kw): await _handle_command(m, "upsell")

@router.message(Command("bundle"))
async def cmd_bundle(m: Message, **kw): await _handle_command(m, "bundle")

@router.message(Command("retention"))
async def cmd_retention(m: Message, **kw): await _handle_command(m, "retention")

@router.message(Command("winback"))
async def cmd_winback(m: Message, **kw): await _handle_command(m, "winback")

@router.message(Command("loyalty"))
async def cmd_loyalty(m: Message, **kw): await _handle_command(m, "loyalty")

@router.message(Command("forecast"))
async def cmd_forecast(m: Message, **kw): await _handle_command(m, "forecast")

@router.message(Command("objection"))
async def cmd_objection(m: Message, **kw): await _handle_command(m, "objection")

@router.message(Command("giftguide"))
async def cmd_giftguide(m: Message, **kw): await _handle_command(m, "giftguide")

@router.message(Command("profit"))
async def cmd_profit(m: Message, **kw): await _handle_command(m, "profit")

# Platforms
@router.message(Command("connect"))
async def cmd_connect(m: Message, **kw): await _handle_command(m, "connect")

@router.message(Command("publish"))
async def cmd_publish(m: Message, **kw): await _handle_command(m, "publish")

@router.message(Command("shopmanage"))
async def cmd_shopmanage(m: Message, **kw): await _handle_command(m, "shopmanage")

@router.message(Command("euromarket"))
async def cmd_euromarket(m: Message, **kw): await _handle_command(m, "euromarket")

@router.message(Command("listing"))
async def cmd_listing(m: Message, **kw): await _handle_command(m, "listing")

@router.message(Command("analyze"))
async def cmd_analyze(m: Message, **kw): await _handle_command(m, "analyze")

# Product Auto
@router.message(Command("addproduct"))
async def cmd_addproduct(m: Message, **kw): await _handle_command(m, "addproduct")

@router.message(Command("editproduct"))
async def cmd_editproduct(m: Message, **kw): await _handle_command(m, "editproduct")

@router.message(Command("delproduct"))
async def cmd_delproduct(m: Message, **kw): await _handle_command(m, "addproduct")

@router.message(Command("autopipeline"))
async def cmd_autopipeline(m: Message, **kw): await _handle_command(m, "autopipeline")

# Automation
@router.message(Command("remind"))
async def cmd_remind(m: Message, **kw): await _handle_command(m, "remind")

@router.message(Command("qr"))
async def cmd_qr(m: Message, **kw): await _handle_command(m, "qr")

@router.message(Command("short"))
async def cmd_short(m: Message, **kw): await _handle_command(m, "short")

@router.message(Command("weather"))
async def cmd_weather(m: Message, **kw): await _handle_command(m, "weather")

@router.message(Command("currency"))
async def cmd_currency(m: Message, **kw): await _handle_command(m, "currency")

@router.message(Command("rss"))
async def cmd_rss(m: Message, **kw): await _handle_command(m, "rss")

@router.message(Command("note"))
async def cmd_note(m: Message, **kw): await _handle_command(m, "note")

@router.message(Command("quote"))
async def cmd_quote(m: Message, **kw): await _handle_command(m, "quote")

@router.message(Command("password"))
async def cmd_password(m: Message, **kw): await _handle_command(m, "password")

# Agents
@router.message(Command("workflow"))
async def cmd_workflow(m: Message, **kw): await _handle_command(m, "workflow")

@router.message(Command("crm"))
async def cmd_crm(m: Message, **kw): await _handle_command(m, "crm")

@router.message(Command("finance"))
async def cmd_finance(m: Message, **kw): await _handle_command(m, "finance")

@router.message(Command("monitor"))
async def cmd_monitor(m: Message, **kw): await _handle_command(m, "monitor")

@router.message(Command("autoreply"))
async def cmd_autoreply(m: Message, **kw): await _handle_command(m, "autoreply")

@router.message(Command("plan"))
async def cmd_plan(m: Message, **kw): await _handle_command(m, "plan")

@router.message(Command("calendar"))
async def cmd_calendar(m: Message, **kw): await _handle_command(m, "calendar")

@router.message(Command("template"))
async def cmd_template(m: Message, **kw): await _handle_command(m, "template")

@router.message(Command("benchmark"))
async def cmd_benchmark(m: Message, **kw): await _handle_command(m, "benchmark")

@router.message(Command("schedule"))
async def cmd_schedule(m: Message, **kw): await _handle_command(m, "schedule")

@router.message(Command("reviews"))
async def cmd_reviews(m: Message, **kw): await _handle_command(m, "reviews")

@router.message(Command("inventory"))
async def cmd_inventory(m: Message, **kw): await _handle_command(m, "inventory")

# Visual/Design
@router.message(Command("image"))
async def cmd_image(m: Message, **kw): await _handle_command(m, "image")

@router.message(Command("design"))
async def cmd_design(m: Message, **kw): await _handle_command(m, "design")

@router.message(Command("poster"))
async def cmd_poster(m: Message, **kw): await _handle_command(m, "poster")

@router.message(Command("mockup"))
async def cmd_mockup(m: Message, **kw): await _handle_command(m, "mockup")

@router.message(Command("logo"))
async def cmd_logo(m: Message, **kw): await _handle_command(m, "logo")

@router.message(Command("moodboard"))
async def cmd_moodboard(m: Message, **kw): await _handle_command(m, "moodboard")

@router.message(Command("banner"))
async def cmd_banner(m: Message, **kw): await _handle_command(m, "banner")

@router.message(Command("infographic"))
async def cmd_infographic(m: Message, **kw): await _handle_command(m, "infographic")

@router.message(Command("photoedit"))
async def cmd_photoedit(m: Message, **kw): await _handle_command(m, "photoedit")

@router.message(Command("htmlpage"))
async def cmd_htmlpage(m: Message, **kw): await _handle_command(m, "htmlpage")

@router.message(Command("exportcsv"))
async def cmd_exportcsv(m: Message, **kw): await _handle_command(m, "exportcsv")

# Victor AI
@router.message(Command("victor"))
async def cmd_victor(m: Message, **kw): await _handle_command(m, "victor")

@router.message(Command("debate"))
async def cmd_debate(m: Message, **kw): await _handle_command(m, "debate")

# Marketing TITAN
@router.message(Command("marketing_dashboard"))
async def cmd_mktg_dash(m: Message, **kw): await _handle_command(m, "marketing_dashboard")

@router.message(Command("marketing_hunt"))
async def cmd_mktg_hunt(m: Message, **kw): await _handle_command(m, "marketing_hunt")

@router.message(Command("marketing_campaign"))
async def cmd_mktg_campaign(m: Message, **kw): await _handle_command(m, "marketing_campaign")

@router.message(Command("marketing_outreach"))
async def cmd_mktg_outreach(m: Message, **kw): await _handle_command(m, "marketing_outreach")

@router.message(Command("marketing_analyze"))
async def cmd_mktg_analyze(m: Message, **kw): await _handle_command(m, "marketing_analyze")

@router.message(Command("marketing_health"))
async def cmd_mktg_health(m: Message, **kw): await _handle_command(m, "marketing_health")

@router.message(Command("marketing_platforms"))
async def cmd_mktg_platforms(m: Message, **kw): await _handle_command(m, "marketing_platforms")

# Compare/Consensus
@router.message(Command("compare"))
async def cmd_compare(m: Message, **kw): await _handle_command(m, "compare")

@router.message(Command("consensus"))
async def cmd_consensus(m: Message, **kw): await _handle_command(m, "consensus")

# Model/Settings (lightweight versions)
@router.message(Command("model"))
async def cmd_model(m: Message, **kw): await _handle_command(m, "model")

@router.message(Command("persona"))
async def cmd_persona(m: Message, **kw): await _handle_command(m, "model")

@router.message(Command("settings"))
async def cmd_settings(m: Message, **kw): await _handle_command(m, "settings")

@router.message(Command("autotune"))
async def cmd_autotune(m: Message, **kw): await _handle_command(m, "autotune")

# Other
@router.message(Command("dashboard"))
async def cmd_dashboard(m: Message, **kw): await _handle_command(m, "dashboard")

@router.message(Command("subscribe"))
async def cmd_subscribe(m: Message, **kw): await _handle_command(m, "subscribe")

@router.message(Command("upgrade"))
async def cmd_upgrade(m: Message, **kw): await _handle_command(m, "upgrade")

@router.message(Command("products"))
async def cmd_products(m: Message, **kw): await _handle_command(m, "products")

@router.message(Command("platforms"))
async def cmd_platforms(m: Message, **kw): await _handle_command(m, "platforms")

@router.message(Command("templates"))
async def cmd_templates(m: Message, **kw): await _handle_command(m, "templates")

# ── Claude Ultra ──
@router.message(Command("claude_ultra"))
async def cmd_claude_ultra(m: Message, **kw): await _handle_command(m, "claude_ultra")


