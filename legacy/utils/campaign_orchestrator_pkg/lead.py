
"""
campaign_orchestrator_pkg/lead.py — Lead
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class Lead:
    """A lead in the campaign pipeline."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    company_name: str = ""
    domain: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_role: str = ""
    stage: LeadStage = LeadStage.DISCOVERED
    score: float = 0.0
    source: str = ""
    region: str = ""
    industry: str = ""
    enrichment_data: Dict[str, Any] = field(default_factory=dict)
    interactions: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "company_name": self.company_name,
            "domain": self.domain, "contact_name": self.contact_name,
            "contact_email": self.contact_email, "stage": self.stage.value,
            "score": self.score, "source": self.source,
            "region": self.region, "industry": self.industry,
            "interactions_count": len(self.interactions),
            "tags": self.tags,
        }




