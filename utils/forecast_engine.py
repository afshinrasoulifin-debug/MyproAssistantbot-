
from __future__ import annotations
"""
tg_bot/utils/forecast_engine.py — Sales Forecasting Engine v1.0
════════════════════════════════════════════════════════════════
Real forecasting from actual sales data (not just AI guessing).

Methods:
  • Moving Average (simple + weighted)
  • Linear Regression
  • Seasonal decomposition
  • Growth rate analysis
  • Revenue projection
"""


import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SalesDataPoint:
    date: datetime
    amount: float
    quantity: int = 1
    product: str = ""
    platform: str = ""
    customer_id: int = 0


@dataclass
class ForecastResult:
    period: str              # "next_7d" / "next_30d" / "next_quarter"
    predicted_revenue: float
    predicted_orders: int
    confidence: float        # 0-1
    trend: str               # "growing" / "stable" / "declining"
    growth_rate: float       # % change
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SalesInsight:
    metric: str
    value: Any
    change: float = 0.0      # % change from previous period
    trend: str = "stable"


class ForecastEngine:
    """
    Sales forecasting from real transaction data.
    
    Usage:
        engine = ForecastEngine()
        
        # Add sales data
        engine.add_sale(SalesDataPoint(date=..., amount=45.0))
        
        # Or load from CRM
        engine.load_from_records(finance_records)
        
        # Get forecast
        forecast = engine.forecast_next_30_days()
        
        # Get insights
        insights = engine.get_insights()
    """

    def __init__(self) -> None:
        self._data: List[SalesDataPoint] = []

    def add_sale(self, point: SalesDataPoint) -> None:
        self._data.append(point)
        self._data.sort(key=lambda p: p.date)

    def load_from_records(self, records: List[Dict[str, Any]]) -> Any:
        """Load from database FinanceRecord format."""
        for r in records:
            try:
                date = r.get("date") or r.get("created_at")
                if isinstance(date, str):
                    date = datetime.fromisoformat(date)
                self._data.append(SalesDataPoint(
                    date=date,
                    amount=float(r.get("amount", 0)),
                    quantity=int(r.get("quantity", 1)),
                    product=r.get("description", ""),
                    platform=r.get("category", ""),
                    customer_id=int(r.get("user_id", 0)),
                ))
            except (ValueError, TypeError):
                continue
        self._data.sort(key=lambda p: p.date)

    # ─── Core Forecasting ───

    def forecast(self, days_ahead: int = 30) -> ForecastResult:
        """Forecast revenue for next N days."""
        if len(self._data) < 3:
            return ForecastResult(
                period=f"next_{days_ahead}d",
                predicted_revenue=0,
                predicted_orders=0,
                confidence=0,
                trend="unknown",
                growth_rate=0,
                details={"error": "حداقل ۳ فروش ثبت‌شده نیاز است"},
            )

        daily = self._aggregate_daily()
        if len(daily) < 2:
            return ForecastResult(
                period=f"next_{days_ahead}d",
                predicted_revenue=0,
                predicted_orders=0,
                confidence=0,
                trend="unknown",
                growth_rate=0,
            )

        # Method 1: Weighted Moving Average
        wma_revenue = self._weighted_moving_average(
            [d["revenue"] for d in daily], window=min(7, len(daily))
        )

        # Method 2: Linear Regression
        lr_revenue, slope = self._linear_regression(
            [d["revenue"] for d in daily]
        )

        # Combine predictions (60% WMA + 40% LR)
        daily_prediction = 0.6 * wma_revenue + 0.4 * lr_revenue
        total_prediction = daily_prediction * days_ahead

        # Trend from slope
        avg_daily = statistics.mean([d["revenue"] for d in daily])
        if avg_daily > 0:
            growth_rate = (slope / avg_daily) * 100
        else:
            growth_rate = 0

        if growth_rate > 5:
            trend = "growing"
        elif growth_rate < -5:
            trend = "declining"
        else:
            trend = "stable"

        # Confidence based on data consistency
        revenues = [d["revenue"] for d in daily]
        if len(revenues) > 1:
            cv = statistics.stdev(revenues) / max(statistics.mean(revenues), 0.01)
            confidence = max(0.2, min(0.95, 1.0 - cv))
        else:
            confidence = 0.3

        # Orders prediction
        avg_orders = statistics.mean([d["orders"] for d in daily])
        predicted_orders = round(avg_orders * days_ahead)

        return ForecastResult(
            period=f"next_{days_ahead}d",
            predicted_revenue=round(total_prediction, 2),
            predicted_orders=predicted_orders,
            confidence=round(confidence, 2),
            trend=trend,
            growth_rate=round(growth_rate, 1),
            details={
                "daily_avg": round(daily_prediction, 2),
                "data_points": len(daily),
                "method": "WMA+LR blend",
                "wma_daily": round(wma_revenue, 2),
                "lr_daily": round(lr_revenue, 2),
            }
        )

    def forecast_next_7_days(self) -> ForecastResult:
        return self.forecast(7)

    def forecast_next_30_days(self) -> ForecastResult:
        return self.forecast(30)

    def forecast_next_quarter(self) -> ForecastResult:
        return self.forecast(90)

    # ─── Insights ───

    def get_insights(self) -> List[SalesInsight]:
        """Generate actionable sales insights from data."""
        insights = []

        if len(self._data) < 2:
            return [SalesInsight(
                metric="وضعیت",
                value="داده کافی نیست — حداقل ۲ فروش ثبت کنید",
            )]

        daily = self._aggregate_daily()
        revenues = [d["revenue"] for d in daily]
        orders = [d["orders"] for d in daily]

        # Total revenue
        total_rev = sum(revenues)
        insights.append(SalesInsight(
            metric="کل درآمد",
            value=f"€{total_rev:,.2f}",
        ))

        # Average order value
        if sum(orders) > 0:
            aov = total_rev / sum(orders)
            insights.append(SalesInsight(
                metric="میانگین سفارش",
                value=f"€{aov:,.2f}",
            ))

        # Best day
        if daily:
            best = max(daily, key=lambda d: d["revenue"])
            insights.append(SalesInsight(
                metric="بهترین روز",
                value=f"{best['date']} — €{best['revenue']:,.2f}",
            ))

        # Recent trend (last 7 vs previous 7)
        if len(daily) >= 14:
            recent_7 = sum(d["revenue"] for d in daily[-7:])
            prev_7 = sum(d["revenue"] for d in daily[-14:-7])
            if prev_7 > 0:
                change = ((recent_7 - prev_7) / prev_7) * 100
                trend = "رشد" if change > 0 else "کاهش"
                insights.append(SalesInsight(
                    metric="روند هفتگی",
                    value=f"{trend} {abs(change):.1f}%",
                    change=change,
                    trend="growing" if change > 5 else "declining" if change < -5 else "stable",
                ))

        # Top product
        product_rev = defaultdict(float)
        for d in self._data:
            if d.product:
                product_rev[d.product] += d.amount
        if product_rev:
            top = max(product_rev, key=product_rev.get)
            insights.append(SalesInsight(
                metric="پرفروش‌ترین",
                value=f"{top} — €{product_rev[top]:,.2f}",
            ))

        # Top platform
        plat_rev = defaultdict(float)
        for d in self._data:
            if d.platform:
                plat_rev[d.platform] += d.amount
        if plat_rev:
            top = max(plat_rev, key=plat_rev.get)
            insights.append(SalesInsight(
                metric="بهترین پلتفرم",
                value=f"{top} — €{plat_rev[top]:,.2f}",
            ))

        return insights

    # ─── Internals ───

    def _aggregate_daily(self) -> List[Dict[str, Any]]:
        """Group sales by day."""
        by_day: Dict[str, Dict] = {}
        for d in self._data:
            key = d.date.strftime("%Y-%m-%d")
            if key not in by_day:
                by_day[key] = {"date": key, "revenue": 0.0, "orders": 0}
            by_day[key]["revenue"] += d.amount
            by_day[key]["orders"] += d.quantity

        return sorted(by_day.values(), key=lambda x: x["date"])

    @staticmethod
    def _weighted_moving_average(values: List[float], window: int = 7) -> float:
        """Weighted MA — recent values have higher weight."""
        if not values:
            return 0
        recent = values[-window:]
        weights = list(range(1, len(recent) + 1))
        total_weight = sum(weights)
        return sum(v * w for v, w in zip(recent, weights)) / total_weight

    @staticmethod
    def _linear_regression(values: List[float]) -> Tuple[float, float]:
        """Simple linear regression. Returns (prediction, slope)."""
        n = len(values)
        if n < 2:
            return (values[0] if values else 0, 0)

        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, values))
        den = sum((xi - x_mean) ** 2 for xi in x)

        if den == 0:
            return (y_mean, 0)

        slope = num / den
        intercept = y_mean - slope * x_mean

        # Predict next value
        prediction = intercept + slope * n
        return (max(0, prediction), slope)


# ═══════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════

_engine: Optional[ForecastEngine] = None

def get_forecast_engine() -> ForecastEngine:
    global _engine
    if _engine is None:
        _engine = ForecastEngine()
    return _engine


