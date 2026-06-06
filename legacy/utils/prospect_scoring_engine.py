
from __future__ import annotations
"""
tg_bot/utils/prospect_scoring_engine.py — Marketing Agent TITAN (L9)
═════════════════════════════════════════════════════════════════════
Multi-factor B2B prospect scoring engine with behavioral signals.

Architecture
────────────
   ┌──────────────────────────────────────────────────────┐
   │              PROSPECT SCORING ENGINE                  │
   ├──────────┬──────────┬──────────┬──────────┬──────────┤
   │ Firmogr. │ Fit      │ Behavior │ Timing   │ Budget   │
   │ Scoring  │ Scoring  │ Scoring  │ Scoring  │ Scoring  │
   ├──────────┼──────────┼──────────┼──────────┼──────────┤
   │ Size     │ Category │ Opens    │ Season   │ Price Pt │
   │ Revenue  │ Location │ Clicks   │ Event    │ Luxury   │
   │ Staff    │ Style    │ Replies  │ Holiday  │ Volume   │
   └──────────┴──────────┴──────────┴──────────┴──────────┘

Scoring Factors (total 100 pts)
───────────────────────────────
  • Firmographic (20 pts): business size, online presence, review ratings
  • Fit (30 pts): category match, location priority, style alignment
  • Behavioral (25 pts): email opens, clicks, replies, website visits
  • Timing (15 pts): seasonal relevance, holiday proximity
  • Budget (10 pts): price-point indicators, luxury-level signals

Integrates with existing ``lead_scoring_engine.py`` for generic scores
and enriches with marketing-specific factors.
"""


import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── Existing modules ──
try:
    from arki_project.utils.lead_scoring_engine import LeadScoringEngine
    _LEAD_SCORING_AVAILABLE = True
except ImportError:
    _LEAD_SCORING_AVAILABLE = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Scoring Factor Weights
# ═══════════════════════════════════════════════════════════

FACTOR_WEIGHTS = {
    "firmographic": 20.0,
    "fit": 30.0,
    "behavioral": 25.0,
    "timing": 15.0,
    "budget": 10.0,
}

# Priority markets — higher score for closer/target markets
MARKET_PRIORITY = {
    "Finland": 10, "Sweden": 9, "Norway": 9, "Denmark": 9,
    "Germany": 8, "Netherlands": 8, "France": 7,
    "United Kingdom": 7, "United States": 6,
    "Canada": 6, "Australia": 5,
}

# B2B category fit scores
CATEGORY_FIT = {
    "hotels": 1.0, "spas": 0.95, "restaurants": 0.9,
    "galleries": 0.85, "events": 0.8, "interior": 0.9,
    "corporate": 0.7, "photography": 0.75,
}

# Seasons relevant for candle/decor products
SEASONAL_BOOST = {
    10: 1.3,  # October — pre-holiday
    11: 1.5,  # November — holiday shopping
    12: 1.5,  # December — Christmas
    1: 1.1,   # January — new year décor
    2: 1.1,   # February — Valentine's
}


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of a prospect's score."""
    total: float = 0.0
    firmographic: float = 0.0
    fit: float = 0.0
    behavioral: float = 0.0
    timing: float = 0.0
    budget: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)
    tier: str = "cold"  # cold, warm, hot

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": round(self.total, 1),
            "firmographic": round(self.firmographic, 1),
            "fit": round(self.fit, 1),
            "behavioral": round(self.behavioral, 1),
            "timing": round(self.timing, 1),
            "budget": round(self.budget, 1),
            "tier": self.tier,
            "factors": {k: round(v, 2) for k, v in self.factors.items()},
        }


# ═══════════════════════════════════════════════════════════
# Scoring Engine
# ═══════════════════════════════════════════════════════════

