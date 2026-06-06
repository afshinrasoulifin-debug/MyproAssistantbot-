
from __future__ import annotations
"""
utils/latency_cloaking.py — Human Kinetic Synthesis Engine
═══════════════════════════════════════════════════════════
Deep-jitter modeling using Poisson process distribution to mask
automated rhythmic signatures. Zero deterministic delay constants.

All timing comes from stochastic models of real human behavior:
- Page reading: Log-normal (most 3-8s, long tail for articles)
- Click intervals: Weibull (natural clustering)
- Typing: Gaussian per-keystroke with fatigue drift
- Scrolling: Poisson + burst detection
- Session activity: Circadian rhythm model
"""

import logging
import math
import random
from typing import Final, List, Optional

logger = logging.getLogger(__name__)

# ── Statistical model parameters (calibrated from real user studies) ──
_READING_MU: Final[float] = 1.6        # Log-normal μ for page reading (seconds)
_READING_SIGMA: Final[float] = 0.65     # Log-normal σ
_CLICK_SHAPE: Final[float] = 1.8        # Weibull shape for click intervals
_CLICK_SCALE: Final[float] = 2.5        # Weibull scale
_TYPE_MEAN_MS: Final[float] = 92.0      # Average typing speed (ms/key)
_TYPE_STD_MS: Final[float] = 28.0       # Typing speed std dev
_SCROLL_LAMBDA: Final[float] = 0.4      # Poisson λ for scroll events/second
_FATIGUE_RATE: Final[float] = 0.002     # Typing slows by this factor per keystroke


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class PoissonJitter:
    """Pure Poisson process with no deterministic component."""

    @staticmethod
    def delay(rate: float = 0.5) -> float:
        """Generate inter-event delay from Poisson process.

        rate: average events per second
        Returns: delay in seconds (exponentially distributed)
        """
        return -math.log(1.0 - random.random()) / max(0.01, rate)

    @staticmethod
    def batch_delays(n: int, rate: float = 0.5) -> List[float]:
        """Generate a batch of delays."""
        return [PoissonJitter.delay(rate) for _ in range(n)]


class ReadingTimeModel:
    """Log-normal reading time model."""

    @staticmethod
    def estimate(word_count: int = 0) -> float:
        """Estimate reading time with natural variation.

        If word_count given, uses WPM model. Otherwise pure stochastic.
        """
        if word_count > 0:
            # Average adult reads 200-300 WPM, log-normal variation
            wpm = random.lognormvariate(math.log(250), 0.2)
            base_time = (word_count / wpm) * 60  # seconds
            # Add scanning/comprehension jitter
            return base_time * random.uniform(0.6, 1.4)
        return random.lognormvariate(_READING_MU, _READING_SIGMA)

    @staticmethod
    def quick_scan() -> float:
        """Brief glance at content (1-3 seconds)."""
        return random.lognormvariate(0.5, 0.4)

    @staticmethod
    def deep_read() -> float:
        """Deep reading/analysis (10-60 seconds)."""
        return random.lognormvariate(3.0, 0.5)


class ClickTimingModel:
    """Weibull-distributed click intervals."""

    @staticmethod
    def delay() -> float:
        """Time between clicks (seconds)."""
        return random.weibullvariate(_CLICK_SCALE, _CLICK_SHAPE)

    @staticmethod
    def rapid_burst(n: int) -> List[float]:
        """Rapid click burst (like navigating a menu)."""
        return [random.uniform(0.1, 0.5) for _ in range(n)]

    @staticmethod
    def deliberate() -> float:
        """Deliberate click after thinking (form submission, etc)."""
        return random.uniform(1.5, 5.0) + random.expovariate(0.5)


