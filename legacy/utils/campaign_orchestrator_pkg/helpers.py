
"""
campaign_orchestrator_pkg/helpers.py — standalone functions
Arki Engine v29.0.0
"""
from ._base import *  # noqa

def _b2b_outreach_steps() -> List[CampaignStep]:
    """Standard B2B outreach: Discover → Enrich → Score → Email → Follow-up."""
    return [
        CampaignStep(1, StepType.DISCOVER, config={"max_prospects": 50}),
        CampaignStep(2, StepType.ENRICH, config={"deep_recon": True, "contact_intel": True}),
        CampaignStep(3, StepType.SCORE, config={"min_score": 40}),
        CampaignStep(4, StepType.FILTER, condition="score >= 40"),
        CampaignStep(5, StepType.EMAIL, channel=ChannelType.EMAIL,
                     config={"template": "introduction", "personalize": True}),
        CampaignStep(6, StepType.WAIT, delay_hours=72),
        CampaignStep(7, StepType.FILTER, condition="stage != responded"),
        CampaignStep(8, StepType.FOLLOW_UP, channel=ChannelType.EMAIL,
                     config={"template": "follow_up_1", "personalize": True}),
        CampaignStep(9, StepType.WAIT, delay_hours=120),
        CampaignStep(10, StepType.ANALYZE, config={"metrics": ["open_rate", "reply_rate"]}),
    ]



def _b2c_social_steps() -> List[CampaignStep]:
    """B2C social: Content → Publish → Hashtag → Engage → Analyze."""
    return [
        CampaignStep(1, StepType.CONTENT, config={"types": ["product_photo", "story", "reel"]}),
        CampaignStep(2, StepType.SOCIAL_POST, channel=ChannelType.INSTAGRAM,
                     config={"hashtags": True, "schedule": True}),
        CampaignStep(3, StepType.SOCIAL_POST, channel=ChannelType.PINTEREST,
                     config={"pin_boards": True}),
        CampaignStep(4, StepType.SOCIAL_POST, channel=ChannelType.FACEBOOK,
                     config={"boost": False}),
        CampaignStep(5, StepType.WAIT, delay_hours=48),
        CampaignStep(6, StepType.ANALYZE, config={"metrics": ["engagement", "reach", "saves"]}),
    ]



def _competitor_intel_steps() -> List[CampaignStep]:
    """Competitor intel: Scan → Monitor → SWOT → Counter-strategy."""
    return [
        CampaignStep(1, StepType.COMPETITOR_SCAN, config={"depth": "deep"}),
        CampaignStep(2, StepType.ANALYZE, config={"type": "swot"}),
        CampaignStep(3, StepType.CONTENT, config={"type": "counter_strategy",
                                                    "based_on": "competitor_gaps"}),
        CampaignStep(4, StepType.ANALYZE, config={"metrics": ["market_position", "pricing"]}),
    ]



def _full_funnel_steps() -> List[CampaignStep]:
    """Full funnel: combines B2B + B2C + Competitor."""
    return [
        CampaignStep(1, StepType.COMPETITOR_SCAN, config={"depth": "deep"}),
        CampaignStep(2, StepType.DISCOVER, config={"max_prospects": 100}),
        CampaignStep(3, StepType.ENRICH, config={"deep_recon": True, "contact_intel": True}),
        CampaignStep(4, StepType.SCORE, config={"min_score": 30}),
        CampaignStep(5, StepType.CONTENT, config={"calendar_weeks": 4}),
        CampaignStep(6, StepType.FILTER, condition="score >= 50"),
        CampaignStep(7, StepType.EMAIL, channel=ChannelType.EMAIL,
                     config={"template": "personalized_intro"}),
        CampaignStep(8, StepType.SOCIAL_POST, channel=ChannelType.INSTAGRAM),
        CampaignStep(9, StepType.SOCIAL_POST, channel=ChannelType.PINTEREST),
        CampaignStep(10, StepType.WAIT, delay_hours=72),
        CampaignStep(11, StepType.FOLLOW_UP, channel=ChannelType.EMAIL),
        CampaignStep(12, StepType.ANALYZE, config={"comprehensive": True}),
    ]




