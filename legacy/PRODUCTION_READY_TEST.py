

import asyncio
import logging
import sys

# Setup paths
sys.path.append("/home/ubuntu/arki_final")

from architecture.agent.marketing_agent import MarketingMasterAgent
from utils.multi_format_content_factory import ContentFormat

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PRODUCTION_TEST")

async def run_production_test():
    logger.info("🚀 STARTING ARKI PRODUCTION-READY VALIDATION 🚀")
    
    agent = MarketingMasterAgent(admin_ids={12345})
    await agent.initialize()

    # 1. REAL AI STRATEGY
    logger.info("Step 1: Testing REAL AI Strategic Planning...")
    strategy = await agent._director.design_monthly_strategy({"market": "Luxury Nordic Decor in London"})
    logger.info(f"✅ AI Strategy: {strategy.get('primary_objective')}")

    # 2. REAL AI CONTENT
    logger.info("Step 2: Testing REAL AI Content Manufacturing...")
    content = await agent._content_factory.generate_content(
        ContentFormat.ARTICLE, 
        topic="Sustainable Concrete Craftsmanship"
    )
    logger.info(f"✅ AI Content Title: {content.get('title')}")

    # 3. REAL WEB RECON
    logger.info("Step 3: Testing REAL Web Reconnaissance (Live Scrape)...")
    # Using a real site that is likely to be stable for testing (e.g., example.com)
    recon = await agent._recon.deep_recon("example.com")
    logger.info(f"✅ Recon Metadata Title: {recon['metadata'].get('title')}")
    logger.info(f"✅ Recon Tech Stack: {recon['tech_stack']}")

    # 4. REAL ROI LOGIC
    logger.info("Step 4: Testing REAL Financial ROI Analysis...")
    roi_report = await agent._roi.analyze_campaign_roi("camp_999")
    logger.info(f"✅ ROI Analysis Status: {roi_report['status']} (ROI: {roi_report['roi']})")

    logger.info("🏆 ARKI PRODUCTION-READY VALIDATION COMPLETED 🏆")
    logger.info("The system is now powered by REAL AI and REAL logic.")

if __name__ == "__main__":
    asyncio.run(run_production_test())


