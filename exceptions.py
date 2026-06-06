
"""
exceptions.py — Arki Engine Exception Taxonomy
===============================================
Structured exception hierarchy for enterprise-grade error handling.
All domain-specific exceptions inherit from ArkiBaseError.

Usage:
    from arki_project.exceptions import (
        ProviderTimeoutError, ProxyFailureError, BrowserFingerprintError,
        AIModelError, RateLimitExceededError, ...
    )
"""

from __future__ import annotations

__all__ = [
    # Base
    "ArkiBaseError",
    "ArkiConfigError",
    "ArkiStartupError",
    # AI / Model
    "AIError",
    "AIModelError",
    "AIModelNotFoundError",
    "AIProviderError",
    "ProviderTimeoutError",
    "ProviderConnectionError",
    "ProviderRateLimitError",
    "ProviderOverloadedError",
    "ProviderAuthError",
    "ModelFallbackExhaustedError",
    "TokenLimitExceededError",
    "EmptyPromptError",
    "HallucinationDetectedError",
    "AIResponseValidationError",
    # Network / Proxy / Stealth
    "NetworkError",
    "ProxyError",
    "ProxyFailureError",
    "ProxyPoolExhaustedError",
    "ProxyRotationError",
    "BrowserFingerprintError",
    "CaptchaError",
    "CaptchaUnsolvableError",
    "WAFBlockedError",
    "TLSFingerprintError",
    "AntiDetectionError",
    "StealthError",
    "EvasionFailureError",
    "GeoConsistencyError",
    # Circuit Breaker / Resilience
    "ResilienceError",
    "CircuitOpenError",
    "BulkheadFullError",
    "RetryBudgetExhaustedError",
    "RateLimitExceededError",
    "BackpressureError",
    "DegradationError",
    # Database / Storage
    "StorageError",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseMigrationError",
    "CacheError",
    "CacheMissError",
    "VectorStoreError",
    # Pipeline / Orchestration
    "PipelineError",
    "PipelineStageError",
    "PipelineTimeoutError",
    "OrchestrationError",
    "WorkflowError",
    "WorkflowStepError",
    "TaskQueueError",
    "TaskTimeoutError",
    "SchedulerError",
    # Agent / Execution
    "AgentError",
    "AgentExecutionError",
    "AgentPlanError",
    "AgentToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "CodeExecutionError",
    "SandboxError",
    # Handler / Bot
    "HandlerError",
    "CommandError",
    "CommandNotFoundError",
    "InvalidCommandArgsError",
    "CallbackError",
    "CallbackExpiredError",
    "MessageDeliveryError",
    "MediaProcessingError",
    # Marketing / Sales
    "MarketingError",
    "CampaignError",
    "CampaignCreationError",
    "CampaignExecutionError",
    "LeadScoringError",
    "OutreachError",
    "SEOError",
    "ContentGenerationError",
    # Platform / Integration
    "PlatformError",
    "PlatformConnectionError",
    "PlatformPublishError",
    "PlatformRateLimitError",
    "IntegrationError",
    "WebhookError",
    "APIGatewayError",
    # Security / Auth
    "SecurityError",
    "AuthenticationError",
    "AuthorizationError",
    "RBACError",
    "PermissionDeniedError",
    "EncryptionError",
    "KMSError",
    "GDPRError",
    "PoisonPillError",
    # Plugin / Module
    "PluginError",
    "PluginLoadError",
    "PluginExecutionError",
    "ModuleBridgeError",
    # Observability
    "ObservabilityError",
    "TracingError",
    "MetricsError",
]


# ─── Base ───────────────────────────────────────────────────────

class ArkiBaseError(Exception):
    """Root exception for all Arki Engine errors."""

    def __init__(self, message: str = "", *, code: str | None = None,
                 details: dict | None = None, cause: Exception | None = None):
        self.code = code
        self.details = details or {}
        if cause:
            self.details["cause"] = str(cause)
        super().__init__(message)


class ArkiConfigError(ArkiBaseError):
    """Configuration error (missing env var, invalid setting)."""


class ArkiStartupError(ArkiBaseError):
    """Bot failed to start (missing dependencies, DB init failure)."""


# ─── AI / Model ─────────────────────────────────────────────────

class AIError(ArkiBaseError):
    """Base for all AI-related errors."""


class AIModelError(AIError):
    """Generic AI model error."""


