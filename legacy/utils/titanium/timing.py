
from __future__ import annotations
"""
tg_bot/utils/titanium/timing.py — Gaussian Timing & Normalization v10.3.1
═══════════════════════════════════════════════════════════════════
Human-like timing distributions for anti-detection.

Ported from: TITANIUM ZKI utils/timing.ts
"""


import asyncio
import math
import time
from arki_project.utils.titanium.crypto import csprng_float


def _box_muller_gaussian(mean: float = 0.0, std: float = 1.0) -> float:
    """
    Box-Muller transform with rejection sampling.

    Unlike random.gauss() which uses Mersenne Twister,
    this uses CSPRNG (os.urandom) for unpredictable timing.

    Rejection sampling (up to 20 attempts) avoids boundary spikes
    when u1 ≈ 0 → log(u1) → -∞.
    """
    for _ in range(20):
        u1 = csprng_float()
        u2 = csprng_float()
        if u1 > 1e-10:  # avoid log(0) boundary spike
            z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
            return mean + std * z
    # Fallback: uniform approximation
    return mean


def gaussian_delay(mean_ms: float = 300.0, std_ms: float = 100.0,
                   min_ms: float = 50.0, max_ms: float = 1500.0) -> float:
    """
    Generate a Gaussian-distributed delay in milliseconds.

    Clamped to [min_ms, max_ms] for safety.
    Returns float milliseconds.
    """
    delay = _box_muller_gaussian(mean_ms, std_ms)
    return max(min_ms, min(max_ms, delay))


async def sleep_gaussian(mean_ms: float = 300.0, std_ms: float = 100.0,
                         min_ms: float = 50.0, max_ms: float = 1500.0) -> float:
    """Sleep for a Gaussian-distributed duration. Returns actual ms slept."""
    delay_ms = gaussian_delay(mean_ms, std_ms, min_ms, max_ms)
    await asyncio.sleep(delay_ms / 1000.0)
    return delay_ms


def normalize_time(target_ms: float = 2000.0, std_ms: float = 300.0) -> float:
    """
    Generate a normalized response time.

    For error responses, use this to mask the actual processing time
    so attackers can't distinguish errors from successes by timing.
    """
    return gaussian_delay(target_ms, std_ms, target_ms * 0.4, target_ms * 1.6)


class TimingNormalizer:
    """
    Ensures consistent response timing regardless of actual work duration.

    Usage:
        tn = TimingNormalizer(target_ms=2000)
        tn.start()
        ... do work ...
        await tn.wait()  # pads remaining time with Gaussian noise
    """

    def __init__(self, target_ms: float = 2000.0, std_ms: float = 300.0) -> None:
        self.target_ms = target_ms
        self.std_ms = std_ms
        self._start: float = 0.0

    def start(self) -> "TimingNormalizer":
        self._start = time.monotonic()
        return self

    async def wait(self) -> float:
        """Wait until the normalized target time. Returns total ms elapsed."""
        if self._start == 0:
            self.start()

        elapsed_ms = (time.monotonic() - self._start) * 1000
        target = normalize_time(self.target_ms, self.std_ms)
        remaining = target - elapsed_ms

        if remaining > 10:
            await asyncio.sleep(remaining / 1000.0)

        return (time.monotonic() - self._start) * 1000


