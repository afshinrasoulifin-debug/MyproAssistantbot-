
from __future__ import annotations
"""
tg_bot/utils/titanium/health_monitor.py — Active Deep Health Monitor v10.3.1
══════════════════════════════════════════════════════════════════════
Periodically checks AI provider health with deep probes:
  1. Endpoint reachable (HTTP level)
  2. API key valid (auth level)
  3. Model responds (inference level)

Updates orchestrator tier scoring based on health results.

Ported from: TITANIUM ZKI transport/health_monitor.ts
"""


import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Any

from arki_project.utils.titanium.ai_orchestrator import (
    TitaniumOrchestrator, AIProvider
)
from arki_project.utils.titanium.shielded_client import get_shielded_pool

logger = logging.getLogger("titanium.health_monitor")


class HealthStatus(str, Enum):
    HEALTHY = "healthy"         # All 3 checks pass
    DEGRADED = "degraded"       # Reachable but slow or partial failure
    UNHEALTHY = "unhealthy"     # Unreachable or auth failure


@dataclass(slots=True)
class ProviderHealthResult:
    """Result of a single provider health check."""
    provider_id: str
    status: HealthStatus
    reachable: bool = False
    auth_valid: bool = False
    inference_ok: bool = False
    latency_ms: float = 0.0
    error: Optional[str] = None
    checked_at: float = 0.0


