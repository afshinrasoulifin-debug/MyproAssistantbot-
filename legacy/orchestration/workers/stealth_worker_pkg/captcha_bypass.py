
"""
stealth_worker_pkg/captcha_bypass.py — CaptchaBypass
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CaptchaBypass:
    """
    Multi-solver CAPTCHA bypass router.

    Supports:
    - Cloudflare Turnstile (wait + click)
    - reCAPTCHA v2 (audio challenge or external solver API)
    - reCAPTCHA v3 (score manipulation via behavioral simulation)
    - hCaptcha (external solver API)

    External solver integration points:
    - 2captcha API
    - Anti-Captcha API
    - CapMonster Cloud
    """

    # External solver config (set via environment)
    SOLVER_API_KEY: Final[str] = os.environ.get("CAPTCHA_SOLVER_API_KEY", "")
    SOLVER_SERVICE: Final[str] = os.environ.get("CAPTCHA_SOLVER_SERVICE", "2captcha")

    @classmethod
    async def solve(cls, page, captcha_type: CaptchaType) -> BypassResult:
        """Route to the appropriate solver."""
        solvers = {
            CaptchaType.CLOUDFLARE_TURNSTILE: cls._solve_turnstile,
            CaptchaType.CLOUDFLARE_CHALLENGE: cls._solve_cf_challenge,
            CaptchaType.RECAPTCHA_V2: cls._solve_recaptcha_v2,
            CaptchaType.RECAPTCHA_V3: cls._solve_recaptcha_v3,
            CaptchaType.HCAPTCHA: cls._solve_hcaptcha,
        }

        solver = solvers.get(captcha_type, cls._solve_generic)
        return await solver(page)

    @classmethod
    async def _solve_turnstile(cls, page) -> BypassResult:
        """Solve Cloudflare Turnstile — mostly behavioral."""
        return await CloudflareBypass.attempt_bypass(page, StealthConfig())

    @classmethod
    async def _solve_cf_challenge(cls, page) -> BypassResult:
        """Solve generic Cloudflare challenge — JS wait."""
        return await CloudflareBypass.attempt_bypass(page, StealthConfig())

    @classmethod
    async def _solve_recaptcha_v2(cls, page) -> BypassResult:
        """Attempt reCAPTCHA v2 solve via external service or audio."""
        if cls.SOLVER_API_KEY:
            return await cls._external_solve(page, "recaptcha_v2")
        # Fallback: try audio challenge
        logger.info("🔊 Attempting reCAPTCHA v2 audio challenge...")
        try:
            # Find recaptcha iframe
            frames = page.frames
            for frame in frames:
                if "recaptcha" in (frame.url or ""):
                    audio_btn = await frame.query_selector("#recaptcha-audio-button")
                    if audio_btn:
                        await audio_btn.click()
                        await asyncio.sleep(random.uniform(2, 4))
                        # Audio solving would need speech-to-text
                        logger.info("Audio challenge opened — needs external solver")
                        return BypassResult.CAPTCHA_DETECTED
        except Exception as e:
            logger.debug("reCAPTCHA v2 audio fallback: %s", e)
        return BypassResult.CAPTCHA_DETECTED

    @classmethod
    async def _solve_recaptcha_v3(cls, page) -> BypassResult:
        """reCAPTCHA v3 — high score via behavior simulation."""
        logger.info("🤖 reCAPTCHA v3 — simulating human behavior for high score")
        try:
            # v3 is score-based — simulate natural browsing
            await _simulate_browsing_behavior(page, duration_seconds=5)
            return BypassResult.SUCCESS
        except Exception:
            return BypassResult.CAPTCHA_DETECTED

    @classmethod
    async def _solve_hcaptcha(cls, page) -> BypassResult:
        """hCaptcha — needs external solver."""
        if cls.SOLVER_API_KEY:
            return await cls._external_solve(page, "hcaptcha")
        return BypassResult.CAPTCHA_DETECTED

    @classmethod
    async def _solve_generic(cls, page) -> BypassResult:
        """Generic unknown captcha — wait and hope."""
        await asyncio.sleep(random.uniform(5, 10))
        return BypassResult.RETRY_NEEDED

    @classmethod
    async def _external_solve(cls, page, captcha_kind: str) -> BypassResult:
        """Route to external solver API (2captcha, Anti-Captcha, CapMonster)."""
        logger.info("📡 Routing %s to external solver: %s", captcha_kind, cls.SOLVER_SERVICE)
        # Integration point — implement based on selected service
        # This requires the page's sitekey + page URL → API call → token → inject
        try:
            html = await page.content()

            # Extract sitekey
            sitekey_match = re.search(
                r'(?:data-sitekey|sitekey)["\s=:]+["\']?([a-zA-Z0-9_-]{20,})',
                html,
            )
            if not sitekey_match:
                logger.warning("Could not extract sitekey for %s", captcha_kind)
                return BypassResult.CAPTCHA_DETECTED

            sitekey = sitekey_match.group(1)
            page_url = page.url

            logger.info(
                "🔑 Extracted sitekey=%s... for %s at %s",
                sitekey[:12], captcha_kind, page_url,
            )

            # API call would go here:
            # result = await call_solver_api(service, sitekey, page_url)
            # await inject_token(page, result.token)

            return BypassResult.CAPTCHA_DETECTED  # Until solver configured

        except Exception as e:
            logger.error("External solver error: %s", e)
            return BypassResult.CAPTCHA_DETECTED


# ═══════════════════════════════════════════════════════════
# Human Behavior Simulation
# ═══════════════════════════════════════════════════════════



