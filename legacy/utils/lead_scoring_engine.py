
from __future__ import annotations
"""
tg_bot/utils/lead_scoring_engine.py — Behavioral Lead Scoring v1.0
═══════════════════════════════════════════════════════════════════
Automatic lead scoring based on user behavior in the bot.

Scoring Events:
  • Message sent        +1
  • Product viewed      +3
  • Used /sales cmd     +5
  • Asked about price   +8
  • Used /crm           +2
  • Shared product      +10
  • Placed order        +20
  • Returned            +5 (came back after 7+ days)
  • Inactive 30d        -10

Tiers:
  • Cold    (0-20)
  • Warm    (21-50)
  • Hot     (51-80)
  • Ready   (81+)
"""


import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LeadTier(str, Enum):
    COLD = "cold"
    WARM = "warm"
    HOT = "hot"
    READY = "ready"


# Score weights for different actions
SCORE_WEIGHTS: Dict[str, int] = {
    "message": 1,
    "product_view": 3,
    "sales_command": 5,
    "price_inquiry": 8,
    "crm_action": 2,
    "share_product": 10,
    "order_placed": 20,
    "returned_user": 5,
    "content_created": 3,
    "platform_connected": 7,
    "email_opened": 4,
    "link_clicked": 6,
    "inactive_30d": -10,
}


@dataclass
class LeadProfile:
    user_id: int
    name: str = ""
    score: float = 0.0
    tier: LeadTier = LeadTier.COLD
    events: List[Dict[str, Any]] = field(default_factory=list)
    last_active: float = 0.0
    first_seen: float = 0.0
    total_orders: int = 0
    total_spent: float = 0.0
    tags: List[str] = field(default_factory=list)

    @property
    def days_since_last_active(self) -> float:
        if self.last_active == 0:
            return 999
        return (time.time() - self.last_active) / 86400

    @property
    def days_since_first_seen(self) -> float:
        if self.first_seen == 0:
            return 0
        return (time.time() - self.first_seen) / 86400


class LeadScoringEngine:
    """
    Tracks user behavior and assigns lead scores.
    
    Usage:
        engine = LeadScoringEngine()
        
        # Record events
        engine.record_event(user_id, "message")
        engine.record_event(user_id, "price_inquiry")
        engine.record_event(user_id, "order_placed", amount=45.0)
        
        # Get score
        profile = engine.get_profile(user_id)
        logger.debug("Score: %s, Tier: %s", profile.score, profile.tier)
        
        # Get hot leads
        hot = engine.get_leads_by_tier(LeadTier.HOT)
    """

    def __init__(self) -> None:
        self._profiles: Dict[int, LeadProfile] = {}

    def record_event(
        self, user_id: int, event_type: str,
        name: str = "", amount: float = 0.0,
        metadata: Optional[Dict] = None,
    ) -> LeadProfile:
        """Record a user event and update score."""
        profile = self._get_or_create(user_id, name)
        now = time.time()

        # Record event
        event = {
            "type": event_type,
            "timestamp": now,
            "amount": amount,
            **(metadata or {}),
        }
        profile.events.append(event)

        # Keep last 200 events
        if len(profile.events) > 200:
            profile.events = profile.events[-200:]

        # Check for returned user bonus
        if profile.last_active > 0 and (now - profile.last_active) > 7 * 86400:
            profile.score += SCORE_WEIGHTS.get("returned_user", 5)

        profile.last_active = now

        # Add score
        weight = SCORE_WEIGHTS.get(event_type, 1)
        profile.score += weight

        # Track orders
        if event_type == "order_placed":
            profile.total_orders += 1
            profile.total_spent += amount

        # Recalculate tier
        profile.tier = self._calculate_tier(profile.score)

        return profile

    def decay_inactive(self, days_threshold: int = 30) -> Any:
        """Apply decay to inactive users."""
        now = time.time()
        for profile in self._profiles.values():
            if profile.last_active > 0:
                days = (now - profile.last_active) / 86400
                if days > days_threshold:
                    profile.score += SCORE_WEIGHTS.get("inactive_30d", -10)
                    profile.score = max(0, profile.score)
                    profile.tier = self._calculate_tier(profile.score)

    def get_profile(self, user_id: int) -> Optional[LeadProfile]:
        return self._profiles.get(user_id)

    def get_leads_by_tier(self, tier: LeadTier) -> List[LeadProfile]:
        """Get all leads of a specific tier, sorted by score desc."""
        return sorted(
            [p for p in self._profiles.values() if p.tier == tier],
            key=lambda p: p.score, reverse=True,
        )

    def get_top_leads(self, limit: int = 10) -> List[LeadProfile]:
        """Get top leads by score."""
        return sorted(
            self._profiles.values(),
            key=lambda p: p.score, reverse=True,
        )[:limit]

    def get_leads_needing_attention(self) -> List[LeadProfile]:
        """
        Get leads that need follow-up:
        - Hot leads not contacted in 3+ days
        - Warm leads going cold (inactive 7+ days)
        - Ready leads (should close sale)
        """
        attention = []
        for p in self._profiles.values():
            if p.tier == LeadTier.READY:
                attention.append(p)
            elif p.tier == LeadTier.HOT and p.days_since_last_active > 3:
                attention.append(p)
            elif p.tier == LeadTier.WARM and p.days_since_last_active > 7:
                attention.append(p)
        return sorted(attention, key=lambda p: p.score, reverse=True)

    def get_summary(self) -> Dict[str, Any]:
        """Get overall lead scoring summary."""
        tiers = defaultdict(int)
        total_value = 0.0
        for p in self._profiles.values():
            tiers[p.tier.value] += 1
            total_value += p.total_spent

        return {
            "total_leads": len(self._profiles),
            "tiers": dict(tiers),
            "total_revenue": total_value,
            "avg_score": (
                sum(p.score for p in self._profiles.values()) / max(1, len(self._profiles))
            ),
            "needs_attention": len(self.get_leads_needing_attention()),
        }

    def _get_or_create(self, user_id: int, name: str = "") -> LeadProfile:
        if user_id not in self._profiles:
            self._profiles[user_id] = LeadProfile(
                user_id=user_id, name=name,
                first_seen=time.time(),
            )
        elif name and not self._profiles[user_id].name:
            self._profiles[user_id].name = name
        return self._profiles[user_id]

    @staticmethod
    def _calculate_tier(score: float) -> LeadTier:
        if score >= 81:
            return LeadTier.READY
        if score >= 51:
            return LeadTier.HOT
        if score >= 21:
            return LeadTier.WARM
        return LeadTier.COLD


# ═══════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════

_engine: Optional[LeadScoringEngine] = None

def get_lead_scoring_engine() -> LeadScoringEngine:
    global _engine
    if _engine is None:
        _engine = LeadScoringEngine()
    return _engine


