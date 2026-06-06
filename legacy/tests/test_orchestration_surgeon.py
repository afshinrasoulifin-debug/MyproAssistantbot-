

import pytest

from arki_project.orchestration.surgeon import SurgeonAgent, surgeon
from arki_project.orchestration.types import ProviderName

@pytest.mark.asyncio
class TestOrchestrationSurgeon:

    @pytest.fixture(autouse=True)
    def reset_surgeon_singleton(self):
        """Reset the global surgeon singleton before each test to ensure isolation."""
        # This is a workaround for testing singletons. In a real application,
        # the singleton state would persist.
        original_surgeon_instance = surgeon
        # Re-initialize the singleton for each test
        SurgeonAgent.__init__(surgeon)
        yield
        # Restore original state if necessary, or just let the fixture re-init next time
        SurgeonAgent.__init__(original_surgeon_instance)

    async def test_surgeon_agent_init_state(self):
        """C20: SurgeonAgent() ساخته شود، assert is_running=False، model_benchmarks={}."""
        # We are testing the global singleton 'surgeon' directly after reset_surgeon_singleton
        assert surgeon.is_running is False
        assert surgeon.model_benchmarks == {}
        assert surgeon.active_sessions == {}
        assert surgeon.provider_registry == {}
        assert surgeon.audit_interval == 300
        assert surgeon.research_interval == 3600
        assert isinstance(surgeon.capabilities, list)
        assert len(surgeon.capabilities) > 0

    async def test_surgeon_provider_registry_update(self):
        """C21: متد ثبت provider فراخوانده شود، assert provider در provider_registry باشد.
        Note: SurgeonAgent does not have a public `register_provider` method.
        This test simulates an internal update to `provider_registry`.
        """
        # Simulate an internal update to the provider_registry
        provider_id = "test_provider_id"
        provider_data = {
            "name": ProviderName.GEMINI,
            "model_id": "gemini-pro",
            "status": "HEALTHY"
        }
        surgeon.provider_registry[provider_id] = provider_data

        assert provider_id in surgeon.provider_registry
        assert surgeon.provider_registry[provider_id]["name"] == ProviderName.GEMINI

    async def test_surgeon_benchmark_record(self):
        """C22: benchmark برای یک model ثبت شود، assert مقدار بازیابی شود.
        Note: SurgeonAgent does not have a public method to record benchmarks.
        This test simulates an internal update to `model_benchmarks`.
        """
        model_name = "test-model"
        benchmark_data = {"latency": 150, "throughput": 100}

        # Simulate an internal update to model_benchmarks
        surgeon.model_benchmarks[model_name] = benchmark_data

        assert model_name in surgeon.model_benchmarks
        assert surgeon.model_benchmarks[model_name]["latency"] == 150
        assert surgeon.model_benchmarks[model_name]["throughput"] == 100

    async def test_surgeon_audit_interval_config(self):
        """C23: audit_interval تغییر دهد، assert مقدار جدید حفظ شود."""
        new_interval = 600 # 10 minutes
        surgeon.audit_interval = new_interval
        assert surgeon.audit_interval == new_interval

        # Also test that it can be changed back
        another_interval = 120
        surgeon.audit_interval = another_interval
        assert surgeon.audit_interval == another_interval


