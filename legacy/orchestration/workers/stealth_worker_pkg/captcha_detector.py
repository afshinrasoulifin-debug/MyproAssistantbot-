
"""
stealth_worker_pkg/captcha_detector.py — CaptchaDetector
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CaptchaDetector:
    """Detects CAPTCHA/challenge type from page content."""

    # Patterns for detection
    CF_CHALLENGE_MARKERS: Final[List[str]] = [
        "cf-challenge-running", "cf-turnstile", "challenge-platform",
        "cf-chl-widget", "cf_chl_opt", "jschl_vc", "jschl_answer",
    ]
    RECAPTCHA_MARKERS: Final[List[str]] = [
        "g-recaptcha", "recaptcha/api", "grecaptcha",
    ]
    HCAPTCHA_MARKERS: Final[List[str]] = [
        "h-captcha", "hcaptcha.com",
    ]
    TURNSTILE_MARKERS: Final[List[str]] = [
        "cf-turnstile", "challenges.cloudflare.com/turnstile",
    ]

    @classmethod
    async def detect(cls, page) -> Optional[CaptchaType]:
        """Detect CAPTCHA type on the current page."""
        if not PLAYWRIGHT_AVAILABLE:
            return None
        try:
            html = await page.content()
            url = page.url

            # Cloudflare challenge page
            if any(m in html for m in cls.CF_CHALLENGE_MARKERS):
                if any(m in html for m in cls.TURNSTILE_MARKERS):
                    return CaptchaType.CLOUDFLARE_TURNSTILE
                return CaptchaType.CLOUDFLARE_CHALLENGE

            # reCAPTCHA
            if any(m in html for m in cls.RECAPTCHA_MARKERS):
                if "recaptcha/api.js?render=" in html:
                    return CaptchaType.RECAPTCHA_V3
                return CaptchaType.RECAPTCHA_V2

            # hCaptcha
            if any(m in html for m in cls.HCAPTCHA_MARKERS):
                return CaptchaType.HCAPTCHA

            return None
        except Exception:
            return None




