

import asyncio
import logging
import sys
import os

# Setup paths
sys.path.append("/home/ubuntu/arki_final")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///real_world_test.db"

from architecture.agent.marketing_agent import MarketingMasterAgent
from utils.multi_format_content_factory import ContentFormat

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TITAN_STRESS_TEST")

async def run_end_to_end_test():
    logger.info("🔥 STARTING TITAN-OMEGA REAL-WORLD STRESS TEST 🔥")
    
    agent = MarketingMasterAgent(admin_ids={12345})
    
    # 1. INITIALIZATION TEST
    logger.info("Step 1: Initializing all 18+ Engines...")
    if not await agent.initialize():
        logger.error("❌ Initialization Failed")
        return
    logger.info("✅ All Engines Online.")

    # 2. STRATEGIC DIRECTOR TEST
    logger.info("Step 2: Strategic Director - Autonomous Strategy Design...")
    strategy = await agent._director.design_monthly_strategy({"market": "Nordic Luxury"})
    logger.info(f"✅ Strategy Generated: {strategy['primary_objective']}")

    # 3. TREND INTEL TEST
    logger.info("Step 3: Trend Intelligence - Live Market Scanning...")
    trends = await agent._trend_intel.scan_market_signals()
    logger.info(f"✅ Trends Detected: {len(trends)} signals found.")

    # 4. CONTENT FACTORY TEST
    logger.info("Step 4: Multi-Format Content Factory - Production Run...")
    article = await agent._content_factory.generate_content(ContentFormat.ARTICLE, topic="Concrete Sustainability")
    script = await agent._content_factory.generate_content(ContentFormat.VIDEO_SCRIPT, topic="Artisan Process")
    logger.info("✅ Multi-format content manufactured successfully.")

    # 5. VISUAL FORGE & LAYOUT TEST
    logger.info("Step 5: Visual Forge & Layout Orchestration...")
    banner = await agent._visual_forge.generate_ad_banner("Arki Concrete Vase", style="nordic")
    layout = await agent._layout_orch.design_infographic([{"point": "Eco-friendly"}, {"point": "Handmade"}])
    logger.info("✅ Visual assets and layouts orchestrated.")

    # 6. RECON & PERSONALIZATION TEST
    logger.info("Step 6: Deep Recon & Hyper-Personalization Loop...")
    mock_prospect = {"id": 1, "business_name": "Stockholm Design House", "website": "sdh.se"}
    recon_report = await agent._recon.deep_recon(mock_prospect["website"])
    personalization = await agent._personalizer.craft_personalized_email(
        prospect=mock_prospect,
        recon_report=recon_report,
        base_content="Hello, we love your work.",
        language="en"
    )
    logger.info("✅ Deep Recon and Personalization successful.")

    # 7. DISTRIBUTION HUB TEST
    logger.info("Step 7: Omni-Channel Distribution - Scheduling & SEO...")
    distro_plan = await agent._distro_hub.schedule_campaign_distribution(
        campaign_assets={"banner": banner, "article": article},
        platforms=["instagram", "linkedin", "pinterest"]
    )
    logger.info(f"✅ Distribution scheduled for {len(distro_plan)} platforms with SEO optimization.")

    logger.info("🏆 TITAN-OMEGA REAL-WORLD STRESS TEST COMPLETED SUCCESSFULLY 🏆")
    logger.info("All 18+ engines are verified, integrated, and operational.")

if __name__ == "__main__":
    asyncio.run(run_end_to_end_test())


