
from __future__ import annotations
"""
tg_bot/services/sales_service.py — Sales Business Logic
Extracted from handlers/sales_brain.py to separate business logic from handler layer.

This module contains:
  • Lead scoring algorithms
  • Sales funnel analytics
  • CRM data operations
  • Revenue forecasting
  • Competitor analysis helpers
"""
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

# ── TITANIUM v29.0 Integration ──


# ── Infrastructure access ──
try:
    from arki_project.services.infra_bridge import get_service_bridge 
except ImportError:
    _get_svc_infra = lambda: None


logger = logging.getLogger(__name__)


@dataclass
class Lead:
    """Structured lead data."""
    user_id: int
    name: str = ""
    score: float = 0.0
    stage: str = "awareness"  # awareness → interest → decision → action
    source: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SalesForecast:
    """Revenue forecast result."""
    period: str = ""
    expected_revenue: float = 0.0
    confidence: float = 0.0
    growth_rate: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)


class SalesService:
    """Business logic for sales operations."""

    def __init__(self):
        self._leads: Dict[int, Lead] = {}

    def score_lead(self, user_id: int, interactions: int, recency_days: int,
                   value: float = 0.0) -> Lead:
        """Score a lead using RFM (Recency, Frequency, Monetary) model."""
        # RFM scoring
        recency_score = max(0, 100 - recency_days * 2)
        frequency_score = min(100, interactions * 10)
        monetary_score = min(100, value / 10)
        total_score = (recency_score * 0.3 + frequency_score * 0.4 + monetary_score * 0.3)

        # Determine stage
        if total_score > 75:
            stage = "action"
        elif total_score > 50:
            stage = "decision"
        elif total_score > 25:
            stage = "interest"
        else:
            stage = "awareness"

        lead = Lead(user_id=user_id, score=total_score, stage=stage)
        self._leads[user_id] = lead
        return lead

    def get_funnel_stats(self) -> Dict[str, int]:
        """Get sales funnel statistics."""
        funnel = {"awareness": 0, "interest": 0, "decision": 0, "action": 0}
        for lead in self._leads.values():
            funnel[lead.stage] = funnel.get(lead.stage, 0) + 1
        return funnel

    def forecast(self, historical_data: List[float], periods: int = 3) -> SalesForecast:
        """Simple revenue forecast using moving average."""
        if not historical_data:
            return SalesForecast()

        avg = sum(historical_data) / len(historical_data)
        if len(historical_data) > 1:
            growth = (historical_data[-1] - historical_data[0]) / max(1, len(historical_data) - 1)
            growth_rate = growth / max(1, avg) * 100
        else:
            growth_rate = 0

        return SalesForecast(
            period=f"next_{periods}_periods",
            expected_revenue=avg * (1 + growth_rate / 100) * periods,
            confidence=min(0.95, 0.5 + len(historical_data) * 0.05),
            growth_rate=round(growth_rate, 2),
        )

    def competitor_analysis(self, competitors: List[Dict]) -> List[Dict]:
        """Score competitors based on available data."""
        scored = []
        for comp in competitors:
            score = 0
            score += comp.get("market_share", 0) * 2
            score += comp.get("growth_rate", 0) * 3
            score -= comp.get("price_advantage", 0) * 1.5
            scored.append({**comp, "threat_score": round(score, 1)})
        return sorted(scored, key=lambda x: x["threat_score"], reverse=True)


_service: Optional[SalesService] = None

def get_sales_service() -> SalesService:
    global _service
    if _service is None:
        _service = SalesService()
    return _service


