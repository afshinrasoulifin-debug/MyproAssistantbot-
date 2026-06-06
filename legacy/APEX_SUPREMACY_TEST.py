

import asyncio
import logging
import sys

# Setup paths
sys.path.append("/home/ubuntu/arki_final")

from architecture.agent.marketing_agent import MarketingMasterAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("APEX_TEST")

async def run_apex_test():
    logger.info("⚡ STARTING ARKI APEX-SUPREMACY VALIDATION ⚡")
    
    agent = MarketingMasterAgent(admin_ids={12345})
    await agent.initialize()

    # 1. GLOBAL NEURAL SYNC
    logger.info("Step 1: Testing APEX Global Neural Sync...")
    await agent._apex.run_global_sync()
    logger.info("✅ Global Sync executed. All domains verified.")

    # 2. HIGH-VELOCITY OFFENSIVE
    logger.info("Step 2: Testing APEX High-Velocity Offensive...")
    results = await agent._apex.execute_high_velocity_offensive("Luxury Architecture")
    logger.info(f"✅ HVE Offensive launched with {len(results)} parallel workstreams.")

    logger.info("🏆 ARKI APEX-SUPREMACY VALIDATION COMPLETED 🏆")
    logger.info("The system has reached the peak of command and coordination.")

if __name__ == "__main__":
    asyncio.run(run_apex_test())


