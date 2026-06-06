
"""
campaign_orchestrator_pkg/campaign_status.py — CampaignStatus
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CampaignStatus(Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"




