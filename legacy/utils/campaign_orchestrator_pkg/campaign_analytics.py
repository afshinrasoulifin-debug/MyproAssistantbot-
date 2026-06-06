
"""
campaign_orchestrator_pkg/campaign_analytics.py — CampaignAnalytics
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class CampaignAnalytics:
    """Analytics for a campaign."""
    campaign_id: str = ""
    total_leads: int = 0
    leads_by_stage: Dict[str, int] = field(default_factory=dict)
    conversion_rate: float = 0.0
    avg_score: float = 0.0
    emails_sent: int = 0
    emails_opened: int = 0
    emails_replied: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0
    social_posts: int = 0
    social_engagement: float = 0.0
    content_pieces: int = 0
    competitor_alerts: int = 0
    roi_estimate: float = 0.0
    top_performing_channel: str = ""
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "total_leads": self.total_leads,
            "leads_by_stage": self.leads_by_stage,
            "conversion_rate": round(self.conversion_rate, 2),
            "avg_score": round(self.avg_score, 1),
            "emails_sent": self.emails_sent,
            "open_rate": round(self.open_rate, 2),
            "reply_rate": round(self.reply_rate, 2),
            "social_posts": self.social_posts,
            "content_pieces": self.content_pieces,
            "roi_estimate": round(self.roi_estimate, 2),
            "recommendations": self.recommendations,
        }


# ═══════════════════════════════════════════════════════════════════
# Campaign Templates — Pre-built sequences
# ═══════════════════════════════════════════════════════════════════



