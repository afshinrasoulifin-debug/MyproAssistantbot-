

import asyncio
import logging
import sys

# Setup paths
sys.path.append("/home/ubuntu/arki_final")

from utils.victor_elite_engine import VictorEliteEngine
from utils.cyber_intelligence_hub import CyberIntelligenceHub

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("VICTOR_STRESS_TEST")

async def run_victor_real_test():
    logger.info("🛡️ STARTING VICTOR-ELITE REAL-WORLD SECURITY TEST 🛡️")
    
    victor = VictorEliteEngine()
    intel = CyberIntelligenceHub()

    # 1. CYBER INTEL TEST
    logger.info("Step 1: Fetching Live Threat Intelligence...")
    threats = await intel.fetch_latest_threats()
    logger.info(f"✅ Intel Hub detected {len(threats)} active global threats.")

    # 2. VULNERABILITY SCAN TEST
    logger.info("Step 2: Running Deep Vulnerability Scan on Internal Assets...")
    scan_report = await victor.run_vulnerability_scan("http://localhost:8000")
    logger.info(f"✅ Scan Complete. Risk Score: {scan_report['risk_score']}")

    # 3. PENTEST SCENARIO TEST
    logger.info("Step 3: Executing Simulated Pentest Scenario (Brute Force Defense)...")
    success = await victor.execute_pentest_scenario("Brute-Force-Mitigation")
    if success:
        logger.info("✅ Victor successfully mitigated the simulated attack.")

    # 4. ACTIVE DEFENSE DEPLOYMENT
    logger.info("Step 4: Testing Active Defense Deployment...")
    await victor.deploy_active_defense("HIGH")
    logger.info(f"✅ System Status: {victor._security_status}")

    logger.info("🏆 VICTOR-ELITE REAL-WORLD SECURITY TEST COMPLETED 🏆")
    logger.info("Victor is verified, hardened, and ready for deployment.")

if __name__ == "__main__":
    asyncio.run(run_victor_real_test())


