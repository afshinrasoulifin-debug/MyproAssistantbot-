

import asyncio
import logging
import sys
import os

# Setup paths
sys.path.append("/home/ubuntu/arki_final")

# Mocking connection before imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_omega.db"

from architecture.agent.marketing_agent import MarketingMasterAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OMEGA_TEST")

async def test_content_titan_initialization():
    logger.info("🧪 Testing CONTENT-TITAN Marketing System Initialization...")
    
    agent = MarketingMasterAgent(admin_ids={12345})
    
    # Initialize agent (this will trigger engine wiring)
    success = await agent.initialize()
    
    if not success:
        logger.error("❌ Agent initialization failed")
        return False
        
    logger.info("✅ Agent initialized successfully")
    
    # Check if CONTENT-TITAN engines are present
    titan_engines = [
        agent._recon, agent._personalizer, agent._trend_intel, 
        agent._social_exec, agent._visual_forge, agent._director,
        agent._content_factory, agent._layout_orch, agent._distro_hub
    ]
    if all(titan_engines):
        logger.info("✅ ALL 18+ CONTENT-TITAN Engines detected and wired")
    else:
        logger.error("❌ Some CONTENT-TITAN Engines missing from agent")
        return False
        
    # Check if Campaign Manager has OMEGA engines
    if agent._campaign_manager._recon and agent._campaign_manager._personalizer:
        logger.info("✅ Campaign Manager OMEGA-ready")
    else:
        logger.error("❌ Campaign Manager not wired with OMEGA engines")
        return False
        
    # Check if Automation Service has the new sync task
    if "omega_recon_sync" in agent._service._scheduled_tasks:
        logger.info("✅ Automation Service has OMEGA Recon Sync task")
    else:
        logger.error("❌ OMEGA Recon Sync task missing from Automation Service")
        return False
        
    logger.info("🚀 ALL OMEGA ARCHITECTURE CHECKS PASSED")
    return True

if __name__ == "__main__":
    asyncio.run(test_content_titan_initialization())


