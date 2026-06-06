"""All Arki Engine exceptions — single source of truth."""

class ArkiBaseError(Exception):
    pass

class AIProviderError(ArkiBaseError): pass
class APIGatewayError(ArkiBaseError): pass
class AgentExecutionError(ArkiBaseError): pass
class CacheError(ArkiBaseError): pass
class CallbackError(ArkiBaseError): pass
class CampaignError(ArkiBaseError): pass
class CaptchaError(ArkiBaseError): pass
class DatabaseError(ArkiBaseError): pass
class HandlerError(ArkiBaseError): pass
class MarketingError(ArkiBaseError): pass
class NetworkError(ArkiBaseError): pass
class ObservabilityError(ArkiBaseError): pass
class OrchestrationError(ArkiBaseError): pass
class PipelineError(ArkiBaseError): pass
class PlatformError(ArkiBaseError): pass
class PluginError(ArkiBaseError): pass
class ProviderAuthError(AIProviderError): pass
class ProxyFailureError(ArkiBaseError): pass
class RateLimitExceededError(ArkiBaseError): pass
class ResilienceError(ArkiBaseError): pass
class SecurityError(ArkiBaseError): pass
class StealthError(ArkiBaseError): pass
class StorageError(ArkiBaseError): pass
class WorkflowError(ArkiBaseError): pass
class ConfigError(ArkiBaseError): pass