class AIModelNotFoundError(AIError):
    """Requested model not found in registry."""


class AIProviderError(AIError):
    """Base for provider-level errors."""

    def __init__(self, message: str = "", *, provider: str = "unknown", **kw):
        self.provider = provider
        super().__init__(message, **kw)


class ProviderTimeoutError(AIProviderError):
    """AI provider did not respond within the deadline."""


class ProviderConnectionError(AIProviderError):
    """Could not connect to AI provider."""


class ProviderRateLimitError(AIProviderError):
    """AI provider returned 429 / rate limit."""


class ProviderOverloadedError(AIProviderError):
    """AI provider returned 529 / overloaded."""


class ProviderAuthError(AIProviderError):
    """Invalid API key or auth failure for provider."""


class ModelFallbackExhaustedError(AIError):
    """All fallback models/providers failed."""


class TokenLimitExceededError(AIError):
    """Prompt or response exceeded token limit."""


class EmptyPromptError(AIError):
    """Empty or whitespace-only prompt submitted."""


class HallucinationDetectedError(AIError):
    """AI response flagged by hallucination detector."""


class AIResponseValidationError(AIError):
    """AI response did not pass output validation."""


# ─── Network / Proxy / Stealth ──────────────────────────────────

class NetworkError(ArkiBaseError):
    """Base for network-level errors."""


class ProxyError(NetworkError):
    """Base for proxy-related errors."""


class ProxyFailureError(ProxyError):
    """Proxy connection or authentication failed."""


class ProxyPoolExhaustedError(ProxyError):
    """No healthy proxies remaining in pool."""


class ProxyRotationError(ProxyError):
    """Proxy rotation strategy failed."""


class BrowserFingerprintError(NetworkError):
    """Browser fingerprint validation or generation failed."""


class CaptchaError(NetworkError):
    """Base for CAPTCHA errors."""


class CaptchaUnsolvableError(CaptchaError):
    """CAPTCHA could not be solved after max attempts."""


class WAFBlockedError(NetworkError):
    """Web Application Firewall blocked the request."""


class TLSFingerprintError(NetworkError):
    """TLS fingerprint mismatch or JA3 spoofing failure."""


class AntiDetectionError(NetworkError):
    """Anti-detection system general failure."""


class StealthError(NetworkError):
    """Stealth operation (header rotation, timing, etc.) failed."""


class EvasionFailureError(StealthError):
    """Evasion script execution failed."""


class GeoConsistencyError(StealthError):
    """Geographic consistency check failed (IP ≠ timezone, etc.)."""


# ─── Circuit Breaker / Resilience ────────────────────────────────

class ResilienceError(ArkiBaseError):
    """Base for resilience-pattern errors."""


class CircuitOpenError(ResilienceError):
    """Circuit breaker is open; request rejected."""


class BulkheadFullError(ResilienceError):
    """Bulkhead concurrency limit reached."""


class RetryBudgetExhaustedError(ResilienceError):
    """Retry budget (token bucket) exhausted."""


class RateLimitExceededError(ResilienceError):
    """Rate limit exceeded for user/endpoint."""


class BackpressureError(ResilienceError):
    """Back-pressure threshold reached; shedding load."""


class DegradationError(ResilienceError):
    """Graceful degradation activated."""


# ─── Database / Storage ──────────────────────────────────────────

class StorageError(ArkiBaseError):
    """Base for storage errors."""


class DatabaseError(StorageError):
    """Database operation failed."""


class DatabaseConnectionError(DatabaseError):
    """Could not connect to database."""


class DatabaseMigrationError(DatabaseError):
    """Migration or schema issue."""


class CacheError(StorageError):
    """Cache operation failed."""


class CacheMissError(CacheError):
    """Expected cache key not found."""


class VectorStoreError(StorageError):
    """Vector store (embeddings) operation failed."""


# ─── Pipeline / Orchestration ────────────────────────────────────

class PipelineError(ArkiBaseError):
    """Base for pipeline errors."""


class PipelineStageError(PipelineError):
    """A specific pipeline stage failed."""

    def __init__(self, message: str = "", *, stage: str = "", **kw):
        self.stage = stage
        super().__init__(message, **kw)


class PipelineTimeoutError(PipelineError):
    """Pipeline did not complete within deadline."""


class OrchestrationError(ArkiBaseError):
    """Base for orchestration errors."""


