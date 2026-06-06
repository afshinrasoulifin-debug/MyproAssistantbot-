
from __future__ import annotations
"""
tg_bot/utils/titanium/compat.py — Drop-in CSPRNG replacement for `random` module
════════════════════════════════════════════════════════════════════════════════════
Import this instead of `random` in security-critical modules.

Usage:
    # Before (INSECURE):
    import random
    val = random.choice(items)

    # After (SECURE):
    from arki_project.utils.titanium.compat import secure_random as random
    val = random.choice(items)
"""


import math
from typing import Sequence, TypeVar

from arki_project.utils.titanium.crypto import (
    csprng_int,
    csprng_float,
    csprng_choice,
    csprng_weighted_choice,
)

T = TypeVar("T")


class SecureRandom:
    """
    Drop-in replacement for Python's `random` module using CSPRNG.

    Implements the most commonly used random.* functions with
    os.urandom() backing instead of Mersenne Twister.
    """

    @staticmethod
    def random() -> float:
        """CSPRNG replacement for random.random()."""
        return csprng_float()

    @staticmethod
    def choice(seq: Sequence[T]) -> T:
        """CSPRNG replacement for random.choice()."""
        return csprng_choice(seq)

    @staticmethod
    def choices(population: Sequence[T], *, weights: Sequence[float] | None = None,
                k: int = 1) -> list[T]:
        """CSPRNG replacement for random.choices()."""
        if weights:
            return [csprng_weighted_choice(population, weights) for _ in range(k)]
        return [csprng_choice(population) for _ in range(k)]

    @staticmethod
    def randint(a: int, b: int) -> int:
        """CSPRNG replacement for random.randint()."""
        return csprng_int(a, b)

    @staticmethod
    def randrange(start: int, stop: int | None = None, step: int = 1) -> int:
        """CSPRNG replacement for random.randrange()."""
        if stop is None:
            start, stop = 0, start
        n = len(range(start, stop, step))
        if n <= 0:
            raise ValueError("empty range for randrange()")
        return start + step * csprng_int(0, n - 1)

    @staticmethod
    def uniform(a: float, b: float) -> float:
        """CSPRNG replacement for random.uniform()."""
        return a + csprng_float() * (b - a)

    @staticmethod
    def sample(population: Sequence[T], k: int) -> list[T]:
        """CSPRNG replacement for random.sample()."""
        if k > len(population):
            raise ValueError("Sample larger than population")
        pool = list(population)
        result = []
        for _ in range(k):
            idx = csprng_int(0, len(pool) - 1)
            result.append(pool.pop(idx))
        return result

    @staticmethod
    def shuffle(x: list) -> None:
        """CSPRNG replacement for random.shuffle() (Fisher-Yates)."""
        for i in range(len(x) - 1, 0, -1):
            j = csprng_int(0, i)
            x[i], x[j] = x[j], x[i]

    @staticmethod
    def gauss(mu: float = 0.0, sigma: float = 1.0) -> float:
        """CSPRNG replacement for random.gauss()."""
        u1 = csprng_float()
        u2 = csprng_float()
        if u1 < 1e-10:
            u1 = 1e-10
        z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return mu + sigma * z


# Singleton instance — import as `random`
secure_random = SecureRandom()


