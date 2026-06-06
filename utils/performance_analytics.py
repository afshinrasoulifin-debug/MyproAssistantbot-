
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
utils/performance_analytics.py — Performance Analytics Engine v26.0
═══════════════════════════════════════════════════════════════════
Tracks model performance, user satisfaction, and system health.

Features:
  - Per-model latency tracking with percentiles
  - Success/failure rates per provider
  - Best model per query type (auto-learns)
  - Auto-demote: models failing >40% get lower priority
  - Auto-promote: models succeeding >90% get higher priority
  - Admin /stats command data source
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("arki.analytics")


@dataclass
class ModelMetrics:
    """Performance metrics for a single model."""
    model_key: str
    total_calls: int = 0
    successes: int = 0
    failures: int = 0
    total_latency_ms: float = 0
    latencies: List[float] = field(default_factory=list)
    quality_scores: List[float] = field(default_factory=list)
    last_failure_time: float = 0
    consecutive_failures: int = 0
    demoted: bool = False
    demoted_at: float = 0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successes / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def avg_quality(self) -> float:
        if not self.quality_scores:
            return 0.0
        return sum(self.quality_scores) / len(self.quality_scores)


@dataclass
class ProviderMetrics:
    """Aggregate metrics for a provider."""
    provider: str
    total_calls: int = 0
    successes: int = 0
    total_latency_ms: float = 0

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successes / self.total_calls

    @property
    def avg_latency_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls


