
"""
autotune_pkg/simulated_annealing.py — SimulatedAnnealing
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SimulatedAnnealing:
    """
    Simulated annealing optimizer.

    Probabilistic technique that explores the search space
    with decreasing randomness over time.
    """

    def __init__(
        self,
        space: ParameterSpace,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.95,
        min_temp: float = 0.01,
        direction: OptimizeDirection = OptimizeDirection.MAXIMIZE,
    ) -> None:
        self.space = space
        self.temperature = initial_temp
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.direction = direction

        self.current_params: Dict[str, Any] = space.sample()
        self.current_score: float = float("-inf") if direction == OptimizeDirection.MAXIMIZE else float("inf")
        self.best_params: Dict[str, Any] = dict(self.current_params)
        self.best_score: float = self.current_score
        self.iteration: int = 0

    def step(self, score: float) -> Dict[str, Any]:
        """
        Perform one annealing step.

        Returns next parameter set to evaluate.
        """
        self.iteration += 1

        # Accept or reject based on Metropolis criterion
        delta = score - self.current_score
        if self.direction == OptimizeDirection.MINIMIZE:
            delta = -delta

        if delta > 0 or random.random() < math.exp(
            delta / max(self.temperature, 1e-10)
        ):
            self.current_params = dict(self._last_candidate)
            self.current_score = score

        # Update best
        if (
            (self.direction == OptimizeDirection.MAXIMIZE and score > self.best_score)
            or (self.direction == OptimizeDirection.MINIMIZE and score < self.best_score)
        ):
            self.best_params = dict(self.current_params)
            self.best_score = score

        # Cool down
        self.temperature *= self.cooling_rate
        self.temperature = max(self.temperature, self.min_temp)

        # Generate neighbor
        self._last_candidate = self._neighbor(self.current_params)
        return self._last_candidate

    def _neighbor(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a neighboring solution."""
        neighbor = dict(params)
        # Perturb one random parameter
        name = random.choice(list(self.space.params.keys()))
        pdef = self.space.params[name]

        if pdef.param_type == ParamType.CONTINUOUS:
            rng = (pdef.high - pdef.low) * self.temperature / self.initial_temp
            val = float(params[name]) + random.gauss(0, rng * 0.3)
            neighbor[name] = max(pdef.low, min(pdef.high, val))
        elif pdef.param_type == ParamType.DISCRETE:
            step = pdef.step or 1
            delta = random.choice([-step, step])
            val = float(params[name]) + delta
            neighbor[name] = max(pdef.low, min(pdef.high, val))
        else:
            neighbor[name] = pdef.sample()

        return neighbor

    def reset(self) -> None:
        """Reset temperature (restart)."""
        self.temperature = self.initial_temp


# ═══════════════════════════════════════════════════════════════════
# A/B Test Framework
# ═══════════════════════════════════════════════════════════════════



