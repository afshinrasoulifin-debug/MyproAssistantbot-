

import pytest
from arki_project.orchestration.observatory import Observatory, RequestMetric
from arki_project.orchestration.types import ProviderName

@pytest.mark.asyncio
class TestOrchestrationObservatory:

    @pytest.fixture(autouse=True)
    def observatory_instance(self):
        """Provide a fresh Observatory instance for each test."""
        obs = Observatory()
        yield obs
        obs.reset() # Clean up after each test

    async def test_observatory_record_metric(self, observatory_instance: Observatory):
        """C29: یک metric ثبت شود، assert بازیابی صحیح."""
        metric = RequestMetric(
            request_id="req1",
            provider=ProviderName.GEMINI,
            model_id="gemini-pro",
            latency_ms=150.5,
            success=True,
            tokens_in=100,
            tokens_out=50,
            cached=False
        )
        observatory_instance.record_request(metric)

        dashboard = observatory_instance.get_dashboard()
        assert dashboard["total_requests"] == 1
        assert dashboard["providers"][ProviderName.GEMINI]["requests"] == 1
        assert dashboard["models"]["gemini-pro"]["requests"] == 1
        assert dashboard["tokens"]["total_in"] == 100
        assert dashboard["tokens"]["total_out"] == 50

    async def test_observatory_health_snapshot(self, observatory_instance: Observatory):
        """C30: چند metric ثبت، get_health_snapshot() فراخوانده شود، assert ساختار dict."""
        # Record some successful requests
        for i in range(5):
            metric = RequestMetric(
                request_id=f"req_ok_{i}",
                provider=ProviderName.GEMINI,
                model_id="gemini-pro",
                latency_ms=100.0 + i,
                success=True
            )
            observatory_instance.record_request(metric)

        # Record some failed requests
        for i in range(2):
            metric = RequestMetric(
                request_id=f"req_fail_{i}",
                provider=ProviderName.GEMINI,
                model_id="gemini-pro",
                latency_ms=200.0 + i,
                success=False,
                error_type="ProviderError"
            )
            observatory_instance.record_request(metric)

        health_snapshot = observatory_instance.get_health_check()

        assert isinstance(health_snapshot, dict)
        assert "status" in health_snapshot
        assert "uptime" in health_snapshot
        assert "total_requests" in health_snapshot
        assert "error_rate" in health_snapshot
        assert "providers" in health_snapshot

        assert health_snapshot["total_requests"] == 7
        assert health_snapshot["providers"][ProviderName.GEMINI]["requests"] == 7
        assert health_snapshot["providers"][ProviderName.GEMINI]["errors"] == 2
        assert health_snapshot["error_rate"] == pytest.approx(2/7, rel=1e-2)

    async def test_observatory_metric_aggregation(self, observatory_instance: Observatory):
        """C31: 10 مقدار latency ثبت، assert avg/min/max صحیح."""
        latencies = [100.0, 110.0, 90.0, 120.0, 105.0, 95.0, 115.0, 102.0, 98.0, 107.0]
        for i, lat in enumerate(latencies):
            metric = RequestMetric(
                request_id=f"agg_req_{i}",
                provider=ProviderName.GROQ,
                model_id="llama3",
                latency_ms=lat,
                success=True
            )
            observatory_instance.record_request(metric)

        provider_stats = observatory_instance.get_provider_stats(ProviderName.GROQ)

        assert provider_stats["requests"] == 10
        assert provider_stats["avg_latency_ms"] == pytest.approx(sum(latencies) / len(latencies), rel=1e-2)
        assert provider_stats["p50_latency_ms"] == pytest.approx(sorted(latencies)[4], rel=1e-2) # Median
        assert provider_stats["p95_latency_ms"] == pytest.approx(sorted(latencies)[9], rel=1e-2) # 95th percentile

    async def test_observatory_threshold_alert(self, observatory_instance: Observatory):
        """C32: مقدار بالاتر از threshold، assert alert trigger شود.
        (Testing the internal _is_healthy heuristic via get_health_check status)"""
        # Record 10 successful requests
        for i in range(10):
            metric = RequestMetric(
                request_id=f"healthy_req_{i}",
                provider=ProviderName.GEMINI,
                model_id="gemini-pro",
                latency_ms=100.0,
                success=True
            )
            observatory_instance.record_request(metric)

        health_check_initial = observatory_instance.get_health_check()
        assert health_check_initial["status"] == "healthy"

        # Record enough failed requests to push error rate above 0.5 (50%)
        # We have 10 successful requests. To make error rate > 0.5, we need more than 10 failures.
        # E.g., 10 successes + 11 failures = 11/21 ~ 0.52 > 0.5
        for i in range(11):
            metric = RequestMetric(
                request_id=f"unhealthy_req_{i}",
                provider=ProviderName.GEMINI,
                model_id="gemini-pro",
                latency_ms=200.0,
                success=False,
                error_type="CriticalError"
            )
            observatory_instance.record_request(metric)

        health_check_final = observatory_instance.get_health_check()
        assert health_check_final["status"] == "degraded"
        assert health_check_final["error_rate"] == pytest.approx(11/21, rel=1e-2)