class TypingModel:
    """Realistic keystroke timing with fatigue and error patterns."""

    def __init__(self) -> None:
        self._keystroke_count = 0
        self._base_speed = random.gauss(_TYPE_MEAN_MS, 10)  # Per-session calibration

    def keystroke_delay(self) -> float:
        """Get delay for next keystroke (milliseconds)."""
        self._keystroke_count += 1
        # Base Gaussian delay with fatigue drift
        fatigue = 1.0 + (_FATIGUE_RATE * self._keystroke_count)
        delay = random.gauss(self._base_speed * fatigue, _TYPE_STD_MS)

        # Occasional pauses (thinking)
        if random.random() < 0.03:
            delay += random.uniform(500, 2000)
        # Occasional burst (muscle memory for common words)
        elif random.random() < 0.05:
            delay *= 0.5

        return _clamp(delay, 20, 5000)

    def type_string(self, text: str) -> List[float]:
        """Generate realistic keystroke delays for a string."""
        delays = []
        for i, char in enumerate(text):
            d = self.keystroke_delay()
            # Slower on uppercase (Shift key)
            if char.isupper():
                d += random.uniform(20, 50)
            # Faster on space (common key)
            elif char == " ":
                d *= 0.8
            # Slower on special chars
            elif not char.isalnum():
                d += random.uniform(30, 80)
            delays.append(d)
        return delays

    def reset_session(self) -> None:
        self._keystroke_count = 0
        self._base_speed = random.gauss(_TYPE_MEAN_MS, 10)


class ScrollModel:
    """Poisson-driven scroll timing."""

    @staticmethod
    def scroll_delays(n_scrolls: int) -> List[float]:
        """Generate inter-scroll delays."""
        delays = []
        for _ in range(n_scrolls):
            if random.random() < 0.15:
                # Pause to read
                delays.append(ReadingTimeModel.estimate())
            else:
                delays.append(PoissonJitter.delay(_SCROLL_LAMBDA))
        return delays

    @staticmethod
    def scroll_amount() -> int:
        """Pixels to scroll (varies naturally)."""
        # Normal scrolling
        if random.random() < 0.7:
            return int(random.gauss(300, 100))
        # Large scroll (page down)
        elif random.random() < 0.5:
            return int(random.gauss(800, 200))
        # Tiny scroll (adjustment)
        else:
            return int(random.gauss(50, 30))


class CircadianModel:
    """Model session timing based on time-of-day patterns."""

    @staticmethod
    def activity_multiplier(hour: Optional[int] = None) -> float:
        """Get activity level multiplier based on hour (0-23).

        Peak hours: 10-12, 14-17, 20-22
        Low hours: 2-6
        """
        if hour is None:
            import datetime
            hour = datetime.datetime.now().hour

        # Cosine-based circadian curve
        # Peak at 15:00, trough at 4:00
        phase = (hour - 15) * math.pi / 12
        base = 0.5 + 0.5 * math.cos(phase)
        # Add natural variation
        return _clamp(base * random.uniform(0.8, 1.2), 0.1, 1.0)

    @staticmethod
    def session_duration(hour: Optional[int] = None) -> float:
        """Expected session duration in minutes."""
        activity = CircadianModel.activity_multiplier(hour)
        # 5-45 minutes, scaled by activity
        return random.lognormvariate(2.5, 0.6) * activity


class HumanKineticSynthesizer:
    """
    Master synthesizer combining all timing models.

    Usage:
        hks = HumanKineticSynthesizer()

        # Get delay between page loads
        await asyncio.sleep(hks.page_load_delay())

        # Get typing sequence
        delays = hks.typing.type_string("search query")

        # Get browsing session timing
        plan = hks.session_plan(num_pages=10)
    """

    def __init__(self) -> None:
        self.poisson = PoissonJitter()
        self.reading = ReadingTimeModel()
        self.clicks = ClickTimingModel()
        self.typing = TypingModel()
        self.scrolling = ScrollModel()
        self.circadian = CircadianModel()

    def page_load_delay(self) -> float:
        """Delay between page loads (seconds)."""
        # Combine reading + click + loading wait
        return (
            self.reading.estimate() +
            self.clicks.delay() * 0.3 +
            random.uniform(0.2, 0.8)  # "loading" time
        )

    def api_request_delay(self) -> float:
        """Delay between API requests."""
        return self.poisson.delay(rate=random.uniform(0.3, 1.0))

    def session_plan(self, num_pages: int = 10) -> List[float]:
        """Generate full session timing plan."""
        activity = self.circadian.activity_multiplier()
        delays = []
        for i in range(num_pages):
            d = self.page_load_delay() / activity
            # Occasional long break
            if random.random() < 0.1:
                d += random.uniform(10, 30)
            delays.append(_clamp(d, 0.5, 60))
        return delays


_hks: Optional[HumanKineticSynthesizer] = None

def get_kinetic_synthesizer() -> HumanKineticSynthesizer:
    global _hks
    if _hks is None:
        _hks = HumanKineticSynthesizer()
    return _hks


