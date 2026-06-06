
"""
autotune_pkg/parameter_space.py — ParameterSpace
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class ParameterSpace:
    """Define and sample from a parameter space."""

    def __init__(self) -> None:
        self.params: Dict[str, ParameterDef] = {}

    def add(self, param: ParameterDef) -> "ParameterSpace":
        self.params[param.name] = param
        return self

    def add_continuous(self, name: str, low: float, high: float,
                       log_scale: bool = False) -> "ParameterSpace":
        return self.add(ParameterDef(
            name=name, param_type=ParamType.CONTINUOUS,
            low=low, high=high, log_scale=log_scale,
        ))

    def add_discrete(self, name: str, low: int, high: int,
                      step: int = 1) -> "ParameterSpace":
        return self.add(ParameterDef(
            name=name, param_type=ParamType.DISCRETE,
            low=float(low), high=float(high), step=float(step),
        ))

    def add_categorical(self, name: str,
                         choices: List[Any]) -> "ParameterSpace":
        return self.add(ParameterDef(
            name=name, param_type=ParamType.CATEGORICAL,
            choices=choices,
        ))

    def add_boolean(self, name: str) -> "ParameterSpace":
        return self.add(ParameterDef(
            name=name, param_type=ParamType.BOOLEAN,
        ))

    def sample(self) -> Dict[str, Any]:
        """Sample a random point from the parameter space."""
        return {name: p.sample() for name, p in self.params.items()}

    def dimensions(self) -> int:
        return len(self.params)


# ═══════════════════════════════════════════════════════════════════
# Trial (Single Evaluation)
# ═══════════════════════════════════════════════════════════════════



