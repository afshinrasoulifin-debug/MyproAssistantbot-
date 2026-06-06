
from __future__ import annotations
"""
tg_bot/utils/marketing_engine.py — Marketing Engine v3.3
═══════════════════════════════════════════════════════════════
Real marketing automation: campaign management, audience segmentation,
lead scoring, A/B testing, conversion tracking, and analytics.
"""
import logging, random, time
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from arki_project.database.models import Campaign as DBCampaign, Customer as DBLead
from arki_project.database.marketing_models import Prospect
import json # For serializing/deserializing JSON fields in DB models

logger = logging.getLogger(__name__)

class CampaignStatus(Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CampaignType(Enum):
    BROADCAST = "broadcast"        # Send to all/segment
    DRIP = "drip"                  # Sequential messages over time
    TRIGGERED = "triggered"        # Event-based
    AB_TEST = "ab_test"           # A/B variant testing
    REFERRAL = "referral"         # Referral program
    RETENTION = "retention"       # Re-engagement



class MarketingEngine:
    """Full marketing automation engine."""

    SEGMENTS = {
        "whale": {"min_score": 80, "min_spent": 50},
        "active": {"min_score": 50, "min_messages": 100},
        "engaged": {"min_score": 30, "min_messages": 20},
        "trial": {"min_score": 10, "max_messages": 20},
        "dormant": {"max_score": 10, "inactive_days": 14},
        "churned": {"max_score": 5, "inactive_days": 30},
    }

    SEGMENTS_B2B = {
        "high_potential": {"min_score": 70, "min_revenue": 1000000, "min_employees": 50},
        "mid_market": {"min_score": 40, "min_revenue": 100000, "max_revenue": 999999, "min_employees": 10},
        "small_business": {"min_score": 10, "max_revenue": 99999, "max_employees": 9},
        "new_discovery": {"max_score": 10, "age_days": 7},
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._ab_results: Dict[str, Dict[str, Dict]] = {}
        # _conversions and _scheduled_tasks will be managed directly via DB
        self._stats = {
            "campaigns_created": 0, "messages_sent": 0,
            "conversions_total": 0, "revenue_total": 0.0,
        }

    # ── Campaign Management ──

    async def create_campaign(self, name: str, campaign_type: str = "broadcast",
                              target_segment: str = "all",
                              messages: List[Dict] = None) -> DBCampaign:
        ctype = CampaignType(campaign_type) if campaign_type in [e.value for e in CampaignType] else CampaignType.BROADCAST
        db_campaign = DBCampaign(
            name=name, campaign_type=ctype.value,
            target_segment=target_segment,
            messages=json.dumps(messages or []),
        )
        self.session.add(db_campaign)
        await self.session.commit()
        await self.session.refresh(db_campaign)
        self._stats["campaigns_created"] += 1
        logger.info("Campaign created: %s (%s)", name, db_campaign.campaign_id)
        return db_campaign

    async def schedule_campaign(self, campaign_id: str,
                                start_time: Optional[float] = None,
                                end_time: Optional[float] = None) -> bool:
        stmt = select(DBCampaign).where(DBCampaign.campaign_id == campaign_id)
        result = await self.session.execute(stmt)
        db_campaign = result.scalar_one_or_none()
        if not db_campaign:
            return False
        
        schedule_data = {
            "start": start_time or time.time(),
            "end": end_time,
        }
        db_campaign.schedule = json.dumps(schedule_data)
        db_campaign.status = CampaignStatus.SCHEDULED.value
        await self.session.commit()
        return True

    async def start_campaign(self, campaign_id: str) -> Dict[str, Any]:
        stmt = select(DBCampaign).where(DBCampaign.campaign_id == campaign_id)
        result = await self.session.execute(stmt)
        db_campaign = result.scalar_one_or_none()
        if not db_campaign:
            return {"error": "Campaign not found"}

        db_campaign.status = CampaignStatus.ACTIVE.value
        db_campaign.started_at = time.time()

        # Get target audience
        audience = await self.segment_audience(db_campaign.target_segment)

        results = {"campaign_id": campaign_id, "audience_size": len(audience),
                   "messages_queued": 0}

        if db_campaign.campaign_type == CampaignType.AB_TEST.value:
            # Split audience for A/B test
            random.shuffle(audience)
            variants = json.loads(db_campaign.variants).keys() or ["A", "B"]
            split_size = len(audience) // len(variants)
            for i, variant in enumerate(variants):
                start = i * split_size
                end = start + split_size if i < len(variants) - 1 else len(audience)
                segment = audience[start:end]
                self._ab_results.setdefault(campaign_id, {})[variant] = {
                    "audience": len(segment), "sent": 0, "opened": 0,
                    "clicked": 0, "converted": 0,
                }
                results["messages_queued"] += len(segment)
        else:
            messages_list = json.loads(db_campaign.messages)
            results["messages_queued"] = len(audience) * len(messages_list)

        db_campaign.sent = results["messages_queued"]
        self._stats["messages_sent"] += results["messages_queued"]
        await self.session.commit()
        return results

    async def pause_campaign(self, campaign_id: str) -> bool:
        stmt = select(DBCampaign).where(DBCampaign.campaign_id == campaign_id)
        result = await self.session.execute(stmt)
        db_campaign = result.scalar_one_or_none()
        if db_campaign and db_campaign.status == CampaignStatus.ACTIVE.value:
            db_campaign.status = CampaignStatus.PAUSED.value
            await self.session.commit()
            return True
        return False

    async def get_campaign_analytics(self, campaign_id: str) -> Dict[str, Any]:
        stmt = select(DBCampaign).where(DBCampaign.campaign_id == campaign_id)
        result = await self.session.execute(stmt)
        db_campaign = result.scalar_one_or_none()
        if not db_campaign:
            return {"error": "Campaign not found"}
        
        # Calculate rates
        delivery_rate = db_campaign.delivered / max(1, db_campaign.sent)
        open_rate = db_campaign.opened / max(1, db_campaign.delivered)
        click_rate = db_campaign.clicked / max(1, db_campaign.delivered)
        conversion_rate = db_campaign.converted / max(1, db_campaign.delivered)

        return {
            "campaign_id": db_campaign.campaign_id, "name": db_campaign.name,
            "status": db_campaign.status, "type": db_campaign.campaign_type,
            "sent": db_campaign.sent, "delivered": db_campaign.delivered,
            "delivery_rate": f"{delivery_rate:.1%}",
            "open_rate": f"{open_rate:.1%}",
            "click_rate": f"{click_rate:.1%}",
            "conversion_rate": f"{conversion_rate:.1%}",
            "revenue": db_campaign.revenue,
            "ab_results": self._ab_results.get(campaign_id, {}),
        }

    # ── Audience Segmentation ──

    async def segment_audience(self, segment: str = "all") -> List[int]:
        """Get user IDs matching a segment from the database."""
        if segment == "all":
            stmt = select(DBLead.telegram_id)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        
        criteria = self.SEGMENTS.get(segment, {})
        stmt = select(DBLead).where(DBLead.is_deleted == False) # Only consider active leads
        result = await self.session.execute(stmt)
        all_leads = result.scalars().all()
        
        matched = []
        for lead in all_leads:
            if self._matches_segment(lead, criteria):
                matched.append(lead.telegram_id)
        return matched

    async def segment_prospect_audience(self, segment: str = "all") -> List[int]:
        """Get prospect IDs matching a B2B segment from the database."""
        if segment == "all":
            stmt = select(Prospect.id)
            result = await self.session.execute(stmt)
            return result.scalars().all()
        
        criteria = self.SEGMENTS_B2B.get(segment, {})
        stmt = select(Prospect).where(Prospect.is_deleted == False) # Only consider active prospects
        result = await self.session.execute(stmt)
        all_prospects = result.scalars().all()
        
        matched = []
        for prospect in all_prospects:
            if self._matches_b2b_segment(prospect, criteria):
                matched.append(prospect.id)
        return matched

    def _matches_segment(self, lead: DBLead, criteria: Dict) -> bool:
        if "min_score" in criteria and lead.score < criteria["min_score"]:
            return False
        if "max_score" in criteria and lead.score > criteria["max_score"]:
            return False
        if "min_spent" in criteria and lead.total_spent < criteria["min_spent"]:
            return False
        if "min_messages" in criteria and lead.message_count < criteria["min_messages"]:
            return False
        if "max_messages" in criteria and lead.message_count > criteria["max_messages"]:
            return False
        if "inactive_days" in criteria:
            if lead.last_active is None: # If never active, consider inactive
                return True
            days_inactive = (time.time() - lead.last_active.timestamp()) / 86400
            if days_inactive < criteria["inactive_days"]:
                return False
        return True

    def _matches_b2b_segment(self, prospect: Prospect, criteria: Dict) -> bool:
        if "min_score" in criteria and prospect.score < criteria["min_score"]:
            return False
        if "max_score" in criteria and prospect.score > criteria["max_score"]:
            return False
        if "min_revenue" in criteria and (prospect.revenue is None or prospect.revenue < criteria["min_revenue"]):
            return False
        if "max_revenue" in criteria and (prospect.revenue is None or prospect.revenue > criteria["max_revenue"]):
            return False
        if "min_employees" in criteria and (prospect.employee_count is None or prospect.employee_count < criteria["min_employees"]):
            return False
        if "max_employees" in criteria and (prospect.employee_count is None or prospect.employee_count > criteria["max_employees"]):
            return False
        if "age_days" in criteria:
            if prospect.discovered_at is None:
                return False
            days_since_discovery = (datetime.now() - prospect.discovered_at).days
            if days_since_discovery > criteria["age_days"]:
                return False
        return True

    async def auto_segment_user(self, user_id: int) -> str:
        """Automatically assign segment based on profile from the database."""
        stmt = select(DBLead).where(DBLead.telegram_id == user_id)
        result = await self.session.execute(stmt)
        lead = result.scalar_one_or_none()
        if not lead:
            return "unknown"
        for seg_name in ["whale", "active", "engaged", "trial", "dormant", "churned"]:
            criteria = self.SEGMENTS[seg_name]
            if self._matches_segment(lead, criteria):
                lead.segment = seg_name
                await self.session.commit()
                return seg_name
        return "unknown"

    # ── Lead Scoring ──

    async def score_lead(self, user_id: int) -> float:
        """Calculate lead score based on behavior signals from the database."""
        stmt = select(DBLead).where(DBLead.telegram_id == user_id)
        result = await self.session.execute(stmt)
        lead = result.scalar_one_or_none()
        if not lead:
            return 0.0

        score = 0.0

        # Engagement scoring (max 30)
        msg_score = min(15, lead.message_count * 0.1)
        cmd_score = min(10, lead.command_count * 0.3)
        ai_score = min(5, lead.ai_requests * 0.2)
        score += msg_score + cmd_score + ai_score

        # Monetary scoring (max 30)
        spend_score = min(20, lead.total_spent * 2)
        referral_score = min(10, lead.referrals * 5)
        score += spend_score + referral_score

        # Recency scoring (max 20)
        if lead.last_active:
            days_since_active = (datetime.now() - lead.last_active).total_seconds() / 86400
            if days_since_active < 1:
                score += 20
            elif days_since_active < 3:
                score += 15
            elif days_since_active < 7:
                score += 10
            elif days_since_active < 14:
                score += 5

        # Consistency scoring (max 20)
        if lead.created_at:
            days_as_user = max(1, (datetime.now() - lead.created_at).total_seconds() / 86400)
            daily_avg = lead.message_count / days_as_user
            if daily_avg >= 5:
                score += 20
            elif daily_avg >= 2:
                score += 15
            elif daily_avg >= 0.5:
                score += 10
            elif daily_avg >= 0.1:
                score += 5

        lead.score = min(100, round(score, 1))
        await self.session.commit()
        return lead.score

    async def score_prospect(self, prospect_id: int) -> float:
        """Calculate B2B prospect score based on available data."""
        stmt = select(Prospect).where(Prospect.id == prospect_id)
        result = await self.session.execute(stmt)
        prospect = result.scalar_one_or_none()
        if not prospect:
            return 0.0

        score = 0.0

        # Base score for being discovered
        score += 10

        # Website presence (important for B2B)
        if prospect.website and prospect.website != "Unknown Website":
            score += 10

        # Industry relevance (placeholder, would need a mapping)
        if prospect.business_type == "B2B SaaS": # Example
            score += 15

        # Revenue/Employee count (if available)
        if prospect.revenue:
            if prospect.revenue >= 1000000: score += 20
            elif prospect.revenue >= 100000: score += 10
            else: score += 5
        
        if prospect.employee_count:
            if prospect.employee_count >= 50: score += 15
            elif prospect.employee_count >= 10: score += 7
            else: score += 3

        # Recency of discovery
        if prospect.discovered_at:
            days_since_discovery = (datetime.now() - prospect.discovered_at).days
            if days_since_discovery < 7: score += 10
            elif days_since_discovery < 30: score += 5

        # Status (e.g., qualified, contacted)
        if prospect.status == "qualified": score += 10
        if prospect.status == "contacted": score += 5

        prospect.score = min(100, round(score, 1))
        await self.session.commit()
        return prospect.score

    async def update_lead_activity(self, user_id: int, activity_type: str = "message",
                                   amount: float = 0.0) -> DBLead:
        """Track user activity for scoring and segmentation in the database."""
        stmt = select(DBLead).where(DBLead.telegram_id == user_id)
        result = await self.session.execute(stmt)
        lead = result.scalar_one_or_none()
        
        if not lead:
            # Provide default values for required fields
            lead = DBLead(
                telegram_id=user_id,
                owner_id=0, # Assuming 0 or some system ID for auto-generated leads
                name=f"Lead_{user_id}",
                created_at=datetime.now()
            )
            self.session.add(lead)
            await self.session.flush() # To get the lead.id if needed later

        lead.last_active = datetime.now()
        if activity_type == "message":
            lead.message_count += 1
        elif activity_type == "command":
            lead.command_count += 1
        elif activity_type == "ai_request":
            lead.ai_requests += 1
        elif activity_type == "payment":
            lead.total_spent += amount
        elif activity_type == "referral":
            lead.referrals += 1

        # Update engagement history (JSON field)
        history = json.loads(lead.engagement_history) if lead.engagement_history else []
        history.append({
            "type": activity_type, "time": time.time(), "amount": amount,
        })
        # Keep last 100
        if len(history) > 100:
            history = history[-100:]
        lead.engagement_history = json.dumps(history)

        # Re-score and re-segment
        await self.score_lead(user_id)
        await self.auto_segment_user(user_id)
        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    # ── Conversion Tracking ──

    async def track_conversion(self, user_id: int, campaign_id: str = "",
                               conversion_type: str = "signup",
                               value: float = 0.0) -> Dict:
        # For now, conversions are tracked in _stats, but could be a separate DB table
        self._stats["conversions_total"] += 1
        self._stats["revenue_total"] += value

        # Update campaign metrics in DB
        if campaign_id:
            stmt = select(DBCampaign).where(DBCampaign.campaign_id == campaign_id)
            result = await self.session.execute(stmt)
            db_campaign = result.scalar_one_or_none()
            if db_campaign:
                db_campaign.converted += 1
                db_campaign.revenue += value
                await self.session.commit()

        # Update lead in DB
        stmt = select(DBLead).where(DBLead.telegram_id == user_id)
        result = await self.session.execute(stmt)
        db_lead = result.scalar_one_or_none()
        if db_lead:
            db_lead.campaign_interactions += 1
            await self.session.commit()

        return {"user_id": user_id, "campaign_id": campaign_id, "type": conversion_type, "value": value, "timestamp": time.time()}

    # ── Analytics ──

    async def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        cutoff_datetime = datetime.now() - timedelta(days=days)

        # Segment distribution from DBLeads
        stmt_leads = select(DBLead)
        result_leads = await self.session.execute(stmt_leads)
        all_leads = result_leads.scalars().all()
        segments = defaultdict(int)
        for lead in all_leads:
            segments[lead.segment] += 1

        # Top campaigns from DBCampaigns
        stmt_campaigns = select(DBCampaign).order_by(DBCampaign.revenue.desc()).limit(10)
        result_campaigns = await self.session.execute(stmt_campaigns)
        top_campaigns_db = result_campaigns.scalars().all()
        active_campaigns = []
        for c in top_campaigns_db:
            delivery_rate = c.delivered / max(1, c.sent)
            conversion_rate = c.converted / max(1, c.delivered)
            active_campaigns.append({
                "id": c.campaign_id, "name": c.name,
                "conversion_rate": f"{conversion_rate:.1%}",
                "revenue": c.revenue,
            })

        total_leads_count = len(all_leads)
        avg_lead_score = round(sum(l.score for l in all_leads) / max(1, total_leads_count), 1) if total_leads_count > 0 else 0.0

        # Conversions are still in _stats for now, as no dedicated DB table for them yet
        return {
            "period_days": days,
            "total_leads": total_leads_count,
            "segments": dict(segments),
            "conversions": self._stats["conversions_total"],
            "revenue": self._stats["revenue_total"],
            "avg_lead_score": avg_lead_score,
            "top_campaigns": active_campaigns,
            "campaigns_created": self._stats["campaigns_created"],
            "messages_sent": self._stats["messages_sent"],
        }

    async def get_funnel(self) -> Dict[str, int]:
        """Get conversion funnel metrics from the database."""
        stmt = select(DBLead)
        result = await self.session.execute(stmt)
        all_leads = result.scalars().all()
        total = len(all_leads)
        
        engaged_count = len(await self.segment_audience("engaged")) + len(await self.segment_audience("active"))
        active_count = len(await self.segment_audience("active"))
        paying_count = len(await self.segment_audience("whale"))
        churned_count = len(await self.segment_audience("churned"))

        return {
            "total_users": total,
            "engaged": engaged_count,
            "active": active_count,
            "paying": paying_count,
            "churned": churned_count,
        }


# Singleton
_engine: Optional[MarketingEngine] = None
async def get_marketing_engine(session: AsyncSession) -> MarketingEngine:
    return MarketingEngine(session=session)


