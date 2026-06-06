
"""
autotune_pkg/a_b_variant.py — ABVariant
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ABVariant:
    """A/B test variant."""
    name: str
    params: Dict[str, Any]
    observations: List[float] = field(default_factory=list)

    @property
    def mean(self) -> float:
        return sum(self.observations) / max(1, len(self.observations))

    @property
    def variance(self) -> float:
        if len(self.observations) < 2:
            return 0.0
        m = self.mean
        return sum((x - m) ** 2 for x in self.observations) / (len(self.observations) - 1)

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    @property
    def n(self) -> int:
        return len(self.observations)




