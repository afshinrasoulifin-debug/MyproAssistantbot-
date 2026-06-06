

import pytest
from unittest.mock import patch, MagicMock

from arki_project.orchestration.load_balancer import LoadBalancer, Strategy
from arki_project.orchestration.types import ProviderName

@pytest.mark.asyncio
class TestOrchestrationLoadBalancer:

    async def test_load_balancer_round_robin(self):
        """C6: 3 node ثبت، 9 request ارسال، assert هر node دقیقاً 3 بار انتخاب شود."""
        balancer = LoadBalancer(strategy=Strategy.ROUND_ROBIN)
        nodes = ["node1", "node2", "node3"]
        for node in nodes:
            balancer.add_endpoint(node, ProviderName.GEMINI, "model_a")

        selections = {node: 0 for node in nodes}
        for _ in range(9):
            selected_node = balancer.pick(ProviderName.GEMINI, "model_a")
            assert selected_node is not None
            selections[selected_node] += 1

        assert selections["node1"] == 3
        assert selections["node2"] == 3
        assert selections["node3"] == 3

    async def test_load_balancer_weighted(self):
        """C7: weights [3,1,1]، 100 request، assert توزیع تقریباً 60%/20%/20%."""
        balancer = LoadBalancer(strategy=Strategy.WEIGHTED_RANDOM)
        balancer.add_endpoint("node_high", ProviderName.GEMINI, "model_b", weight=3)
        balancer.add_endpoint("node_med1", ProviderName.GEMINI, "model_b", weight=1)
        balancer.add_endpoint("node_med2", ProviderName.GEMINI, "model_b", weight=1)

        selections = {"node_high": 0, "node_med1": 0, "node_med2": 0}
        num_requests = 1000 # Increase requests for better statistical distribution

        # Mock csprng_weighted_choice if it's used, to ensure deterministic testing
        # The overview mentioned it uses arki_project.utils.titanium.crypto.csprng_weighted_choice
        # if available, otherwise random.choices. We should mock the former if it exists.
        with patch(
            "arki_project.orchestration.load_balancer.csprng_weighted_choice",
            side_effect=lambda population, weights, k: MagicMock(return_value=[
                population[0] if i % 5 < 3 else (population[1] if i % 5 == 3 else population[2])
                for i in range(k[0]) # k is a tuple (num_choices,) for random.choices
            ])
        ) as mock_weighted_choice:
            for i in range(num_requests):
                selected_node = balancer.pick(ProviderName.GEMINI, "model_b")
                assert selected_node is not None
                selections[selected_node] += 1

        # Assert approximate distribution (e.g., within 5% of expected)
        total_weight = 3 + 1 + 1
        expected_high = (3 / total_weight) * num_requests
        expected_med = (1 / total_weight) * num_requests

        assert abs(selections["node_high"] - expected_high) < num_requests * 0.1 # 10% tolerance
        assert abs(selections["node_med1"] - expected_med) < num_requests * 0.1
        assert abs(selections["node_med2"] - expected_med) < num_requests * 0.1

    async def test_load_balancer_removes_unhealthy_node(self):
        """C8: node را unhealthy mark کن، assert هیچ‌وقت انتخاب نشود."""
        balancer = LoadBalancer(strategy=Strategy.ROUND_ROBIN)
        balancer.add_endpoint("healthy_node", ProviderName.GEMINI, "model_c")
        balancer.add_endpoint("unhealthy_node", ProviderName.GEMINI, "model_c")

        # Simulate removing the unhealthy node
        balancer.remove_endpoint("unhealthy_node", ProviderName.GEMINI, "model_c")

        selections = {"healthy_node": 0, "unhealthy_node": 0}
        for _ in range(10):
            selected_node = balancer.pick(ProviderName.GEMINI, "model_c")
            assert selected_node == "healthy_node"
            selections[selected_node] += 1

        assert selections["healthy_node"] == 10
        assert selections["unhealthy_node"] == 0

    async def test_load_balancer_single_node_fallback(self):
        """C9: 2 node، یکی down، assert همه به node سالم برود."""
        balancer = LoadBalancer(strategy=Strategy.ROUND_ROBIN)
        balancer.add_endpoint("node_up", ProviderName.GEMINI, "model_d")
        balancer.add_endpoint("node_down", ProviderName.GEMINI, "model_d")

        # Simulate one node going down by removing it
        balancer.remove_endpoint("node_down", ProviderName.GEMINI, "model_d")

        selections = {"node_up": 0, "node_down": 0}
        for _ in range(10):
            selected_node = balancer.pick(ProviderName.GEMINI, "model_d")
            assert selected_node == "node_up"
            selections[selected_node] += 1

        assert selections["node_up"] == 10
        assert selections["node_down"] == 0

    async def test_load_balancer_empty_pool_returns_none(self):
        """C10: pool خالی، assert None برگردد (بر اساس بررسی کد واقعی)."""
        balancer = LoadBalancer(strategy=Strategy.ROUND_ROBIN)
        # No endpoints added, so the pool is empty

        selected_node = balancer.pick(ProviderName.GEMINI, "model_e")
        assert selected_node is None