class WorkflowError(OrchestrationError):
    """Workflow execution error."""


class WorkflowStepError(WorkflowError):
    """A specific workflow step failed."""


class TaskQueueError(OrchestrationError):
    """Task queue operation failed."""


class TaskTimeoutError(TaskQueueError):
    """Queued task timed out."""


class SchedulerError(OrchestrationError):
    """Scheduler error."""


# ─── Agent / Execution ───────────────────────────────────────────

class AgentError(ArkiBaseError):
    """Base for agent errors."""


class AgentExecutionError(AgentError):
    """Agent execution failed."""


class AgentPlanError(AgentError):
    """Agent planning/reasoning failed."""


class AgentToolError(AgentError):
    """Agent tool invocation error."""


class ToolNotFoundError(AgentToolError):
    """Requested tool not registered."""


class ToolExecutionError(AgentToolError):
    """Tool execution returned error."""


class CodeExecutionError(AgentError):
    """Code interpreter / sandbox execution failed."""


class SandboxError(CodeExecutionError):
    """Sandbox security violation."""


# ─── Handler / Bot ────────────────────────────────────────────────

class HandlerError(ArkiBaseError):
    """Base for handler errors."""


class CommandError(HandlerError):
    """Command processing error."""


class CommandNotFoundError(CommandError):
    """Unknown command."""


class InvalidCommandArgsError(CommandError):
    """Invalid arguments to command."""


class CallbackError(HandlerError):
    """Callback query processing error."""


class CallbackExpiredError(CallbackError):
    """Callback data expired or invalid."""


class MessageDeliveryError(HandlerError):
    """Could not deliver message to user."""


class MediaProcessingError(HandlerError):
    """Media (image/voice/file) processing failed."""


# ─── Marketing / Sales ────────────────────────────────────────────

class MarketingError(ArkiBaseError):
    """Base for marketing errors."""


class CampaignError(MarketingError):
    """Campaign operation error."""


class CampaignCreationError(CampaignError):
    """Campaign creation failed."""


class CampaignExecutionError(CampaignError):
    """Campaign execution/scheduling failed."""


class LeadScoringError(MarketingError):
    """Lead scoring computation failed."""


class OutreachError(MarketingError):
    """Outreach operation failed."""


class SEOError(MarketingError):
    """SEO analysis/optimization error."""


class ContentGenerationError(MarketingError):
    """Content generation (poster, text, etc.) failed."""


# ─── Platform / Integration ──────────────────────────────────────

class PlatformError(ArkiBaseError):
    """Base for platform errors."""


class PlatformConnectionError(PlatformError):
    """Could not connect to external platform."""


class PlatformPublishError(PlatformError):
    """Content publishing to platform failed."""


class PlatformRateLimitError(PlatformError):
    """Platform-specific rate limit."""


class IntegrationError(ArkiBaseError):
    """External integration error."""


class WebhookError(IntegrationError):
    """Webhook delivery or processing failed."""


class APIGatewayError(IntegrationError):
    """API gateway error."""


# ─── Security / Auth ──────────────────────────────────────────────

class SecurityError(ArkiBaseError):
    """Base for security errors."""


class AuthenticationError(SecurityError):
    """Authentication failed."""


class AuthorizationError(SecurityError):
    """Authorization / permission check failed."""


class RBACError(AuthorizationError):
    """Role-based access control violation."""


class PermissionDeniedError(AuthorizationError):
    """User lacks required permission."""


class EncryptionError(SecurityError):
    """Encryption/decryption failed."""


class KMSError(SecurityError):
    """Key Management Service error."""


class GDPRError(SecurityError):
    """GDPR compliance violation."""


class PoisonPillError(SecurityError):
    """Malicious input detected."""


# ─── Plugin / Module ──────────────────────────────────────────────

class PluginError(ArkiBaseError):
    """Base for plugin errors."""


class PluginLoadError(PluginError):
    """Plugin failed to load."""


class PluginExecutionError(PluginError):
    """Plugin execution failed."""


class ModuleBridgeError(ArkiBaseError):
    """Module bridge connection/communication failed."""


# ─── Observability ────────────────────────────────────────────────

class ObservabilityError(ArkiBaseError):
    """Observability subsystem error."""


class TracingError(ObservabilityError):
    """Tracing export or propagation failed."""


class MetricsError(ObservabilityError):
    """Metrics collection or export failed."""


