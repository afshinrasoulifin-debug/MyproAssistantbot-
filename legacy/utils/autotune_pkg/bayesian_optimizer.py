
"""
autotune_pkg/bayesian_optimizer.py — BayesianOptimizer
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class BayesianOptimizer:
    """
    Bayesian optimization with Expected Improvement.

    Uses GP surrogate + EI acquisition to efficiently
    search the parameter space.
    """

    def __init__(self, space: ParameterSpace,
                 direction: OptimizeDirection = OptimizeDirection.MAXIMIZE,
                 n_initial: int = 5) -> None:
        self.space = space
        self.direction = direction
        self.n_initial = n_initial
        self.gp = GaussianProcessSurrogate()
        self.trials: List[Trial] = []
        self.trial_counter = 0

    def suggest(self) -> Dict[str, Any]:
        """Suggest next parameters to evaluate."""
        # Random initialization phase
        if len(self.trials) < self.n_initial:
            return self.space.sample()

        # Fit GP on observed data
        X = [self._params_to_vector(t.params) for t in self.trials]
        y = [
            t.score if self.direction == OptimizeDirection.MAXIMIZE
            else -t.score
            for t in self.trials
        ]
        self.gp.fit(X, y)

        # Optimize acquisition function
        best_params = None
        best_ei = float("-inf")

        for _ in range(100):  # Random search over acquisition
            candidate = self.space.sample()
            x = self._params_to_vector(candidate)
            ei = self._expected_improvement(x, max(y))
            if ei > best_ei:
                best_ei = ei
                best_params = candidate

        return best_params or self.space.sample()

    def report(self, params: Dict[str, Any], score: float,
               metrics: Optional[Dict[str, float]] = None) -> Trial:
        """Report evaluation result."""
        self.trial_counter += 1
        trial = Trial(
            trial_id=self.trial_counter,
            params=params,
            score=score,
            metrics=metrics or {},
        )
        self.trials.append(trial)
        return trial

    def best_trial(self) -> Optional[Trial]:
        """Get the best trial so far."""
        if not self.trials:
            return None
        if self.direction == OptimizeDirection.MAXIMIZE:
            return max(self.trials, key=lambda t: t.score)
        return min(self.trials, key=lambda t: t.score)

    def _expected_improvement(self, x: List[float],
                              y_best: float) -> float:
        """Expected Improvement acquisition function."""
        mean, var = self.gp.predict(x)
        std = math.sqrt(var)
        if std < 1e-10:
            return 0.0

        z = (mean - y_best) / std
        # Approximate Φ(z) and φ(z) without scipy
        ei = std * (z * self._norm_cdf(z) + self._norm_pdf(z))
        return ei

    @staticmethod
    def _norm_cdf(x: float) -> float:
        """Standard normal CDF approximation."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    @staticmethod
    def _norm_pdf(x: float) -> float:
        """Standard normal PDF."""
        return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

    def _params_to_vector(self, params: Dict[str, Any]) -> List[float]:
        """Convert params dict to numeric vector."""
        vector: List[float] = []
        for name, pdef in self.space.params.items():
            val = params.get(name, pdef.default or 0)
            if pdef.param_type == ParamType.CONTINUOUS:
                # Normalize to [0, 1]
                rng = pdef.high - pdef.low
                vector.append((float(val) - pdef.low) / max(rng, 1e-10))
            elif pdef.param_type == ParamType.DISCRETE:
                rng = pdef.high - pdef.low
                vector.append((float(val) - pdef.low) / max(rng, 1e-10))
            elif pdef.param_type == ParamType.CATEGORICAL:
                idx = pdef.choices.index(val) if val in pdef.choices else 0
                vector.append(idx / max(1, len(pdef.choices) - 1))
            elif pdef.param_type == ParamType.BOOLEAN:
                vector.append(1.0 if val else 0.0)
        return vector


# ═══════════════════════════════════════════════════════════════════
# Genetic Algorithm
# ═══════════════════════════════════════════════════════════════════



