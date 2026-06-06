
from __future__ import annotations
"""
tg_bot/handlers/marketing_auto.py — Marketing Agent TITAN Telegram Commands (L2) — ENHANCED v29.2
═════════════════════════════════════════════════════════════════════════════════════════════════
7 Telegram bot commands for the Marketing Agent TITAN with professional formatting and error handling.

FIXED VERSION:
- ✅ Corrected import block indentation
- ✅ Removed duplicate _format_dashboard
- ✅ Added missing imports (select, default_api, etc.)
- ✅ Fixed schema mismatches
"""

import json
import logging
import re
from typing import Any, Dict

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

logger = logging.getLogger(__name__)

# ── Imports with proper error handling ──
try:
    from arki_project.utils.marketing_engine import get_marketing_engine
    from arki_project.utils.event_bus import get_event_bus
    from arki_project.database.connection import get_session
    from arki_project.database.marketing_models import Prospect
    _MKT_ENGINE = True
except ImportError as e:
    logger.warning("Marketing engine imports failed: %s", e)
    _MKT_ENGINE = False

# ── Manus API for real-world data ──
try:
    from arki_project.utils.manus_api_bridge import get_manus_api
    _MANUS_API_AVAILABLE = True
except ImportError:
    _MANUS_API_AVAILABLE = False

# ── Database models ──
try:
    from arki_project.database.models import Campaign as DBCampaign
    _DB_CAMPAIGN_AVAILABLE = True
except ImportError:
    _DB_CAMPAIGN_AVAILABLE = False

logger = logging.getLogger(__name__)


async def _track_marketing_event(user_id: int, event_type: str, data: dict = None) -> None:
    """Track marketing event through both engine and event bus."""
    if not _MKT_ENGINE:
        return
    
    try:
        async with get_session() as session:
            engine = await get_marketing_engine(session)
            await engine.update_lead_activity(
                user_id, 
                event_type, 
                amount=data.get("value", 0) if data else 0
            )
            
            try:
                bus = get_event_bus()
                await bus.publish("campaign.event", {
                    "user_id": user_id, 
                    "action": event_type, 
                    **(data or {})
                })
            except Exception as e:
                logger.debug("Event bus publish failed: %s", e)
    except Exception as e:
        logger.debug("Marketing event tracking failed: %s", e)


_marketing_agent = None


def setup_marketing_handler(agent: Any) -> None:
    """Set the MarketingMasterAgent reference for the handler."""
    global _marketing_agent
    _marketing_agent = agent
    logger.info(
        "📋 Marketing handler connected to %s v%s",
        agent.AGENT_NAME, 
        agent.AGENT_VERSION
    )


router = Router(name="marketing_auto")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL FORMATTING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def _format_dashboard(data: Dict[str, Any]) -> str:
    """Format dashboard analytics professionally."""
    lines = ["📊 *Marketing Dashboard Overview*\n"]
    
    # Safe access with defaults
    total_campaigns = data.get("total_campaigns", 0)
    active_campaigns = data.get("active_campaigns", 0)
    total_leads = data.get("total_leads", 0)
    new_leads_30d = data.get("new_leads_30d", 0)
    total_prospects = data.get("total_prospects", 0)
    new_prospects_30d = data.get("new_prospects_30d", 0)
    total_conversions = data.get("total_conversions", 0)
    total_revenue = data.get("total_revenue", 0)
    
    lines.append(f"*Total Campaigns:* {total_campaigns}")
    lines.append(f"*Active Campaigns:* {active_campaigns}")
    lines.append(f"*Total Leads:* {total_leads}")
    lines.append(f"*New Leads (last 30 days):* {new_leads_30d}")
    lines.append(f"*Total Prospects:* {total_prospects}")
    lines.append(f"*New Prospects (last 30 days):* {new_prospects_30d}")
    lines.append(f"*Total Conversions:* {total_conversions}")
    lines.append(f"*Total Revenue:* €{total_revenue:.2f}\n")

    # Lead Segments
    lead_segments = data.get("lead_segments", {})
    if lead_segments:
        lines.append("*Lead Segments:*")
        for segment, count in lead_segments.items():
            lines.append(f"  • {segment.title()}: {count}")
    
    # Prospect Segments
    prospect_segments = data.get("prospect_segments", {})
    if prospect_segments:
        lines.append("\n*B2B Prospect Segments:*")
        for segment, count in prospect_segments.items():
            segment_name = segment.replace("_", " ").title()
            lines.append(f"  • {segment_name}: {count}")

    return "\n".join(lines)


