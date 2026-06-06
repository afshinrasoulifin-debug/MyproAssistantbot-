
"""
campaign_orchestrator_pkg/lead_stage.py — LeadStage
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class LeadStage(Enum):
    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    SCORED = "scored"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    QUALIFIED = "qualified"
    NEGOTIATING = "negotiating"
    CONVERTED = "converted"
    LOST = "lost"




