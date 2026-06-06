
"""
campaign_orchestrator_pkg/campaign.py — Campaign
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class Campaign:
    """A marketing campaign."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    campaign_type: CampaignType = CampaignType.B2B_OUTREACH
    status: CampaignStatus = CampaignStatus.DRAFT
    steps: List[CampaignStep] = field(default_factory=list)
    leads: List[Lead] = field(default_factory=list)
    target_regions: List[str] = field(default_factory=list)
    target_industries: List[str] = field(default_factory=list)
    channels: List[ChannelType] = field(default_factory=list)
    budget: float = 0.0
    budget_spent: float = 0.0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    gdpr_compliant: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "type": self.campaign_type.value,
            "status": self.status_code.value,
            "steps_count": len(self.steps),
            "steps_completed": sum(1 for s in self.steps if s.completed),
            "leads_count": len(self.leads),
            "target_regions": self.target_regions,
            "channels": [c.value for c in self.channels],
            "budget": self.budget, "budget_spent": self.budget_spent,
            "metrics": self.metrics,
            "gdpr_compliant": self.gdpr_compliant,
        }