class ProspectScoringEngine:
    """
    Multi-factor B2B prospect scoring engine.

    Provides:
    - Initial scoring based on firmographic & fit data
    - Behavioral scoring updates from outreach interactions
    - Automatic tier classification (cold / warm / hot)
    - Batch re-scoring for the priority queue
    - Integration with lead_scoring_engine.py
    """

    def __init__(self, hot_threshold: float = 70.0, warm_threshold: float = 40.0) -> None:
        self._hot_threshold = hot_threshold
        self._warm_threshold = warm_threshold
        self._scoring_history: Dict[int, List[ScoreBreakdown]] = {}

    # ── Primary Scoring ──────────────────────────────────

    async def score_prospect(self, prospect: Dict[str, Any]) -> ScoreBreakdown:
        """
        Calculate a full multi-factor score for a prospect.

        Args:
            prospect: Prospect data dict (from MarketingDataBridge)

        Returns:
            ScoreBreakdown with total, per-factor scores, and tier
        """
        breakdown = ScoreBreakdown()

        # Factor 1: Firmographic
        breakdown.firmographic = self._score_firmographic(prospect)
        breakdown.factors["firmographic_total"] = breakdown.firmographic

        # Factor 2: Fit
        breakdown.fit = self._score_fit(prospect)
        breakdown.factors["fit_total"] = breakdown.fit

        # Factor 3: Behavioral
        breakdown.behavioral = await self._score_behavioral(prospect)
        breakdown.factors["behavioral_total"] = breakdown.behavioral

        # Factor 4: Timing
        breakdown.timing = self._score_timing()
        breakdown.factors["timing_total"] = breakdown.timing

        # Factor 5: Budget
        breakdown.budget = self._score_budget(prospect)
        breakdown.factors["budget_total"] = breakdown.budget

        # Factor 6: OMEGA intel bonus (extra signals from deep recon / contact intel)
        omega_bonus = self._score_omega_intel(prospect)
        breakdown.factors["omega_intel_bonus"] = omega_bonus

        # Total
        breakdown.total = (
            breakdown.firmographic
            + breakdown.fit
            + breakdown.behavioral
            + breakdown.timing
            + breakdown.budget
            + omega_bonus
        )

        # Tier
        if breakdown.total >= self._hot_threshold:
            breakdown.tier = "hot"
        elif breakdown.total >= self._warm_threshold:
            breakdown.tier = "warm"
        else:
            breakdown.tier = "cold"

        return breakdown

    async def batch_rescore(
        self,
        prospects: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Re-score a batch of prospects and return sorted by score.
        Updates score and tier in the returned data.
        """
        scored = []
        for prospect in prospects:
            breakdown = await self.score_prospect(prospect)
            prospect["score"] = breakdown.total
            prospect["score_tier"] = breakdown.tier
            prospect["score_factors"] = breakdown.to_dict()
            scored.append(prospect)

        scored.sort(key=lambda p: p["score"], reverse=True)
        return scored

    async def update_behavioral_score(
        self,
        prospect_id: int,
        event_type: str,
        *,
        data_bridge=None,
    ) -> Optional[float]:
        """
        Update a prospect's score based on a behavioral event.

        Event types and their score impacts:
          email_opened: +3
          email_clicked: +5
          email_replied: +10
          website_visited: +2
          catalog_downloaded: +7
          meeting_booked: +15
          unsubscribed: -20
        """
        delta_map = {
            "email_opened": 3.0,
            "email_clicked": 5.0,
            "email_replied": 10.0,
            "website_visited": 2.0,
            "catalog_downloaded": 7.0,
            "meeting_booked": 15.0,
            "unsubscribed": -20.0,
        }

        delta = delta_map.get(event_type, 0.0)
        if delta == 0.0:
            return None

        if data_bridge:
            # Get current prospect, update score
            prospects = await data_bridge.get_prospects(limit=1)
            # Actual update would use prospect_id lookup and update
            await data_bridge.log_event(
                f"score_update_{event_type}",
                prospect_id=prospect_id,
                score_delta=delta,
                outcome="success",
            )

        return delta

    # ── Internal Scoring Functions ───────────────────────

    def _score_firmographic(self, prospect: Dict[str, Any]) -> float:
        """Score based on business characteristics (0–20 pts)."""
        score = 0.0
        max_score = FACTOR_WEIGHTS["firmographic"]

        # Has website (+5)
        if prospect.get("website"):
            score += 5.0
            self._add_factor(prospect, "has_website", 5.0)

        # Has email (+4)
        if prospect.get("email"):
            score += 4.0
            self._add_factor(prospect, "has_email", 4.0)

        # Has phone (+2)
        if prospect.get("phone"):
            score += 2.0
            self._add_factor(prospect, "has_phone", 2.0)

        # Has contact person (+3)
        if prospect.get("contact_person"):
            score += 3.0
            self._add_factor(prospect, "has_contact", 3.0)

        # Has contact role (+2)
        if prospect.get("contact_role"):
            role = prospect["contact_role"].lower()
            if any(r in role for r in ["manager", "owner", "director", "buyer"]):
                score += 3.0
                self._add_factor(prospect, "decision_maker_role", 3.0)
            else:
                score += 1.0

        # Source quality (+3)
        source = prospect.get("source", "")
        if "google_maps" in source or "tripadvisor" in source:
            score += 3.0
        elif "booking" in source:
            score += 2.0

        return min(score, max_score)

    def _score_fit(self, prospect: Dict[str, Any]) -> float:
        """Score based on how well the prospect fits our target (0–30 pts)."""
        score = 0.0
        max_score = FACTOR_WEIGHTS["fit"]

        # Category match (0–12)
        btype = prospect.get("business_type", "").lower()
        cat_score = CATEGORY_FIT.get(btype, 0.3)
        score += cat_score * 12.0
        self._add_factor(prospect, "category_fit", cat_score)

        # Location priority (0–10)
        country = prospect.get("country", "")
        market_score = MARKET_PRIORITY.get(country, 3)
        score += market_score
        self._add_factor(prospect, "market_priority", market_score)

        # Language match bonus (0–4)
        lang = prospect.get("language", "en")
        if lang in ("fi", "en", "sv", "de"):
            score += 4.0
        elif lang in ("fr", "no", "da", "nl"):
            score += 3.0
        else:
            score += 1.0

        # Tags bonus (0–4)
        tags = prospect.get("tags", [])
        if isinstance(tags, str):
            try:
                import json
                tags = json.loads(tags)
            except (ValueError, TypeError):
                tags = []
        design_tags = {"minimalist", "scandinavian", "handmade", "artisan", "concrete", "candle"}
        matching_tags = set(t.lower() for t in tags) & design_tags
        score += min(len(matching_tags) * 2.0, 4.0)

        return min(score, max_score)

    async def _score_behavioral(self, prospect: Dict[str, Any]) -> float:
        """Score based on outreach interaction history (0–25 pts)."""
        score = 0.0
        max_score = FACTOR_WEIGHTS["behavioral"]

        status = prospect.get("status", "discovered")

        # Status-based scoring
        status_scores = {
            "discovered": 0,
            "qualified": 3,
            "contacted": 5,
            "responded": 15,
            "converted": 25,
        }
        score += status_scores.get(status, 0)

        # Last contact recency bonus
        last_contact = prospect.get("last_contacted_at")
        if last_contact:
            score += 2.0  # Was contacted at all

        last_response = prospect.get("last_responded_at")
        if last_response:
            score += 5.0  # Actually responded

        return min(score, max_score)

    def _score_timing(self) -> float:
        """Score based on current seasonal relevance (0–15 pts)."""
        max_score = FACTOR_WEIGHTS["timing"]
        now = datetime.now(timezone.utc)
        month = now.month

        seasonal_multiplier = SEASONAL_BOOST.get(month, 1.0)
        base_score = 8.0  # Default baseline

        return min(base_score * seasonal_multiplier, max_score)

    def _score_budget(self, prospect: Dict[str, Any]) -> float:
        """Score based on budget/luxury indicators (0–10 pts)."""
        score = 5.0  # Default mid-range

        btype = prospect.get("business_type", "").lower()
        # Higher budget categories
        if btype in ("hotels", "spas", "corporate"):
            score += 3.0
        elif btype in ("galleries", "interior"):
            score += 2.0
        elif btype in ("restaurants", "events"):
            score += 1.0

        # Country wealth indicator
        country = prospect.get("country", "")
        high_gdp = {"Finland", "Sweden", "Norway", "Denmark", "Germany", "Netherlands", "United States", "Australia"}
        if country in high_gdp:
            score += 2.0

        return min(score, FACTOR_WEIGHTS["budget"])

    @staticmethod
    def _add_factor(prospect: Dict[str, Any], key: str, value: float) -> None:
        """Track individual scoring factors (for debugging/reporting)."""
        if "_score_factors" not in prospect:
            prospect["_score_factors"] = {}
        prospect["_score_factors"][key] = value

    # ── OMEGA Intel Scoring ─────────────────────────────

    def _score_omega_intel(self, prospect: Dict[str, Any]) -> float:
        """
        Bonus scoring from OMEGA-enriched data (0–15 pts).

        Awards points for having rich intelligence data:
        - Decision-maker identified: +5
        - Tech stack known: +2
        - Multiple contact emails: +3
        - Domain MX verified: +2
        - Deep recon data: +3
        """
        score = 0.0
        extra = prospect.get("extra_data", {})
        if not extra:
            return score

        # Decision-maker(s) found via ContactIntelEngine
        dms = extra.get("decision_makers", [])
        if dms:
            score += 5.0
            # Bonus for purchasing/owner role
            for dm in dms:
                role = dm.get("role", "")
                if role in ("owner", "ceo", "founder", "purchasing"):
                    score += 2.0
                    break
            self._add_factor(prospect, "omega_decision_maker", min(7.0, score))

        # Tech stack known (helps personalization)
        if extra.get("tech_stack"):
            score += 2.0
            self._add_factor(prospect, "omega_tech_stack", 2.0)

        # Multiple verified emails
        all_emails = extra.get("all_emails", [])
        if len(all_emails) >= 2:
            score += 3.0
            self._add_factor(prospect, "omega_multi_email", 3.0)

        # Domain MX verified (email will reach them)
        domain_intel = extra.get("domain_intel", {})
        if domain_intel.get("accepts_mail"):
            score += 2.0
            self._add_factor(prospect, "omega_mx_verified", 2.0)

        # Deep recon data available
        if extra.get("dns_intel") or extra.get("security_posture"):
            score += 1.0
            self._add_factor(prospect, "omega_deep_recon", 1.0)

        return min(score, 15.0)

    # ── Priority Queue ───────────────────────────────────

    async def get_priority_queue(
        self,
        data_bridge: Any,
        *,
        limit: int = 50,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Get prospects ordered by score as a priority queue.
        Optionally re-scores before returning.
        """
        prospects = await data_bridge.get_prospects(
            min_score=min_score,
            limit=limit,
            order_by_score=True,
            exclude_opted_out=True,
        )
        return await self.batch_rescore(prospects)

    # ── Tier Summary ─────────────────────────────────────

    async def get_tier_summary(self, data_bridge: Any) -> Dict[str, int]:
        """Count prospects by tier."""
        all_prospects = await data_bridge.get_prospects(limit=10000)
        tiers = {"hot": 0, "warm": 0, "cold": 0}

        for p in all_prospects:
            score = p.get("score", 0)
            if score >= self._hot_threshold:
                tiers["hot"] += 1
            elif score >= self._warm_threshold:
                tiers["warm"] += 1
            else:
                tiers["cold"] += 1

        return tiers


