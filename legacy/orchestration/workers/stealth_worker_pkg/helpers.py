
"""
stealth_worker_pkg/helpers.py — standalone functions
Arki Engine v29.0.0
"""
from ._base import *  # noqa

async def _simulate_browsing_behavior(page, duration_seconds: float = 5.0) -> None:
    """Simulate human-like browsing behavior on a page."""
    if not PLAYWRIGHT_AVAILABLE:
        return

    start = time.time()
    while (time.time() - start) < duration_seconds:
        action = random.choice(["scroll", "move", "idle"])
        try:
            if action == "scroll":
                delta = random.randint(-300, 300)
                await page.mouse.wheel(0, delta)
                await asyncio.sleep(random.uniform(0.3, 0.8))

            elif action == "move":
                vp = page.viewport_size or {"width": 1920, "height": 1080}
                x = random.randint(100, vp["width"] - 100)
                y = random.randint(100, vp["height"] - 100)
                steps = random.randint(5, 20)
                await page.mouse.move(x, y, steps=steps)
                await asyncio.sleep(random.uniform(0.2, 0.5))

            else:  # idle
                await asyncio.sleep(random.uniform(0.5, 1.5))

        except Exception:
            await asyncio.sleep(0.5)


# ═══════════════════════════════════════════════════════════
# Stealth Worker Engine
# ═══════════════════════════════════════════════════════════



