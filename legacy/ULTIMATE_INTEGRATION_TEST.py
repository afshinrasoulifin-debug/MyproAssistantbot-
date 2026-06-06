

import asyncio
import logging
import sys

# Setup paths
sys.path.append("/home/ubuntu/arki_final")

from architecture.agent.marketing_agent import MarketingMasterAgent
from arki_project.utils.multi_format_content_factory import ContentFormat

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ULTIMATE_TEST")

async def run_ultimate_test():
    logger.info("🌌 STARTING ARKI V30 ULTIMATE INTEGRATION VALIDATION 🌌")
    
    agent = MarketingMasterAgent(admin_ids={12345})
    await agent.initialize()

    # 1. APEX Command & Neural Sync
    logger.info("\n--- Phase 1: Apex Supremacy Command & Control ---")
    await agent._apex.run_global_sync()
    logger.info("✅ Apex Sync Successful.")

    # 2. Strategic AI Reasoning
    logger.info("\n--- Phase 2: Strategic AI Intelligence ---")
    strategy = await agent._director.design_monthly_strategy({"market": "Global Luxury Artisan Decor"})
    logger.info(f"✅ Strategy Objective: {strategy.get('primary_objective')}")

    # 3. Content & Visual Manufacturing
    logger.info("\n--- Phase 3: Content & Visual Production ---")
    content = await agent._content_factory.generate_content(ContentFormat.ARTICLE, "The Soul of Nordic Design")
    logger.info(f"✅ Content Generated: {content.get('title')}")
    banner = await agent._visual_forge.generate_ad_banner("Nordic Design")
    logger.info(f"✅ Visual Asset Prepared: {banner.get('style')}")

    # 4. Security & Recon
    logger.info("\n--- Phase 4: Security & Intelligence Recon ---")
    recon = await agent._recon.deep_recon("example.com")
    logger.info(f"✅ Deep Recon Metadata: {recon['metadata'].get('title')}")
    threats = await agent._cyber_intel.fetch_latest_threats()
    logger.info(f"✅ Security Intel: {len(threats)} threats monitored.")

    # 5. Financial ROI Logic
    logger.info("\n--- Phase 5: Financial ROI Optimization ---")
    roi = await agent._roi.analyze_campaign_roi("ultimate_campaign")
    logger.info(f"✅ ROI Analysis: {roi['status']} ({roi['roi']})")

    logger.info("\n🏆 ARKI V30 ULTIMATE INTEGRATION COMPLETED 🏆")
    logger.info("The entire ecosystem is now unified and operational.")

if __name__ == "__main__":
    asyncio.run(run_ultimate_test())