class PerformanceAnalytics:
    """
    Central performance tracking and analytics engine.

    Tracks every model call, builds performance profiles,
    and provides data for smart routing decisions.
    """

    # Auto-demote threshold
    DEMOTE_FAILURE_RATE = 0.40    # Demote if >40% failure
    DEMOTE_MIN_CALLS = 10         # Need at least 10 calls to judge
    DEMOTE_CONSECUTIVE = 5         # Demote after 5 consecutive failures
    PROMOTE_SUCCESS_RATE = 0.90   # Promote back if >90% success
    PROMOTE_MIN_CALLS = 5         # Need 5 calls after demotion

    # Keep only recent data (prevent memory leak)
    MAX_LATENCIES_PER_MODEL = 200
    MAX_QUALITY_SCORES = 200

    def __init__(self) -> None:
        self._models: Dict[str, ModelMetrics] = {}
        self._providers: Dict[str, ProviderMetrics] = {}
        self._query_type_winners: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._start_time: float = time.time()

    def record_call(
        self,
        model_key: str,
        provider: str,
        success: bool,
        latency_ms: float,
        quality_score: float = 0.0,
        query_type: str = "general",
    ) -> None:
        """Record a model call result."""
        # Model metrics
        if model_key not in self._models:
            self._models[model_key] = ModelMetrics(model_key=model_key)
        m = self._models[model_key]

        m.total_calls += 1
        m.total_latency_ms += latency_ms
        m.latencies.append(latency_ms)
        if len(m.latencies) > self.MAX_LATENCIES_PER_MODEL:
            m.latencies = m.latencies[-self.MAX_LATENCIES_PER_MODEL:]

        if quality_score > 0:
            m.quality_scores.append(quality_score)
            if len(m.quality_scores) > self.MAX_QUALITY_SCORES:
                m.quality_scores = m.quality_scores[-self.MAX_QUALITY_SCORES:]

        if success:
            m.successes += 1
            m.consecutive_failures = 0
            # Check if should un-demote
            if m.demoted:
                recent_calls = min(m.total_calls, self.PROMOTE_MIN_CALLS)
                recent_successes = sum(1 for _ in m.latencies[-recent_calls:])  # Approximate
                if m.success_rate > self.PROMOTE_SUCCESS_RATE and recent_calls >= self.PROMOTE_MIN_CALLS:
                    m.demoted = False
                    logger.info("📈 Model %s PROMOTED back (success_rate=%.1f%%)", model_key, m.success_rate * 100)
                    # v26.1: Persist state on promote
                    asyncio.get_event_loop().create_task(self.save_state_to_db())
        else:
            m.failures += 1
            m.last_failure_time = time.time()
            m.consecutive_failures += 1
            # Check auto-demote
            if (
                not m.demoted
                and m.total_calls >= self.DEMOTE_MIN_CALLS
                and (m.success_rate < (1 - self.DEMOTE_FAILURE_RATE) or m.consecutive_failures >= self.DEMOTE_CONSECUTIVE)
            ):
                m.demoted = True
                m.demoted_at = time.time()
                logger.warning(
                    "📉 Model %s AUTO-DEMOTED (success_rate=%.1f%%, consecutive_failures=%d)",
                    model_key, m.success_rate * 100, m.consecutive_failures,
                )
                # v26.1: Persist state on demote
                asyncio.get_event_loop().create_task(self.save_state_to_db())

        # Provider metrics
        if provider not in self._providers:
            self._providers[provider] = ProviderMetrics(provider=provider)
        p = self._providers[provider]
        p.total_calls += 1
        p.total_latency_ms += latency_ms
        if success:
            p.successes += 1

        # Query type tracking
        if success and quality_score > 0.5:
            self._query_type_winners[query_type][model_key] += 1

    def is_demoted(self, model_key: str) -> bool:
        """Check if a model is currently demoted."""
        m = self._models.get(model_key)
        if not m:
            return False
        return m.demoted

    def get_best_model_for_query_type(self, query_type: str, candidates: List[str]) -> Optional[str]:
        """
        Get the historically best model for a query type from candidates.
        Returns None if no data available.
        """
        if query_type not in self._query_type_winners:
            return None

        winners = self._query_type_winners[query_type]
        best = None
        best_score = 0
        for model in candidates:
            if model in winners and winners[model] > best_score:
                if not self.is_demoted(model):
                    best = model
                    best_score = winners[model]

        return best

    def get_model_stats(self, model_key: str) -> Optional[Dict[str, Any]]:
        """Get detailed stats for a specific model."""
        m = self._models.get(model_key)
        if not m:
            return None
        return {
            "model_key": model_key,
            "total_calls": m.total_calls,
            "success_rate": round(m.success_rate * 100, 1),
            "avg_latency_ms": round(m.avg_latency_ms, 0),
            "p95_latency_ms": round(m.p95_latency_ms, 0),
            "avg_quality": round(m.avg_quality, 3),
            "demoted": m.demoted,
            "consecutive_failures": m.consecutive_failures,
        }

    def get_dashboard(self) -> Dict[str, Any]:
        """
        Get full analytics dashboard data.
        Used by admin /stats command.
        """
        uptime = time.time() - self._start_time

        # Top models by calls
        top_by_calls = sorted(
            self._models.values(),
            key=lambda m: m.total_calls,
            reverse=True,
        )[:15]

        # Top by quality
        top_by_quality = sorted(
            [m for m in self._models.values() if m.avg_quality > 0],
            key=lambda m: m.avg_quality,
            reverse=True,
        )[:10]

        # Demoted models
        demoted = [m.model_key for m in self._models.values() if m.demoted]

        # Best per query type
        best_per_type = {}
        for qt, winners in self._query_type_winners.items():
            if winners:
                best = max(winners.items(), key=lambda x: x[1])
                best_per_type[qt] = {"model": best[0], "wins": best[1]}

        return {
            "uptime_seconds": round(uptime, 0),
            "total_models_tracked": len(self._models),
            "total_calls": sum(m.total_calls for m in self._models.values()),
            "overall_success_rate": round(
                sum(m.successes for m in self._models.values()) /
                max(1, sum(m.total_calls for m in self._models.values())) * 100, 1
            ),
            "providers": {
                name: {
                    "calls": p.total_calls,
                    "success_rate": round(p.success_rate * 100, 1),
                    "avg_latency_ms": round(p.avg_latency_ms, 0),
                }
                for name, p in self._providers.items()
            },
            "top_models_by_calls": [
                {
                    "model": m.model_key,
                    "calls": m.total_calls,
                    "success_rate": round(m.success_rate * 100, 1),
                    "avg_latency": round(m.avg_latency_ms, 0),
                }
                for m in top_by_calls
            ],
            "top_models_by_quality": [
                {
                    "model": m.model_key,
                    "avg_quality": round(m.avg_quality, 3),
                    "calls": m.total_calls,
                }
                for m in top_by_quality
            ],
            "demoted_models": demoted,
            "best_per_query_type": best_per_type,
        }

    def format_stats_message(self) -> str:
        """Format analytics into a Farsi message for /stats command."""
        dash = self.get_dashboard()

        lines = [
            "📊 *آمار عملکرد Arki Engine*",
            f"⏱ آپتایم: {dash['uptime_seconds'] / 3600:.1f} ساعت",
            f"📈 کل درخواست‌ها: {dash['total_calls']:,}",
            f"✅ نرخ موفقیت: {dash['overall_success_rate']}%",
            f"🤖 مدل‌های ردیابی شده: {dash['total_models_tracked']}",
            "",
            "🏆 *بهترین مدل‌ها (بر اساس تعداد):*",
        ]

        for m in dash["top_models_by_calls"][:5]:
            lines.append(
                f"  • `{m['model']}` — {m['calls']} بار | "
                f"✅{m['success_rate']}% | ⏱{m['avg_latency']}ms"
            )

        if dash["demoted_models"]:
            lines.append("")
            lines.append("📉 *مدل‌های تنزل‌یافته:*")
            for dm in dash["demoted_models"]:
                lines.append(f"  ⚠️ `{dm}`")

        if dash["best_per_query_type"]:
            lines.append("")
            lines.append("🎯 *بهترین مدل هر نوع سوال:*")
            for qt, info in dash["best_per_query_type"].items():
                lines.append(f"  • {qt}: `{info['model']}` ({info['wins']} بار برنده)")

        return "\n".join(lines)


    # ═══ v26.1: Database Persistence ═══════════════════

    async def save_state_to_db(self) -> int:
        """Persist demote/promote state + key metrics to database.
        
        Called on demote/promote events and periodically.
        Returns number of models saved.
        """
        try:
            from arki_project.database.connection import get_session
            from arki_project.database.models import ModelPerformanceState
            from sqlalchemy import select as _sel

            saved = 0
            async with get_session() as session:
                for mk, m in self._models.items():
                    existing = (await session.execute(
                        _sel(ModelPerformanceState).where(
                            ModelPerformanceState.model_key == mk
                        )
                    )).scalar_one_or_none()

                    if existing:
                        existing.total_calls = m.total_calls
                        existing.successes = m.successes
                        existing.failures = m.failures
                        existing.total_latency_ms = m.total_latency_ms
                        existing.avg_quality = m.avg_quality
                        existing.demoted = m.demoted
                        existing.consecutive_failures = m.consecutive_failures
                        if m.demoted and m.demoted_at:
                            import datetime
                            existing.demoted_at = datetime.datetime.fromtimestamp(
                                m.demoted_at, tz=datetime.timezone.utc
                            )
                    else:
                        import datetime
                        new_record = ModelPerformanceState(
                            model_key=mk,
                            total_calls=m.total_calls,
                            successes=m.successes,
                            failures=m.failures,
                            total_latency_ms=m.total_latency_ms,
                            avg_quality=m.avg_quality,
                            demoted=m.demoted,
                            consecutive_failures=m.consecutive_failures,
                            demoted_at=(
                                datetime.datetime.fromtimestamp(m.demoted_at, tz=datetime.timezone.utc)
                                if m.demoted and m.demoted_at else None
                            ),
                        )
                        session.add(new_record)
                    saved += 1
                await session.commit()
            logger.info("💾 Analytics state saved: %d models persisted", saved)
            return saved
        except ArkiBaseError as e:
            logger.error("Failed to save analytics state: %s", e)
            return 0

    async def load_state_from_db(self) -> int:
        """Load persisted model state from database on startup.
        
        Restores demote/promote status and accumulated metrics.
        Returns number of models loaded.
        """
        try:
            from arki_project.database.connection import get_session
            from arki_project.database.models import ModelPerformanceState
            from sqlalchemy import select as _sel

            loaded = 0
            async with get_session() as session:
                result = await session.execute(_sel(ModelPerformanceState))
                rows = result.scalars().all()

                for row in rows:
                    mk = row.model_key
                    if mk not in self._models:
                        self._models[mk] = ModelMetrics(model_key=mk)
                    m = self._models[mk]
                    m.total_calls = row.total_calls
                    m.successes = row.successes
                    m.failures = row.failures
                    m.total_latency_ms = row.total_latency_ms
                    m.demoted = row.demoted
                    m.consecutive_failures = row.consecutive_failures
                    if row.demoted_at:
                        m.demoted_at = row.demoted_at.timestamp()
                    loaded += 1

            logger.info("📂 Analytics state loaded: %d models restored", loaded)
            return loaded
        except ArkiBaseError as e:
            logger.warning("Failed to load analytics state (first run?): %s", e)
            return 0


# ═══════════════════ SINGLETON ═══════════════════

_analytics: PerformanceAnalytics | None = None

def get_analytics() -> PerformanceAnalytics:
    """Get or create singleton PerformanceAnalytics."""
    global _analytics
    if _analytics is None:
        _analytics = PerformanceAnalytics()
    return _analytics


