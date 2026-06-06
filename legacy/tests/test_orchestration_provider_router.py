

import pytest
from unittest.mock import patch

from arki_project.orchestration.provider_router import ProviderRouter, ProviderCapability, ProviderStatus
from arki_project.orchestration.types import InferenceRequest, ProviderName, RequestPriority

@pytest.mark.asyncio
class TestOrchestrationProviderRouter:

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # Mock MODELS registry as ProviderRouter depends on it
        with patch("arki_project.orchestration.provider_router.MODELS", new={}) as mock_models_registry:
            self.mock_models_registry = mock_models_registry
            yield

    async def test_provider_router_routes_by_capability(self):
        """C11: provider با capability VISION register، request با نیاز VISION، assert همان provider انتخاب شود."""
        router = ProviderRouter()

        # Register a provider with VISION capability
        vision_provider_cap = ProviderCapability(
            provider_name=ProviderName.GEMINI,
            model_id="gemini-vision",
            capabilities=["vision"],
            priority=RequestPriority.NORMAL
        )
        router.register_provider("vision_endpoint", vision_provider_cap)

        # Register a general text provider
        text_provider_cap = ProviderCapability(
            provider_name=ProviderName.GROQ,
            model_id="llama3-8b-8192",
            capabilities=["text"],
            priority=RequestPriority.NORMAL
        )
        router.register_provider("text_endpoint", text_provider_cap)

        # Create an InferenceRequest with VISION task_type
        request = InferenceRequest(prompt="Analyze image", user_id=1, model_key="gemini-vision", task_type="vision")

        selected_provider, selected_model = router.route(request)

        assert selected_provider == ProviderName.GEMINI
        assert selected_model == "gemini-vision"

    async def test_provider_router_fallback_on_missing_capability(self):
        """C12: هیچ provider دقیقاً match نشود، assert به general provider برود."""
        router = ProviderRouter()

        # Register a general text provider
        general_provider_cap = ProviderCapability(
            provider_name=ProviderName.GEMINI,
            model_id="gemini-pro",
            capabilities=["text"],
            priority=RequestPriority.NORMAL
        )
        router.register_provider("general_endpoint", general_provider_cap)

        # Register a specific vision provider
        vision_provider_cap = ProviderCapability(
            provider_name=ProviderName.GROQ,
            model_id="llama3-8b-8192-vision",
            capabilities=["vision"],
            priority=RequestPriority.NORMAL
        )
        router.register_provider("vision_endpoint", vision_provider_cap)

        # Request for a capability that no provider explicitly matches (e.g., 'audio')
        # The router should fall back to a general provider if no specific match is found.
        # The current implementation's _fallback_decision picks the first model from providers in fallback order.
        # So, if no specific match, it should pick the highest priority general provider.
        request = InferenceRequest(prompt="Generate audio", user_id=2, model_key="unknown-audio-model", task_type="audio")

        selected_provider, selected_model = router.route(request)

        assert selected_provider == ProviderName.GEMINI # Expecting fallback to general provider
        assert selected_model == "gemini-pro"

    async def test_provider_router_status_update(self):
        """C13: status provider را DOWN کن، assert از routing حذف شود."""
        router = ProviderRouter()

        # Register a healthy provider
        healthy_provider_cap = ProviderCapability(
            provider_name=ProviderName.GEMINI,
            model_id="gemini-pro",
            capabilities=["text"],
            priority=RequestPriority.NORMAL
        )
        router.register_provider("healthy_endpoint", healthy_provider_cap)

        # Register a provider that will be marked DOWN
        down_provider_cap = ProviderCapability(
            provider_name=ProviderName.GROQ,
            model_id="llama3-8b-8192",
            capabilities=["text"],
            priority=RequestPriority.HIGH
        )
        router.register_provider("down_endpoint", down_provider_cap)

        # Update the status of 'down_endpoint' to DOWN
        router.update_provider_status("down_endpoint", ProviderStatus.DOWN)

        # Request a text model. The DOWN provider should not be selected.
        request = InferenceRequest(prompt="Hello", user_id=3, model_key="any-text-model", task_type="text")

        selected_provider, selected_model = router.route(request)

        assert selected_provider == ProviderName.GEMINI # Expecting healthy provider to be chosen
        assert selected_model == "gemini-pro"

    async def test_provider_router_priority_ordering(self):
        """C14: چند provider با priority مختلف، assert بالاترین priority اول انتخاب شود."""
        router = ProviderRouter()

        # Register providers with different priorities
        low_priority_cap = ProviderCapability(
            provider_name=ProviderName.GROQ,
            model_id="llama3-8b-8192",
            capabilities=["text"],
            priority=RequestPriority.LOW
        )
        router.register_provider("low_priority_endpoint", low_priority_cap)

        high_priority_cap = ProviderCapability(
            provider_name=ProviderName.GEMINI,
            model_id="gemini-pro",
            capabilities=["text"],
            priority=RequestPriority.HIGH
        )
        router.register_provider("high_priority_endpoint", high_priority_cap)

        normal_priority_cap = ProviderCapability(
            provider_name=ProviderName.OPENROUTER,
            model_id="openrouter-model",
            capabilities=["text"],
            priority=RequestPriority.NORMAL
        )
        router.register_provider("normal_priority_endpoint", normal_priority_cap)

        # Request a text model. The highest priority provider should be chosen.
        request = InferenceRequest(prompt="Prioritize this", user_id=4, model_key="any-text-model", task_type="text")

        selected_provider, selected_model = router.route(request)

        assert selected_provider == ProviderName.GEMINI # Expecting high priority provider
        assert selected_model == "gemini-pro"



