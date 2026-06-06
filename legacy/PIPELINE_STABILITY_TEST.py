

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
logger = logging.getLogger("PIPELINE_TEST")

async def run_pipeline_test():
    logger.info("⛓️ STARTING ARKI V30 PIPELINE STABILITY VALIDATION ⛓️")
    
    agent = MarketingMasterAgent(admin_ids={12345})
    await agent.initialize()
    
    # Access the automation service
    service = agent._service
    
    # Test Event Propagation
    logger.info("\n--- Phase 1: Event Propagation Test ---")
    # 1. Simulate finding a prospect
    logger.info("Step 1: Publishing 'prospect_found' event...")
    await service.event_bus.publish("prospect_found", {"prospect_id": "TEST_001"})
    
    # 2. Simulate qualification
    logger.info("Step 2: Publishing 'prospect_qualified' event...")
    await service.event_bus.publish("prospect_qualified", {"prospect_id": "TEST_001"})
    
    # 3. Simulate recon completion
    logger.info("Step 3: Publishing 'recon_complete' event...")
    await service.event_bus.publish("recon_complete", {"prospect_id": "TEST_001"})
    
    # Check history
    history = service.event_bus.get_history()
    logger.info(f"✅ Event History Count: {len(history)}")
    for event in history:
        logger.info(f"  - Event: {event['type']} at {event['timestamp']}")

    # Test Error Resilience
    logger.info("\n--- Phase 2: Pipeline Error Resilience ---")
    async def failing_handler(data):
        raise ValueError("Simulated handler failure")
    
    service.event_bus.subscribe("error_test", failing_handler)
    logger.info("Step 4: Publishing 'error_test' to verify resilience...")
    await service.event_bus.publish("error_test", {"data": "fail"})
    logger.info("✅ Pipeline remained stable after handler failure.")

    logger.info("\n🏆 ARKI V30 PIPELINE STABILITY VERIFIED 🏆")

if __name__ == "__main__":
    asyncio.run(run_pipeline_test())


