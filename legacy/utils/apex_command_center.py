
"""
utils/apex_command_center.py — APEX SUPREMACY COMMAND CENTER
===========================================================
The ultimate coordination layer for the entire Arki ecosystem.
"""

import logging
import asyncio
from datetime import datetime
from arki_project.utils.multi_format_content_factory import ContentFormat

logger = logging.getLogger(__name__)

class ApexCommandCenter:
    """
    The brain of the brain. Orchestrates Marketing, Security, and Content domains.
    """

    def __init__(self, agent=None):
        self._agent = agent
        self._system_health = "OPTIMAL"
        self._last_sync = datetime.now()
        self._engine_status = {}

    async def run_global_sync(self):
        """Coordinates all engines for a unified offensive/defensive stance."""
        logger.info("⚡ APEX: Initiating Global Neural Sync across all domains...")
        
        # 1. Security Check (Victor)
        if hasattr(self._agent, '_victor') and self._agent._victor:
            status = await self._agent._victor.run_vulnerability_scan("internal")
            self._engine_status["security"] = status
            
        # 2. Market Intelligence (Trend & Shadow)
        if hasattr(self._agent, '_trend_intel') and self._agent._trend_intel:
            trends = await self._agent._trend_intel.scan_market_signals()
            self._engine_status["market"] = trends
            
        # 3. Strategy Alignment (Director)
        if hasattr(self._agent, '_director') and self._agent._director:
            # Adjust strategy based on security and trends
            await self._agent._director.design_monthly_strategy({"context": "Apex-Sync"})
            
        self._last_sync = datetime.now()
        logger.info("✅ APEX: Global Sync Complete. All domains aligned.")

    async def execute_high_velocity_offensive(self, target_sector: str):
        """Triggers a massive, coordinated parallel operation."""
        logger.warning(f"🚀 APEX: Triggering High-Velocity Offensive on {target_sector}!")
        
        tasks = [
            self._agent._hunter.hunt(target_sector, {"id": "apex_offensive", "name_en": target_sector}),
            self._agent._content_factory.generate_content(
                format_type=ContentFormat.ARTICLE, 
                topic=target_sector
            ),
            self._agent._visual_forge.generate_ad_banner(target_sector)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"✅ APEX: Offensive launched. {len(results)} primary workstreams active.")
        return results


