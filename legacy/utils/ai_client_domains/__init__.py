
"""
utils/ai_client_domains/ — Domain-Driven AI Client Sub-modules
══════════════════════════════════════════════════════════════
Extracted from ai_client.py god-functions into focused domains:
- provider_calls: Individual provider API calls
- response_parser: Parse and validate AI responses  
- request_builder: Build request payloads
- retry_logic: Retry, fallback, circuit breaking
"""
from .provider_calls import GeminiProvider, GroqProvider, OpenRouterProvider
from .response_parser import parse_ai_response, validate_response
from .request_builder import build_request_payload
from .retry_logic import RetryManager, with_retry

__all__ = [
    "GeminiProvider", "GroqProvider", "OpenRouterProvider",
    "parse_ai_response", "validate_response",
    "build_request_payload", "RetryManager", "with_retry",
]