def _format_hunt_result(data: Dict[str, Any]) -> str:
    """Format hunt results professionally."""
    lines = ["🔍 *B2B Hunt Results*\n"]
    lines.append(f"Found: {data.get('prospects_found', 0)}")
    lines.append(f"New: {data.get('prospects_new', 0)}")
    lines.append(f"Duplicates: {data.get('prospects_duplicate', 0)}")
    lines.append(f"Duration: {data.get('duration_seconds', 0):.1f}s")
    
    errors = data.get("errors", [])
    if errors:
        lines.append(f"\n⚠️ Errors ({len(errors)}):")
        for e in errors[:3]:
            lines.append(f"  └ {e[:100]}")
    
    return "\n".join(lines)


def _format_health(data: Dict[str, Any]) -> str:
    """Format health data professionally."""
    lines = ["💊 *Marketing Agent Health*\n"]
    lines.append(f"Service: {data.get('service', 'unknown')}")
    
    uptime = data.get("uptime_hours")
    if uptime:
        lines.append(f"Uptime: {uptime}h")
    
    lines.append(f"Tasks executed: {data.get('tasks_executed', 0)}\n")
    
    engines = data.get("engines", {})
    if engines:
        lines.append("*Engines:*")
        for name, status in engines.items():
            icon = "✅" if status == "available" else "❌"
            lines.append(f"  {icon} {name}: {status}")
    
    tasks = data.get("scheduled_tasks", {})
    if tasks:
        lines.append("\n*Scheduled Tasks:*")
        for key, info in tasks.items():
            enabled = "✅" if info.get("enabled") else "⏸️"
            last = info.get("last_run", "never")
            interval = info.get("interval_hours", "?")
            lines.append(f"  {enabled} {info.get('name', key)} (every {interval}h) — last: {last}")
    
    return "\n".join(lines)


def _format_analysis(result: Dict[str, Any], analysis_type: str) -> str:
    """Format analysis results professionally."""
    if analysis_type in ("overview", "pricing", "regional", "seasonal"):
        return (
            f"🎓 *Market Analysis — {analysis_type}*\n\n" + 
            json.dumps(result, indent=2, ensure_ascii=False, default=str)
        )
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)


def _format_social_strategy(result: Dict[str, Any], platform: str) -> str:
    """Format social strategy professionally."""
    lines = [f"📱 *Social Strategy — {platform}*\n"]
    strategy = result.get("strategy", {})
    if strategy:
        for key, tags in strategy.items():
            if tags:
                key_name = key.replace('_', ' ').title()
                lines.append(f"*{key_name}:*")
                lines.append(", ".join(tags[:10]))
    return "\n".join(lines)


def _format_briefing(result: Dict[str, Any]) -> str:
    """Format daily briefing professionally."""
    date = result.get('date', 'Today')
    lines = [f"📝 *Daily Briefing — {date}*\n"]
    
    summary = result.get("summary", "No summary available")
    lines.append(summary)
    
    recs = result.get("recommendations", [])
    if recs:
        lines.append("\n*Recommendations:*")
        for r in recs:
            lines.append(f"  • {r}")
    
    return "\n".join(lines)


