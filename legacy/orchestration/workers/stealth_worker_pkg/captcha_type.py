
"""
stealth_worker_pkg/captcha_type.py — CaptchaType
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CaptchaType(Enum):
    """Detected CAPTCHA types."""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE_TURNSTILE = "turnstile"
    CLOUDFLARE_CHALLENGE = "cf_challenge"
    FUNCAPTCHA = "funcaptcha"
    UNKNOWN = "unknown"




