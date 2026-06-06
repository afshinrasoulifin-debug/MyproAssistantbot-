
"""
autotune_pkg/a_b_test.py — ABTest
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ABTest:
    """
    A/B testing with statistical significance testing.

    Uses Welch's t-test for comparing variants.
    """

    def __init__(self, name: str, min_samples: int = 30,
                 significance: float = 0.05) -> None:
        self.name = name
        self.min_samples = min_samples
        self.significance = significance
        self.variants: Dict[str, ABVariant] = {}
        self.started: float = time.time()

    def add_variant(self, name: str, params: Dict[str, Any]) -> None:
        self.variants[name] = ABVariant(name=name, params=params)

    def assign(self) -> str:
        """Randomly assign to a variant."""
        return random.choice(list(self.variants.keys()))

    def observe(self, variant: str, value: float) -> None:
        """Record an observation."""
        if variant in self.variants:
            self.variants[variant].observations.append(value)

    def is_significant(self) -> bool:
        """Check if we have enough data for significance."""
        return all(v.n >= self.min_samples for v in self.variants.values())

    def compare(self, a: str, b: str) -> Dict[str, Any]:
        """Compare two variants using Welch's t-test."""
        va = self.variants.get(a)
        vb = self.variants.get(b)
        if not va or not vb or va.n < 2 or vb.n < 2:
            return {"status": "insufficient_data"}

        # Welch's t-statistic
        se = math.sqrt(va.variance / va.n + vb.variance / vb.n)
        if se < 1e-10:
            return {"status": "no_variance"}

        t_stat = (va.mean - vb.mean) / se

        # Degrees of freedom (Welch–Satterthwaite)
        num = (va.variance / va.n + vb.variance / vb.n) ** 2
        denom = (
            (va.variance / va.n) ** 2 / (va.n - 1)
            + (vb.variance / vb.n) ** 2 / (vb.n - 1)
        )
        df = num / max(denom, 1e-10)

        # Approximate p-value (two-tailed)
        p_value = 2 * (1 - self._t_cdf(abs(t_stat), df))

        winner = a if va.mean > vb.mean else b

        return {
            "winner": winner,
            "t_statistic": round(t_stat, 4),
            "p_value": round(p_value, 6),
            "significant": p_value < self.significance,
            "a_mean": round(va.mean, 4),
            "b_mean": round(vb.mean, 4),
            "effect_size": round(abs(va.mean - vb.mean) / max(se, 1e-10), 4),
        }

    @staticmethod
    def _t_cdf(t: float, df: float) -> float:
        """Approximate Student's t CDF."""
        # Using normal approximation for large df
        if df > 30:
            return 0.5 * (1 + math.erf(t / math.sqrt(2)))
        # Simple approximation for small df
        x = df / (df + t * t)
        return 1 - 0.5 * x ** (df / 2)

    def get_winner(self) -> Optional[str]:
        """Get the winning variant if test is significant."""
        variants = list(self.variants.keys())
        if len(variants) < 2 or not self.is_significant():
            return None
        result = self.compare(variants[0], variants[1])
        if result.get("significant"):
            return result["winner"]
        return None


# ═══════════════════════════════════════════════════════════════════
# Feedback Engine
# ═══════════════════════════════════════════════════════════════════



