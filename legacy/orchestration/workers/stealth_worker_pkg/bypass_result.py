
"""
stealth_worker_pkg/bypass_result.py — BypassResult
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class BypassResult(Enum):
    """Outcome of a bypass attempt."""
    SUCCESS = "success"
    CAPTCHA_DETECTED = "captcha_detected"
    CLOUDFLARE_BLOCKED = "cloudflare_blocked"
    TIMEOUT = "timeout"
    BROWSER_ERROR = "browser_error"
    NETWORK_ERROR = "network_error"
    RETRY_NEEDED = "retry_needed"




