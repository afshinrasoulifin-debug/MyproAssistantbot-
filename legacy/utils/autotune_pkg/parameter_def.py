
"""
autotune_pkg/parameter_def.py — ParameterDef
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class ParameterDef:
    """Definition of a tunable parameter."""
    name: str
    param_type: ParamType
    low: float = 0.0
    high: float = 1.0
    step: Optional[float] = None
    choices: List[Any] = field(default_factory=list)
    default: Any = None
    log_scale: bool = False

    def sample(self) -> Any:
        """Sample a random value from this parameter."""
        if self.param_type == ParamType.CONTINUOUS:
            if self.log_scale:
                log_low = math.log(max(self.low, 1e-10))
                log_high = math.log(max(self.high, 1e-10))
                return math.exp(random.uniform(log_low, log_high))
            return random.uniform(self.low, self.high)

        elif self.param_type == ParamType.DISCRETE:
            step = self.step or 1  # v9.8.7: always ≥ 1, no need for 1e-6 guard
            n_steps = int((self.high - self.low) / step)
            return self.low + random.randint(0, n_steps) * step

        elif self.param_type == ParamType.CATEGORICAL:
            return random.choice(self.choices) if self.choices else None

        elif self.param_type == ParamType.BOOLEAN:
            return random.random() > 0.5

        return self.default