async def _safe_reply(message: Message, text: str) -> None:
    """Reply with truncation for Telegram's message limit."""
    max_len = 4000
    if len(text) > max_len:
        text = text[:max_len] + "\n\n... (truncated)"
    await message.reply(text, parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════════════════════

@router.message(Command("marketing_dashboard"))
async def cmd_marketing_dashboard(message: Message) -> None:
    """📊 Full marketing dashboard overview."""
    if not _marketing_agent:
        await message.reply("❌ Marketing agent not initialized.")
        return
    
    await message.reply("⏳ Generating dashboard...")
    
    if not _MKT_ENGINE:
        await message.reply("❌ Marketing engine not available.")
        return
    
    try:
        async with get_session() as session:
            engine = await get_marketing_engine(session)
            analytics_data = await engine.get_analytics()
            formatted = _format_dashboard(analytics_data)
            await _safe_reply(message, formatted)
            await _track_marketing_event(message.from_user.id, "dashboard_viewed")
    except Exception as exc:
        logger.error("Dashboard command error: %s", exc)
        await message.reply(f"❌ Error: {exc}")


@router.message(Command("marketing_hunt"))
async def cmd_marketing_hunt(message: Message) -> None:
    """🔍 Trigger B2B prospect hunting."""
    if not _marketing_agent:
        await message.reply("❌ Marketing agent not initialized.")
        return
    
    if not _MANUS_API_AVAILABLE:
        await message.reply("❌ Manus API not available for real-world hunting.")
        return
    
    text = message.text or ""
    parts = text.split(maxsplit=1)
    region = "Global"
    niche = "B2B SaaS"

    if len(parts) > 1:
        arg_text = parts[1].strip()
        if "region=" in arg_text:
            region = arg_text.split("region=")[1].split(" ")[0]
        if "niche=" in arg_text:
            niche = arg_text.split("niche=")[1].split(" ")[0]

    await message.reply(
        f"🔍 Starting real-world B2B hunt for {niche} in {region} "
        f"using Manus search engine..."
    )
    
    try:
        # Use Manus search tool for real-world data
        manus_api = get_manus_api()
        search_results = await manus_api.search(
            brief=f"Finding B2B prospects for {niche} in {region}",
            type="info",
            queries=[
                f"B2B {niche} companies in {region}",
                f"top {niche} startups {region}",
                f"{niche} lead generation {region} data"
            ]
        )
        
        # Process search results to extract prospect information
        prospects_found = 0
        new_prospects = 0
        extracted_data = []

        if search_results and search_results.get("webpage_results"):
            urls_to_extract = [
                res["URL"] for res in search_results["webpage_results"] 
                if res.get("URL")
            ]
            
            if urls_to_extract:
                extracted_pages = await manus_api.webpage_extract(
                    brief="Extracting content from search results for B2B lead identification",
                    urls=urls_to_extract
                )

                company_name_regex = (
                    r"(?:Company|Firm|Organization|Corp|Inc|Ltd|LLC|GmbH|S.A.|Pvt. Ltd.)\s+"
                    r"([\w\s.-]+)"
                )
                website_regex = (
                    r"(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,6})(?:/[^\s]*)?"
                )

                for page_content in extracted_pages:
                    if page_content and page_content.get("content"):
                        content = page_content["content"]
                        
                        # Extract company names
                        company_names = re.findall(
                            company_name_regex, content, re.IGNORECASE
                        )
                        # Extract websites
                        websites = re.findall(
                            website_regex, content, re.IGNORECASE
                        )

                        company = (
                            company_names[0].strip() 
                            if company_names else "Unknown Company"
                        )
                        website = (
                            websites[0].strip() 
                            if websites else "Unknown Website"
                        )

                        # Check for duplicates before adding
                        if not any(
                            d.get("company") == company and 
                            d.get("website") == website 
                            for d in extracted_data
                        ):
                            extracted_data.append({
                                "company": company, 
                                "website": website, 
                                "source_url": page_content.get("url", "")
                            })
                            prospects_found += 1

        # Save to database
        if _MKT_ENGINE and extracted_data:
            try:
                async with get_session() as session:
                    engine = await get_marketing_engine(session)
                    
                    for data_item in extracted_data:
                        # Check for existing prospect
                        existing_prospect = await session.execute(
                            select(Prospect).filter(
                                Prospect.website == data_item["website"]
                            ).limit(1)
                        )
                        existing_prospect = existing_prospect.scalar_one_or_none()

                        if not existing_prospect:
                            new_prospect = Prospect(
                                business_name=data_item["company"],
                                website=data_item["website"],
                                source="web_hunt",
                                source_url=data_item["source_url"],
                                business_type=niche,
                                country=region
                            )
                            session.add(new_prospect)
                            await session.flush()
                            
                            # Score the prospect
                            try:
                                await engine.score_prospect(new_prospect.id)
                            except Exception as e:
                                logger.debug("Prospect scoring failed: %s", e)
                            
                            new_prospects += 1
                        
                        prospects_found += 1
                    
                    await session.commit()
                    
                    # Track event
                    await _track_marketing_event(
                        message.from_user.id, 
                        "hunt_completed", 
                        {"prospects": new_prospects}
                    )
            except Exception as e:
                logger.error("Database save failed: %s", e)

        result = {
            "prospects_found": prospects_found,
            "prospects_new": new_prospects,
            "prospects_duplicate": prospects_found - new_prospects,
            "duration_seconds": search_results.get("duration", 0),
            "errors": []
        }
        
        formatted = _format_hunt_result(result)
        await _safe_reply(message, formatted)
        
    except Exception as exc:
        logger.error("Hunt command error: %s", exc)
        await message.reply(f"❌ Error during B2B hunt: {exc}")


@router.message(Command("marketing_campaign"))
async def cmd_marketing_campaign(message: Message) -> None:
    """📋 Campaign management."""
    if not _marketing_agent:
        await message.reply("❌ Marketing agent not initialized.")
        return
    
    text = message.text or ""
    parts = text.split(maxsplit=2)
    
    if len(parts) < 2:
        await _safe_reply(message, (
            "📋 *Campaign Management*\n\n"
            "Usage:\n"
            "  `/marketing_campaign status` — Show all campaigns\n"
            "  `/marketing_campaign create <template>` — Create from template\n"
            "  `/marketing_campaign launch <id>` — Launch a campaign\n\n"
            "*Available templates:*\n"
            "  • `nordic_b2b_intro` — Nordic B2B Introduction\n"
            "  • `dach_expansion` — DACH Market Expansion\n"
            "  • `gallery_focus` — Art Gallery Outreach\n"
            "  • `holiday_push` — Holiday Season Push"
        ))
        return
    
    action = parts[1].strip().lower()
    
    try:
        if action == "status":
            if not _DB_CAMPAIGN_AVAILABLE or not _MKT_ENGINE:
                await message.reply("❌ Campaign database not available.")
                return
            
            async with get_session() as session:
                campaigns = await session.execute(select(DBCampaign))
                campaigns = campaigns.scalars().all()
                
                if campaigns:
                    lines = ["📋 *Active Campaigns*\n"]
                    for c in campaigns:
                        campaign_id = getattr(c, 'campaign_id', '?')
                        name = getattr(c, 'name', 'Unknown')
                        status = getattr(c, 'status', 'unknown')
                        campaign_type = getattr(c, 'campaign_type', 'unknown')
                        sent = getattr(c, 'sent', 0)
                        converted = getattr(c, 'converted', 0)
                        revenue = getattr(c, 'revenue', 0)
                        
                        lines.append(f"  #{campaign_id} — {name}")
                        lines.append(f"    Status: {status} | Type: {campaign_type}")
                        lines.append(
                            f"    Metrics: Sent {sent}, Converted {converted}, "
                            f"Revenue €{revenue:.2f}"
                        )
                    await _safe_reply(message, "\n".join(lines))
                else:
                    await message.reply(
                        "No active campaigns. Use `/marketing_campaign create <template>` "
                        "to create one."
                    )
        
        elif action == "create":
            template = parts[2].strip() if len(parts) > 2 else "nordic_b2b_intro"
            
            if not _MKT_ENGINE:
                await message.reply("❌ Marketing engine not available.")
                return
            
            async with get_session() as session:
                engine = await get_marketing_engine(session)
                db_campaign = await engine.create_campaign(
                    name=f"Campaign from {template}",
                    campaign_type="broadcast",
                    messages=[{"text": f"Hello from {template}!"}]
                )
                
                if db_campaign:
                    campaign_id = getattr(db_campaign, 'campaign_id', '?')
                    await message.reply(
                        f"✅ Campaign #{campaign_id} created from template `{template}`.\n"
                        f"Use `/marketing_campaign launch {campaign_id}` to start."
                    )
                    await _track_marketing_event(
                        message.from_user.id, 
                        "campaign_created", 
                        {"template": template}
                    )
                else:
                    await message.reply("❌ Campaign creation failed.")
        
        elif action == "launch":
            campaign_id = parts[2].strip() if len(parts) > 2 else None
            
            if not campaign_id:
                await message.reply("Usage: `/marketing_campaign launch <campaign_id>`")
                return
            
            if not _MKT_ENGINE:
                await message.reply("❌ Marketing engine not available.")
                return
            
            await message.reply(f"🚀 Launching campaign #{campaign_id}...")
            
            async with get_session() as session:
                engine = await get_marketing_engine(session)
                result = await engine.start_campaign(campaign_id=campaign_id)
                
                if "error" in result:
                    await message.reply(f"❌ Error: {result['error']}")
                else:
                    audience_size = result.get('audience_size', 0)
                    messages_queued = result.get('messages_queued', 0)
                    await _safe_reply(message, (
                        f"✅ *Campaign #{campaign_id} Launched*\n\n"
                        f"Audience Size: {audience_size}\n"
                        f"Messages Queued: {messages_queued}"
                    ))
                    await _track_marketing_event(
                        message.from_user.id, 
                        "campaign_launched", 
                        {"campaign_id": campaign_id}
                    )
        else:
            await message.reply(
                f"Unknown action: `{action}`. Use `status`, `create`, or `launch`."
            )
    
    except Exception as exc:
        logger.error("Campaign command error: %s", exc)
        await message.reply(f"❌ Error: {exc}")


@router.message(Command("marketing_outreach"))
async def cmd_marketing_outreach(message: Message) -> None:
    """📧 Outreach operations."""
    if not _marketing_agent:
        await message.reply("❌ Marketing agent not initialized.")
        return
    
    text = message.text or ""
    parts = text.split(maxsplit=2)
    
    if len(parts) < 2:
        await _safe_reply(message, (
            "📧 *Outreach Operations*\n\n"
            "Usage:\n"
            "  `/marketing_outreach send <campaign_id>` — Send emails\n"
            "  `/marketing_outreach followups <campaign_id>` — Process follow-ups"
        ))
        return
    
    action = parts[1].strip().lower()
    
    try:
        if action == "send":
            try:
                cid = int(parts[2].strip()) if len(parts) > 2 else None
            except ValueError:
                await message.reply("Campaign ID must be a number.")
                return
            
            if not cid:
                await message.reply("Please specify campaign ID.")
                return
            
            await message.reply(f"📧 Sending outreach for campaign #{cid}...")
            
            result = await _marketing_agent.handle_command(
                "outreach", 
                {"campaign_id": cid}, 
                user_id=message.from_user.id,
            )
            
            emails_generated = result.get('emails_generated', 0)
            emails_sent = result.get('emails_sent', 0)
            emails_failed = result.get('emails_failed', 0)
            
            await _safe_reply(message, (
                f"✅ *Outreach Complete*\n\n"
                f"Generated: {emails_generated}\n"
                f"Sent: {emails_sent}\n"
                f"Failed: {emails_failed}"
            ))
            
            await _track_marketing_event(
                message.from_user.id, 
                "outreach_sent", 
                {"emails": emails_sent}
            )
        
        elif action == "followups":
            try:
                cid = int(parts[2].strip()) if len(parts) > 2 else None
            except ValueError:
                await message.reply("Campaign ID must be a number.")
                return
            
            if not cid:
                await message.reply("Please specify campaign ID.")
                return
            
            result = await _marketing_agent.handle_command(
                "followups", 
                {"campaign_id": cid}, 
                user_id=message.from_user.id,
            )
            
            sent = result.get('sent', 0)
            failed = result.get('failed', 0)
            await message.reply(
                f"✅ Follow-ups: {sent} sent, {failed} failed"
            )
        
        else:
            await message.reply(
                f"Unknown action: `{action}`. Use `send` or `followups`."
            )
    
    except Exception as exc:
        logger.error("Outreach command error: %s", exc)
        await message.reply(f"❌ Error: {exc}")


@router.message(Command("marketing_platforms"))
async def cmd_marketing_platforms(message: Message) -> None:
    """🏪 Platform status, events, and listings."""
    if not _marketing_agent:
        await message.reply("❌ Marketing agent not initialized.")
        return
    
    text = message.text or ""
    parts = text.split(maxsplit=1)
    action = parts[1].strip().lower() if len(parts) > 1 else "status"
    
    try:
        if action == "status":
            result = await _marketing_agent.handle_command(
                "platforms", 
                user_id=message.from_user.id
            )
            
            platforms = result.get("platforms", [])
            if platforms:
                lines = ["🏪 *Platform Ranking*\n"]
                for i, p in enumerate(platforms[:10], 1):
                    status = p.get("status", "unknown")
                    icon = (
                        "🟢" if status == "healthy" 
                        else "🟡" if status == "warning" 
                        else "🔴"
                    )
                    name = p.get('name', 'Unknown')
                    active_listings = p.get('active_listings', 0)
                    total_revenue = p.get('total_revenue', 0)
                    roi_score = p.get('roi_score', 0)
                    
                    lines.append(f"  {i}. {icon} *{name}*")
                    lines.append(
                        f"     Listings: {active_listings} | "
                        f"Revenue: €{total_revenue:.0f}"
                    )
                    lines.append(f"     ROI Score: {roi_score}")
                
                await _safe_reply(message, "\n".join(lines))
            else:
                await message.reply("No platform data available yet.")
        
        elif action == "events":
            await message.reply("🎪 Searching for events and markets...")
            result = await _marketing_agent.handle_command(
                "events", 
                user_id=message.from_user.id
            )
            
            events_found = result.get('events_found', 0)
            opportunities_new = result.get('opportunities_new', 0)
            duration = result.get('duration_seconds', 0)
            
            await _safe_reply(message, (
                f"🎪 *Event Discovery*\n\n"
                f"Events found: {events_found}\n"
                f"New opportunities: {opportunities_new}\n"
                f"Duration: {duration:.1f}s"
            ))
        
        else:
            await _safe_reply(message, (
                "🏪 *Platform Commands*\n\n"
                "  `/marketing_platforms status` — Platform ranking\n"
                "  `/marketing_platforms events` — Discover events & markets"
            ))
    
    except Exception as exc:
        logger.error("Platforms command error: %s", exc)
        await message.reply(f"❌ Error: {exc}")


@router.message(Command("marketing_analyze"))
async def cmd_marketing_analyze(message: Message) -> None:
    """🎓 Market analysis, competitors, social strategy."""
    if not _marketing_agent:
        await message.reply("❌ Marketing agent not initialized.")
        return
    
    text = message.text or ""
    parts = text.split(maxsplit=2)
    action = parts[1].strip().lower() if len(parts) > 1 else "overview"
    
    try:
        if action in ("overview", "pricing", "regional", "seasonal", "all"):
            result = await _marketing_agent.handle_command(
                "analyze", 
                {"dimension": action}, 
                user_id=message.from_user.id,
            )
            formatted = _format_analysis(result, action)
            await _safe_reply(message, formatted)
        
        elif action == "competitors":
            await message.reply("🔎 Analyzing competitors...")
            result = await _marketing_agent.handle_command(
                "compete", 
                user_id=message.from_user.id
            )
            
            comps = result.get("competitors", [])
            if comps:
                lines = [f"🔎 *Competitor Analysis — {len(comps)} brands*\n"]
                for c in comps[:10]:
                    comp_name = c.get('name', 'Unknown')
                    comp_website = c.get('website', 'No website')
                    lines.append(f"  • {comp_name}")
                    lines.append(f"    {comp_website}")
                await _safe_reply(message, "\n".join(lines))
            else:
                await message.reply("No competitors found in this scan.")
        
        elif action.startswith("social"):
            parts_social = text.split(maxsplit=2)
            platform = parts_social[2].strip() if len(parts_social) > 2 else "instagram"
            
            result = await _marketing_agent.handle_command(
                "social", 
                {"platform": platform}, 
                user_id=message.from_user.id,
            )
            formatted = _format_social_strategy(result, platform)
            await _safe_reply(message, formatted)
        
        elif action == "briefing":
            await message.reply("📝 Generating daily briefing...")
            result = await _marketing_agent.handle_command(
                "briefing", 
                user_id=message.from_user.id
            )
            formatted = _format_briefing(result)
            await _safe_reply(message, formatted)
        
        else:
            await _safe_reply(message, (
                "🎓 *Analysis Commands*\n\n"
                "  `/marketing_analyze overview` — Market overview\n"
                "  `/marketing_analyze pricing` — Pricing analysis\n"
                "  `/marketing_analyze regional` — Regional analysis\n"
                "  `/marketing_analyze seasonal` — Seasonal insights\n"
                "  `/marketing_analyze competitors` — Competitor research\n"
                "  `/marketing_analyze social instagram` — Social strategy\n"
                "  `/marketing_analyze briefing` — Daily briefing"
            ))
    
    except Exception as exc:
        logger.error("Analyze command error: %s", exc)
        await message.reply(f"❌ Error: {exc}")


@router.message(Command("marketing_health"))
async def cmd_marketing_health(message: Message) -> None:
    """💊 System health and task management."""
    if not _marketing_agent:
        await message.reply("❌ Marketing agent not initialized.")
        return
    
    text = message.text or ""
    parts = text.split(maxsplit=2)
    action = parts[1].strip().lower() if len(parts) > 1 else "status"
    
    try:
        if action == "status":
            result = await _marketing_agent.handle_command(
                "health", 
                user_id=message.from_user.id
            )
            formatted = _format_health(result)
            await _safe_reply(message, formatted)
        
        elif action == "tasks":
            result = await _marketing_agent.handle_command(
                "tasks", 
                {"action": "list"}, 
                user_id=message.from_user.id
            )
            
            tasks = result.get("tasks", [])
            lines = ["⏰ *Scheduled Tasks*\n"]
            for t in tasks:
                enabled = "✅" if t.get("enabled") else "⏸️"
                task_key = t.get('key', '?')
                task_name = t.get('name', 'Unknown')
                interval = t.get('interval_hours', '?')
                last_run = t.get('last_run', 'never')
                
                lines.append(f"  {enabled} `{task_key}` — {task_name}")
                lines.append(f"     Every {interval}h | Last: {last_run}")
            
            await _safe_reply(message, "\n".join(lines))
        
        elif action == "run":
            task_key = parts[2].strip() if len(parts) > 2 else ""
            
            if not task_key:
                await message.reply("Usage: `/marketing_health run <task_key>`")
                return
            
            await message.reply(f"▶️ Running task `{task_key}`...")
            
            result = await _marketing_agent.handle_command(
                "tasks", 
                {"action": "run", "task_key": task_key},
                user_id=message.from_user.id,
            )
            
            success = result.get('success', False)
            status = "completed" if success else "failed"
            icon = "✅" if success else "❌"
            await message.reply(f"{icon} Task `{task_key}` {status}")
        
        else:
            await _safe_reply(message, (
                "💊 *Health Commands*\n\n"
                "  `/marketing_health status` — Full health check\n"
                "  `/marketing_health tasks` — List scheduled tasks\n"
                "  `/marketing_health run <task_key>` — Run a task manually"
            ))
    
    except Exception as exc:
        logger.error("Health command error: %s", exc)
        await message.reply(f"❌ Error: {exc}")