class HealthMonitor:
    """
    Active health monitor for AI providers.

    Runs as an asyncio background task at configurable intervals.
    Updates orchestrator tier configs based on health results.
    """

    def __init__(
        self,
        orchestrator: TitaniumOrchestrator,
        interval: int = 15,  # v10.4: Was 60s
        probe_timeout: float = 10.0,
    ) -> None:
        self.orchestrator = orchestrator
        self.interval = interval
        self.probe_timeout = probe_timeout
        self._task: Optional[asyncio.Task] = None
        self._results: Dict[str, ProviderHealthResult] = {}
        self._running = False

    async def start(self) -> Any:
        """Start the health monitor background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitor started (interval=%ds)", self.interval)

    async def stop(self) -> Any:
        """Stop the health monitor."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitor stopped")

    async def _monitor_loop(self) -> Any:
        """Main monitoring loop with immediate re-probe on failure.

        v10.4: When an UNHEALTHY provider is detected, schedule an immediate
        re-probe after 3 seconds to confirm (not transient). Reduces
        false-positive detection lag from 15s to ~3s.
        """
        while self._running:
            try:
                unhealthy_found = await self._run_health_checks()

                # Immediate re-probe: if any provider went UNHEALTHY,
                # wait 3s and re-check ONLY the unhealthy ones
                if unhealthy_found and self._running:
                    await asyncio.sleep(3.0)
                    await self._reprobe_unhealthy()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Health check cycle error: %s", exc)

            await asyncio.sleep(self.interval)

    async def _reprobe_unhealthy(self) -> Any:
        """Re-probe only providers that were marked UNHEALTHY.

        Confirms failure is real (not transient network blip).
        If the re-probe succeeds, immediately restore to HEALTHY.
        """
        unhealthy_ids = [
            pid for pid, result in self._results.items()
            if result.status == HealthStatus.UNHEALTHY
        ]
        if not unhealthy_ids:
            return

        logger.info("Re-probing %d unhealthy providers: %s", len(unhealthy_ids), unhealthy_ids)

        providers: Dict[str, AIProvider] = {}
        for tier_config in self.orchestrator._tiers.values():
            for provider in tier_config.providers:
                if provider.id in unhealthy_ids:
                    providers[provider.id] = provider

        tasks = [self._check_provider(p) for p in providers.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, ProviderHealthResult):
                old_status = self._results.get(
                    result.provider_id,
                    ProviderHealthResult(provider_id=result.provider_id, status=HealthStatus.UNHEALTHY),
                ).status
                self._results[result.provider_id] = result

                if result.status == HealthStatus.HEALTHY and old_status == HealthStatus.UNHEALTHY:
                    logger.info("Provider %s recovered on re-probe (transient)", result.provider_id)
                    self.orchestrator._scorer.record(result.provider_id, True, result.latency_ms)
                elif result.status == HealthStatus.UNHEALTHY:
                    logger.warning("Provider %s confirmed UNHEALTHY on re-probe", result.provider_id)

    async def _run_health_checks(self) -> bool:
        """Run health checks on all providers in parallel.

        Returns True if any UNHEALTHY provider was detected (triggers re-probe).
        """
        # Collect all unique providers across tiers
        providers: Dict[str, AIProvider] = {}
        for tier_config in self.orchestrator._tiers.values():
            for provider in tier_config.providers:
                if provider.id not in providers:
                    providers[provider.id] = provider

        if not providers:
            return

        # Run checks in parallel
        tasks = []
        for provider in providers.values():
            tasks.append(self._check_provider(provider))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and feed adaptive scorer
        for result in results:
            if isinstance(result, ProviderHealthResult):
                self._results[result.provider_id] = result

                # Feed health results into adaptive scorer
                scorer = self.orchestrator._scorer
                if result.status == HealthStatus.HEALTHY:
                    scorer.record(result.provider_id, True, result.latency_ms)
                elif result.status == HealthStatus.DEGRADED:
                    scorer.record(result.provider_id, False, result.latency_ms * 2)
                    logger.warning(
                        "Provider %s: DEGRADED (reachable=%s, auth=%s, inference=%s, latency=%.0fms)",
                        result.provider_id, result.reachable, result.auth_valid,
                        result.inference_ok, result.latency_ms,
                    )
                else:
                    scorer.record(result.provider_id, False, result.latency_ms * 5)
                    logger.warning(
                        "Provider %s: UNHEALTHY (reachable=%s, auth=%s, inference=%s, error=%s)",
                        result.provider_id, result.reachable, result.auth_valid,
                        result.inference_ok, result.error or "unknown",
                    )

                # v10.4.0: Feed SLA tracker with health check results
                try:
                    from arki_project.utils.titanium import get_sla_tracker
                    sla = get_sla_tracker()
                    sla.record_check(
                        success=(result.status == HealthStatus.HEALTHY),
                        latency_ms=result.latency_ms,
                        provider=result.provider_id,
                    )
                except Exception as _err:
                    logger.warning("Suppressed error: %s", _err)

        # v10.4: Signal whether any provider is unhealthy (triggers re-probe)
        return any(
            r.status == HealthStatus.UNHEALTHY
            for r in self._results.values()
        )

    async def _check_provider(self, provider: AIProvider) -> ProviderHealthResult:
        """
        Deep health check for a single provider.

        Three layers:
          1. HTTP reachable (can we connect?)
          2. Auth valid (does the API key work?)
          3. Inference OK (does the model respond?)
        """
        t0 = time.monotonic()
        result = ProviderHealthResult(
            provider_id=provider.id,
            status=HealthStatus.UNHEALTHY,
            checked_at=time.time(),
        )

        pool = get_shielded_pool()

        try:
            if provider.format == "gemini":
                # Gemini: test with minimal request
                test_body = {
                    "contents": [{"role": "user", "parts": [{"text": "hi"}]}],
                    "generationConfig": {"maxOutputTokens": 10},
                }
                resp = await pool.post(
                provider.url,
                json_data=test_body,
                timeout=self.probe_timeout,
                add_jitter=False,
                provider_name=provider.id,
                )
            else:
                # OpenAI-compatible: test with minimal request
                headers = {}
                if provider.api_key:
                    headers["Authorization"] = f"Bearer {provider.api_key}"

                test_body = {
                    "model": provider.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 10,
                }
                resp = await pool.post(
                provider.url,
                json_data=test_body,
                headers=headers,
                timeout=self.probe_timeout,
                add_jitter=False,
                provider_name=provider.id,
                )

            result.latency_ms = (time.monotonic() - t0) * 1000

            # Check 1: reachable
            result.reachable = resp.status > 0

            # Check 2: auth valid (not 401/403)
            result.auth_valid = resp.status not in (401, 403)

            # Check 3: inference OK
            if resp.success:
                data = resp.json()
                # OpenAI format
                if data.get("choices") or data.get("candidates") or data.get("text"):
                    result.inference_ok = True

            # Determine status
            if result.reachable and result.auth_valid and result.inference_ok:
                result.status = HealthStatus.HEALTHY
            elif result.reachable and result.auth_valid:
                result.status = HealthStatus.DEGRADED
            else:
                result.status = HealthStatus.UNHEALTHY

        except Exception as exc:
            result.latency_ms = (time.monotonic() - t0) * 1000
            result.error = str(exc)[:200]

        return result

    @property
    def results(self) -> Dict[str, ProviderHealthResult]:
        return dict(self._results)

    @property
    def stats(self) -> dict:
        return {
            "running": self._running,
            "interval": self.interval,
            "providers_checked": len(self._results),
            "healthy": sum(1 for r in self._results.values() if r.status == HealthStatus.HEALTHY),
            "degraded": sum(1 for r in self._results.values() if r.status == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for r in self._results.values() if r.status == HealthStatus.UNHEALTHY),
        }


