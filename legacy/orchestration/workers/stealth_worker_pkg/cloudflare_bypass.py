
"""
stealth_worker_pkg/cloudflare_bypass.py — CloudflareBypass
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class CloudflareBypass:
    """
    Specialized Cloudflare challenge bypass.

    Strategy pipeline:
    1. Wait for JS challenge auto-solve (5-15 seconds)
    2. Detect Turnstile widget and trigger click
    3. Cookie extraction after challenge pass
    4. Session persistence for future requests
    """

    MAX_WAIT_SECONDS: Final[int] = 30
    CHECK_INTERVAL: Final[float] = 1.0

    @classmethod
    async def attempt_bypass(cls, page, config: StealthConfig) -> BypassResult:
        """Attempt to bypass Cloudflare protection."""
        logger.info("☁️  Cloudflare challenge detected — initiating bypass pipeline")

        start = time.time()
        while (time.time() - start) < cls.MAX_WAIT_SECONDS:
            # Check if challenge is resolved
            try:
                html = await page.content()

                # JS challenge auto-completes
                if "cf-challenge-running" not in html and "jschl_vc" not in html:
                    if "cf-turnstile" not in html:
                        logger.info("✅ Cloudflare JS challenge auto-resolved in %.1fs",
                                    time.time() - start)
                        return BypassResult.SUCCESS

                # Try clicking Turnstile checkbox if present
                turnstile = await page.query_selector('input[type="checkbox"][name="cf-turnstile-response"]')
                if turnstile:
                    await cls._simulate_human_click(page, turnstile)
                    await asyncio.sleep(random.uniform(2.0, 4.0))

                # Check for iframe-based challenge
                frames = page.frames
                for frame in frames:
                    if "challenges.cloudflare.com" in (frame.url or ""):
                        checkbox = await frame.query_selector('input[type="checkbox"]')
                        if checkbox:
                            await cls._simulate_human_click_frame(frame, checkbox)
                            await asyncio.sleep(random.uniform(2.0, 4.0))

            except Exception as e:
                logger.debug("CF bypass check error: %s", e)

            await asyncio.sleep(cls.CHECK_INTERVAL)

        logger.warning("⏰ Cloudflare bypass timed out after %ds", cls.MAX_WAIT_SECONDS)
        return BypassResult.CLOUDFLARE_BLOCKED

    @classmethod
    async def _simulate_human_click(cls, page, element) -> None:
        """Click with human-like behavior."""
        try:
            box = await element.bounding_box()
            if box:
                x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
                y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
                await page.mouse.move(x, y, steps=random.randint(5, 15))
                await asyncio.sleep(random.uniform(0.1, 0.3))
                await page.mouse.click(x, y)
        except Exception as e:
            logger.debug("Human click failed: %s", e)
            try:
                await element.click()
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

    @classmethod
    async def _simulate_human_click_frame(cls, frame, element) -> None:
        """Click within an iframe."""
        try:
            await element.click()
        except Exception as _err:
            logger.warning("Suppressed error: %s", _err)




