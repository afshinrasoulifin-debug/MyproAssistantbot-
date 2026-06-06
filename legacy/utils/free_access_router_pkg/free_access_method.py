
"""
free_access_router_pkg/free_access_method.py — FreeAccessMethod
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class FreeAccessMethod(Enum):
    """How to access a model for free."""
    OPENROUTER_FREE = "openrouter_free"      # OpenRouter :free variant (NO KEY)
    OPENROUTER_NOKEY = "openrouter_nokey"     # OpenRouter natively free (NO KEY)
    GOOGLE_AISTUDIO = "google_aistudio"       # Google AI Studio free API
    GROQ_FREE = "groq_free"                   # Groq Cloud free tier
    HUGGINGFACE_FREE = "huggingface_free"     # HuggingFace Inference API
    TOGETHER_FREE = "together_free"           # Together.ai free tier
    CEREBRAS_FREE = "cerebras_free"           # Cerebras free inference
    DEEPINFRA_FREE = "deepinfra_free"         # DeepInfra free tier
    PROXY_ROTATE = "proxy_rotate"             # Rotate through multiple free proxies
    SMART_FALLBACK = "smart_fallback"         # Redirect to a free alternative model