# ── Singleton ────────────────────────────────────────────────

_monitor: Optional[HealthMonitor] = None


def get_monitor() -> Optional[HealthMonitor]:
    return _monitor


def set_monitor(m: HealthMonitor) -> None:
    global _monitor
    _monitor = m


# ══════════════════════════════════════════════════════════════
# v10.4 Predictive Health & SLA Monitoring
# ══════════════════════════════════════════════════════════════

class SLATracker:
    """Track service-level agreement compliance."""

    def __init__(self, target_uptime: float = 0.999, target_latency_ms: float = 2000) -> None:
        self.target_uptime = target_uptime
        self.target_latency = target_latency_ms
        self._total_checks = 0
        self._successful_checks = 0
        self._latencies: list[float] = []
        self._violations: list[dict] = []

    def record_check(self, success: bool, latency_ms: float, provider: str = "") -> Any:
        import time as _time
        self._total_checks += 1
        if success:
            self._successful_checks += 1
        self._latencies.append(latency_ms)
        if len(self._latencies) > 10000:
            self._latencies = self._latencies[-5000:]

        if not success or latency_ms > self.target_latency:
            self._violations.append({
                "time": _time.time(),
                "success": success,
                "latency_ms": latency_ms,
                "provider": provider,
            })
            if len(self._violations) > 1000:
                self._violations = self._violations[-500:]

    @property
    def uptime(self) -> float:
        if self._total_checks == 0:
            return 1.0
        return self._successful_checks / self._total_checks

    @property
    def avg_latency(self) -> float:
        if not self._latencies:
            return 0.0
        return sum(self._latencies) / len(self._latencies)

    @property
    def p95_latency(self) -> float:
        if not self._latencies:
            return 0.0
        s = sorted(self._latencies)
        idx = int(len(s) * 0.95)
        return s[min(idx, len(s) - 1)]

    @property
    def sla_compliant(self) -> bool:
        return self.uptime >= self.target_uptime and self.avg_latency <= self.target_latency

    def report(self) -> dict:
        return {
            "uptime": f"{self.uptime * 100:.3f}%",
            "target_uptime": f"{self.target_uptime * 100:.3f}%",
            "avg_latency_ms": round(self.avg_latency, 1),
            "p95_latency_ms": round(self.p95_latency, 1),
            "target_latency_ms": self.target_latency,
            "sla_compliant": self.sla_compliant,
            "total_checks": self._total_checks,
            "violations": len(self._violations),
        }


class PredictiveHealth:
    """Predict future health issues based on trends."""

    def __init__(self, window: int = 50) -> None:
        self._window = window
        self._scores: list[float] = []

    def add_score(self, score: float) -> None:
        self._scores.append(score)
        if len(self._scores) > self._window * 2:
            self._scores = self._scores[-self._window:]

    def trend(self) -> str:
        """Analyze health trend: improving, degrading, stable."""
        if len(self._scores) < 5:
            return "insufficient_data"
        recent = self._scores[-5:]
        older = self._scores[-min(len(self._scores), 10):-5] or self._scores[:5]
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        diff = avg_recent - avg_older
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "degrading"
        return "stable"

    def predict_failure(self) -> dict:
        """Predict if a failure is likely soon."""
        if len(self._scores) < 10:
            return {"risk": "unknown", "confidence": 0.0}
        recent = self._scores[-10:]
        avg = sum(recent) / len(recent)
        declining = all(recent[i] <= recent[i - 1] for i in range(1, len(recent)))
        if avg < 0.5 or declining:
            return {"risk": "high", "confidence": 0.8, "suggestion": "preemptive_failover"}
        if avg < 0.7:
            return {"risk": "medium", "confidence": 0.6, "suggestion": "monitor_closely"}
        return {"risk": "low", "confidence": 0.9, "suggestion": "normal_operation"}


