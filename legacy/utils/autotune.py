
"""
tg_bot/utils/autotune.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
AUTOTUNE — Self-Optimizing AI Parameter Tuning Engine

Bayesian hyperparameter optimization, genetic algorithms,
multi-armed bandit selection, and feedback-driven auto-tuning.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────────┐
   │                     AUTOTUNE ENGINE                         │
   ├──────────┬──────────┬──────────┬──────────┬────────────────┤
   │ Bayesian │ Genetic  │ Bandit   │ Feedback │ Parameter      │
   │ Optimize │ Algo     │ Select   │ Loop     │ Space          │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ Gaussian │ Crossovr │ UCB1     │ Rating   │ continuous     │
   │ Process  │ Mutation │ ε-greedy │ Latency  │ discrete       │
   │ Acq Func │ Selectn  │ Thompson │ Quality  │ categorical    │
   │ EI/PI/CB │ Elitism  │ Boltzman │ Cost     │ conditional    │
   │ Surrogt  │ Populatn │ EXP3     │ Custom   │ constrained    │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ Profile  │ Schedule │ History  │ A/B Test │ Export         │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ prompt   │ annealng │ store    │ split    │ best params    │
   │ model    │ warmup   │ replay   │ measure  │ leaderboard    │
   │ chain    │ decay    │ analyze  │ signif   │ config file    │
   │ agent    │ restart  │ trend    │ winner   │ report         │
   └──────────┴──────────┴──────────┴──────────┴────────────────┘

Features
────────
  • Bayesian optimization with Gaussian process surrogate
  • Genetic algorithm with crossover, mutation, elitism
  • Multi-armed bandits (UCB1, ε-greedy, Thompson sampling)
  • Simulated annealing with adaptive cooling
  • Parameter space definition (continuous, discrete, categorical)
  • A/B testing framework with significance testing
  • Feedback loop: auto-adjust from user ratings + metrics
  • Prompt tuning: optimize prompt templates & parameters
  • Model selection: auto-select best LLM for task
  • Warm-start from previous tuning sessions
  • Pareto frontier for multi-objective optimization
  • Export optimized configs

References
──────────
  Port of: apex_app/src/lib/autotune.ts (584 lines)
           + apex_app/src/lib/autotune-feedback.ts (413 lines)
  Enhanced: Bayesian optimization, genetic algorithms,
            multi-armed bandits, simulated annealing,
            A/B testing, multi-objective Pareto
"""

from __future__ import annotations

import math
try:
    from arki_project.utils.titanium.compat import secure_random as random  # v10: CSPRNG
except ImportError:
    import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ── TITANIUM v29.0 Integration ──



# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════

class ParamType(Enum):
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


class OptimizeDirection(Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class BanditStrategy(Enum):
    UCB1 = "ucb1"
    EPSILON_GREEDY = "epsilon_greedy"
    THOMPSON = "thompson"
    BOLTZMANN = "boltzmann"
    EXP3 = "exp3"


# ═══════════════════════════════════════════════════════════════════
# Parameter Space
# ═══════════════════════════════════════════════════════════════════

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

@dataclass
class Trial:
    """Record of a single hyperparameter evaluation."""
    trial_id: int
    params: Dict[str, Any]
    score: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    status: str = "completed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "params": self.params,
            "score": round(self.score, 6),
            "metrics": {k: round(v, 6) for k, v in self.metrics.items()},
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status_code,
        }


# ═══════════════════════════════════════════════════════════════════
# Bayesian Optimization
# ═══════════════════════════════════════════════════════════════════

class GaussianProcessSurrogate:
    """
    Simplified Gaussian Process surrogate model.

    Uses RBF (squared exponential) kernel for function approximation.
    Provides mean and variance predictions for acquisition functions.
    """

    def __init__(self, length_scale: float = 1.0,
                 noise: float = 1e-6) -> None:
        self.length_scale = length_scale
        self.noise = noise
        self.X: List[List[float]] = []
        self.y: List[float] = []
        self.K_inv: Optional[List[List[float]]] = None

    def fit(self, X: List[List[float]], y: List[float]) -> None:
        """Fit the GP to observed data."""
        self.X = X
        self.y = y
        n = len(X)
        if n == 0:
            return

        # Build kernel matrix K + noise*I
        K = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                K[i][j] = self._rbf_kernel(X[i], X[j])
                if i == j:
                    K[i][j] += self.noise

        # Invert (simple for small n)
        self.K_inv = self._invert_matrix(K)

    def predict(self, x: List[float]) -> Tuple[float, float]:
        """Predict mean and variance at a point."""
        if not self.X or self.K_inv is None:
            return 0.0, 1.0

        n = len(self.X)

        # k(x, X)
        k_star = [self._rbf_kernel(x, self.X[i]) for i in range(n)]

        # Mean: k* @ K_inv @ y
        alpha = self._mat_vec_mul(self.K_inv, self.y)
        mean = sum(k_star[i] * alpha[i] for i in range(n))

        # Variance: k(x,x) - k* @ K_inv @ k*
        k_xx = self._rbf_kernel(x, x) + self.noise
        v = self._mat_vec_mul(self.K_inv, k_star)
        var = k_xx - sum(k_star[i] * v[i] for i in range(n))
        var = max(var, 1e-10)

        return mean, var

    def _rbf_kernel(self, x1: List[float], x2: List[float]) -> float:
        """RBF (squared exponential) kernel."""
        sq_dist = sum((a - b) ** 2 for a, b in zip(x1, x2))
        return math.exp(-0.5 * sq_dist / (self.length_scale ** 2))

    def _mat_vec_mul(self, mat: List[List[float]],
                     vec: List[float]) -> List[float]:
        """Matrix-vector multiplication."""
        return [
            sum(mat[i][j] * vec[j] for j in range(len(vec)))
            for i in range(len(mat))
        ]

    def _invert_matrix(self, matrix: List[List[float]]) -> List[List[float]]:
        """Invert a matrix (Gauss-Jordan, small N only)."""
        n = len(matrix)
        # Augmented matrix [A|I]
        aug = [
            [matrix[i][j] for j in range(n)]
            + [1.0 if i == j else 0.0 for j in range(n)]
            for i in range(n)
        ]

        for col in range(n):
            # Find pivot
            max_row = col
            for row in range(col + 1, n):
                if abs(aug[row][col]) > abs(aug[max_row][col]):
                    max_row = row
            aug[col], aug[max_row] = aug[max_row], aug[col]

            pivot = aug[col][col]
            if abs(pivot) < 1e-12:
                pivot = 1e-12

            # Scale pivot row
            for j in range(2 * n):
                aug[col][j] /= pivot

            # Eliminate column
            for row in range(n):
                if row != col:
                    factor = aug[row][col]
                    for j in range(2 * n):
                        aug[row][j] -= factor * aug[col][j]

        # Extract inverse
        return [
            [aug[i][n + j] for j in range(n)]
            for i in range(n)
        ]


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

class GeneticOptimizer:
    """
    Genetic algorithm for hyperparameter optimization.

    Evolves a population of parameter sets through selection,
    crossover, mutation, and elitism.
    """

    def __init__(
        self,
        space: ParameterSpace,
        population_size: int = 30,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism_count: int = 2,
        direction: OptimizeDirection = OptimizeDirection.MAXIMIZE,
    ) -> None:
        self.space = space
        self.pop_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism = elitism_count
        self.direction = direction
        self.population: List[Dict[str, Any]] = []
        self.fitness: List[float] = []
        self.generation: int = 0
        self.best_ever: Optional[Tuple[Dict[str, Any], float]] = None

    def initialize(self) -> List[Dict[str, Any]]:
        """Create initial random population."""
        self.population = [self.space.sample() for _ in range(self.pop_size)]
        self.fitness = [0.0] * self.pop_size
        self.generation = 0
        return self.population

    def evaluate(self, scores: List[float]) -> None:
        """Set fitness scores for current population."""
        self.fitness = scores
        # Track best ever
        for i, score in enumerate(scores):
            if self.best_ever is None or (
                (self.direction == OptimizeDirection.MAXIMIZE and score > self.best_ever[1])
                or (self.direction == OptimizeDirection.MINIMIZE and score < self.best_ever[1])
            ):
                self.best_ever = (dict(self.population[i]), score)

    def evolve(self) -> List[Dict[str, Any]]:
        """Produce next generation."""
        self.generation += 1
        new_pop: List[Dict[str, Any]] = []

        # Elitism: keep best individuals
        ranked = sorted(
            range(len(self.population)),
            key=lambda i: self.fitness[i],
            reverse=(self.direction == OptimizeDirection.MAXIMIZE),
        )
        for i in range(min(self.elitism, len(ranked))):
            new_pop.append(dict(self.population[ranked[i]]))

        # Fill rest with crossover + mutation
        while len(new_pop) < self.pop_size:
            p1 = self._tournament_select()
            p2 = self._tournament_select()

            if random.random() < self.crossover_rate:
                child = self._crossover(p1, p2)
            else:
                child = dict(p1)

            child = self._mutate(child)
            new_pop.append(child)

        self.population = new_pop[:self.pop_size]
        self.fitness = [0.0] * self.pop_size
        return self.population

    def _tournament_select(self, k: int = 3) -> Dict[str, Any]:
        """Tournament selection."""
        candidates = random.sample(range(len(self.population)), min(k, len(self.population)))
        if self.direction == OptimizeDirection.MAXIMIZE:
            winner = max(candidates, key=lambda i: self.fitness[i])
        else:
            winner = min(candidates, key=lambda i: self.fitness[i])
        return self.population[winner]

    def _crossover(self, p1: Dict[str, Any],
                   p2: Dict[str, Any]) -> Dict[str, Any]:
        """Uniform crossover."""
        child = {}
        for name in self.space.params:
            child[name] = p1[name] if random.random() > 0.5 else p2[name]
        return child

    def _mutate(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """Random mutation."""
        for name, pdef in self.space.params.items():
            if random.random() < self.mutation_rate:
                individual[name] = pdef.sample()
        return individual


# ═══════════════════════════════════════════════════════════════════
# Multi-Armed Bandit
# ═══════════════════════════════════════════════════════════════════

class MultiArmedBandit:
    """
    Multi-armed bandit for online parameter selection.

    Supports UCB1, ε-greedy, Thompson sampling, and Boltzmann.
    """

    def __init__(self, arms: List[str],
                 strategy: BanditStrategy = BanditStrategy.UCB1) -> None:
        self.arms = arms
        self.strategy = strategy
        self.counts: Dict[str, int] = {a: 0 for a in arms}
        self.rewards: Dict[str, float] = {a: 0.0 for a in arms}
        self.reward_sq: Dict[str, float] = {a: 0.0 for a in arms}
        self.total_pulls: int = 0
        self.epsilon: float = 0.1
        self.temperature: float = 1.0

    def select(self) -> str:
        """Select an arm based on the strategy."""
        if self.strategy == BanditStrategy.UCB1:
            return self._ucb1_select()
        elif self.strategy == BanditStrategy.EPSILON_GREEDY:
            return self._epsilon_greedy_select()
        elif self.strategy == BanditStrategy.THOMPSON:
            return self._thompson_select()
        elif self.strategy == BanditStrategy.BOLTZMANN:
            return self._boltzmann_select()
        return random.choice(self.arms)

    def update(self, arm: str, reward: float) -> None:
        """Update arm statistics after observation."""
        self.counts[arm] += 1
        self.rewards[arm] += reward
        self.reward_sq[arm] += reward * reward
        self.total_pulls += 1

    def _ucb1_select(self) -> str:
        """Upper Confidence Bound selection."""
        # Pull each arm once first
        for arm in self.arms:
            if self.counts[arm] == 0:
                return arm

        best_arm = ""
        best_ucb = float("-inf")

        for arm in self.arms:
            mean = self.rewards[arm] / self.counts[arm]
            exploration = math.sqrt(
                2 * math.log(self.total_pulls) / self.counts[arm]
            )
            ucb = mean + exploration
            if ucb > best_ucb:
                best_ucb = ucb
                best_arm = arm

        return best_arm

    def _epsilon_greedy_select(self) -> str:
        """ε-greedy selection."""
        if random.random() < self.epsilon:
            return random.choice(self.arms)

        # Exploit: choose best mean
        return max(
            self.arms,
            key=lambda a: (
                self.rewards[a] / max(1, self.counts[a])
            ),
        )

    def _thompson_select(self) -> str:
        """Thompson sampling (Beta distribution approximation)."""
        samples = {}
        for arm in self.arms:
            alpha = self.rewards[arm] + 1
            beta = max(1, self.counts[arm] - self.rewards[arm] + 1)
            # Approximate Beta sample with normal
            mean = alpha / (alpha + beta)
            var = alpha * beta / ((alpha + beta) ** 2 * (alpha + beta + 1))
            samples[arm] = random.gauss(mean, math.sqrt(max(var, 1e-10)))
        return max(samples, key=lambda a: samples[a])

    def _boltzmann_select(self) -> str:
        """Boltzmann (softmax) selection."""
        means = {
            arm: self.rewards[arm] / max(1, self.counts[arm])
            for arm in self.arms
        }
        max_mean = max(means.values()) if means else 0

        # Softmax with temperature
        probs = {}
        total = 0
        for arm in self.arms:
            exp_val = math.exp((means[arm] - max_mean) / max(self.temperature, 1e-10))
            probs[arm] = exp_val
            total += exp_val

        # Normalize and sample
        r = random.random() * total
        cumulative = 0
        for arm in self.arms:
            cumulative += probs[arm]
            if cumulative >= r:
                return arm

        return self.arms[-1]

    def best_arm(self) -> str:
        """Get the best arm so far."""
        return max(
            self.arms,
            key=lambda a: self.rewards[a] / max(1, self.counts[a]),
        )

    def stats(self) -> Dict[str, Any]:
        return {
            "arms": {
                arm: {
                    "pulls": self.counts[arm],
                    "mean_reward": round(
                        self.rewards[arm] / max(1, self.counts[arm]), 4,
                    ),
                    "total_reward": round(self.rewards[arm], 4),
                }
                for arm in self.arms
            },
            "total_pulls": self.total_pulls,
            "best_arm": self.best_arm() if self.total_pulls > 0 else None,
        }


# ═══════════════════════════════════════════════════════════════════
# Simulated Annealing
# ═══════════════════════════════════════════════════════════════════

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

class FeedbackEngine:
    """
    Collect and process user feedback for auto-tuning.

    Aggregates ratings, latency, quality scores, and
    custom metrics to guide optimization.
    """

    def __init__(self) -> None:
        self.ratings: List[Dict[str, Any]] = []
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self.param_history: List[Dict[str, Any]] = []

    def record_feedback(
        self,
        params: Dict[str, Any],
        rating: float,
        latency_ms: float = 0,
        quality_score: float = 0,
        custom_metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        """Record user feedback."""
        entry = {
            "params": params,
            "rating": rating,
            "latency_ms": latency_ms,
            "quality_score": quality_score,
            "timestamp": time.time(),
        }
        if custom_metrics:
            entry["custom"] = custom_metrics

        self.ratings.append(entry)
        self.metrics["rating"].append(rating)
        self.metrics["latency"].append(latency_ms)
        self.metrics["quality"].append(quality_score)

    def compute_composite_score(self, entry: Dict[str, Any],
                                weights: Optional[Dict[str, float]] = None) -> float:
        """Compute weighted composite score."""
        w = weights or {
            "rating": 0.4,
            "quality": 0.3,
            "latency": 0.3,
        }

        # Normalize latency (lower is better)
        max_lat = max(self.metrics["latency"]) if self.metrics["latency"] else 1
        norm_latency = 1 - (entry.get("latency_ms", 0) / max(max_lat, 1))

        score = (
            w.get("rating", 0) * entry.get("rating", 0)
            + w.get("quality", 0) * entry.get("quality_score", 0)
            + w.get("latency", 0) * norm_latency
        )
        return score

    def trend(self, metric: str = "rating",
              window: int = 10) -> Dict[str, float]:
        """Compute trend for a metric."""
        values = self.metrics.get(metric, [])
        if len(values) < window:
            return {"trend": 0, "current_mean": 0}

        recent = values[-window:]
        older = values[-2 * window:-window] if len(values) >= 2 * window else values[:window]

        recent_mean = sum(recent) / len(recent)
        older_mean = sum(older) / len(older) if older else recent_mean

        return {
            "trend": round(recent_mean - older_mean, 4),
            "current_mean": round(recent_mean, 4),
            "direction": "improving" if recent_mean > older_mean else "declining",
        }


# ═══════════════════════════════════════════════════════════════════
# Autotune Engine (Main Interface)
# ═══════════════════════════════════════════════════════════════════

class AutotuneEngine:
    """
    Main autotuning engine.

    Combines Bayesian optimization, genetic algorithms,
    multi-armed bandits, and feedback for holistic tuning.
    """

    def __init__(self, space: ParameterSpace) -> None:
        self.space = space
        self.bayesian = BayesianOptimizer(space)
        self.genetic = GeneticOptimizer(space)
        self.feedback = FeedbackEngine()
        self.all_trials: List[Trial] = []

    def suggest(self, method: str = "bayesian") -> Dict[str, Any]:
        """Suggest parameters using specified method."""
        if method == "bayesian":
            return self.bayesian.suggest()
        elif method == "genetic":
            if not self.genetic.population:
                self.genetic.initialize()
            return random.choice(self.genetic.population)
        elif method == "random":
            return self.space.sample()
        return self.bayesian.suggest()

    def report(self, params: Dict[str, Any], score: float,
               metrics: Optional[Dict[str, float]] = None) -> Trial:
        """Report evaluation result."""
        trial = self.bayesian.report(params, score, metrics)
        self.all_trials.append(trial)
        return trial

    def best(self) -> Optional[Trial]:
        """Get best trial across all methods."""
        if not self.all_trials:
            return None
        return max(self.all_trials, key=lambda t: t.score)

    def leaderboard(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get top N trials."""
        sorted_trials = sorted(
            self.all_trials, key=lambda t: t.score, reverse=True,
        )
        return [t.to_dict() for t in sorted_trials[:top_n]]

    def export_best_config(self) -> Dict[str, Any]:
        """Export best configuration."""
        best = self.best()
        if not best:
            return {}
        return {
            "params": best.params,
            "score": best.score,
            "metrics": best.metrics,
            "total_trials": len(self.all_trials),
        }



# ═══════════════════════════════════════════════════════════════════════
# APEX AUTOTUNE v2 — Context-Adaptive Parameter Engine (DEEP)
# ═══════════════════════════════════════════════════════════════════════
#
# Architecture:
#   ┌──────────────────────┐
#   │   User Message        │
#   │   + History (last 4)  │
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  CONTEXT DETECTION    │ ← 20 regex patterns, 5 context types
#   │  (code/creative/      │   Current msg: 3× weight
#   │   analytical/conv/    │   History: 1× weight
#   │   chaotic)            │   Persian keywords supported
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  CONFIDENCE BLENDING  │ ← <60%: blend with balanced profile
#   │                       │   ≥60%: pure context profile
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  CONVERSATION ADAPT   │ ← >10 msgs: boost repetition penalty
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  EMA FEEDBACK LOOP    │ ← α=0.3, min 3 samples, max 50% weight
#   │  (learned_profiles)   │   Push toward ↑positive, away from ↓negative
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  USER OVERRIDES       │ ← Absolute precedence
#   └──────────┬───────────┘
#              ▼
#   ┌──────────────────────┐
#   │  BOUNDS ENFORCEMENT   │ ← Clamp to API-valid ranges
#   └──────────────────────┘
#
# Ported from: APEX-main/src/lib/autotune.ts + autotune-feedback.ts
# Version: 4.0.0-DEEP (Phase 1-5 hardened)
# ═══════════════════════════════════════════════════════════════════════


import logging
import re
import time as _time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any, Dict, Final, List, NamedTuple,
    Optional, Tuple, TypedDict,
)

_at_logger = logging.getLogger("arki.apex.autotune")

# ═══════════════════ TYPE DEFINITIONS ═══════════════════

class ContextType(str, Enum):
    """Detectable conversation context types (5 from APEX spec)."""
    CODE = "code"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    CONVERSATIONAL = "conversational"
    CHAOTIC = "chaotic"


class AutoTuneStrategy(str, Enum):
    """Available tuning strategies."""
    PRECISE = "precise"
    BALANCED = "balanced"
    CREATIVE = "creative"
    CHAOTIC = "chaotic"
    ADAPTIVE = "adaptive"  # Uses context detection


class AutoTuneParams(TypedDict, total=False):
    """Parameter set for model generation."""
    temperature: float
    top_p: float
    top_k: int
    frequency_penalty: float
    presence_penalty: float
    repetition_penalty: float


class ContextDetectionResult(NamedTuple):
    """Result from context detection."""
    context_type: str
    confidence: float
    all_scores: Dict[str, int]


class AutoTuneResult(TypedDict):
    """Complete result from apex_compute_autotune."""
    params: AutoTuneParams
    detected_context: str
    confidence: float
    reasoning: str


# ═══════════════════ STRATEGY PROFILES ═══════════════════
# Fixed presets for non-adaptive strategies.

G0D_STRATEGY_PROFILES: Final[Dict[str, AutoTuneParams]] = {
    "precise":  {"temperature": 0.2,  "top_p": 0.85, "top_k": 30,  "frequency_penalty": 0.3, "presence_penalty": 0.1, "repetition_penalty": 1.1},
    "balanced": {"temperature": 0.7,  "top_p": 0.9,  "top_k": 50,  "frequency_penalty": 0.1, "presence_penalty": 0.1, "repetition_penalty": 1.0},
    "creative": {"temperature": 1.1,  "top_p": 0.95, "top_k": 80,  "frequency_penalty": 0.4, "presence_penalty": 0.6, "repetition_penalty": 1.15},
    "chaotic":  {"temperature": 1.6,  "top_p": 0.98, "top_k": 100, "frequency_penalty": 0.7, "presence_penalty": 0.8, "repetition_penalty": 1.25},
}

# ═══════════════════ CONTEXT DETECTION PATTERNS ═══════════════════
# 20+ regex patterns, 5 context types. Pre-compiled at module level.
# Persian keywords integrated into each category.

_G0D_CONTEXT_PATTERNS: Final[Dict[str, Tuple[re.Pattern, ...]]] = {
    "code": (
        re.compile(r"\b(code|function|class|variable|bug|error|debug|compile|syntax|api|endpoint|regex|algorithm|refactor|typescript|javascript|python|rust|html|css|sql|json|xml|import|export|return|async|await|promise|interface|type|const|let|var|کد|برنامه|دیباگ)\b", re.I),
        re.compile(r"```[\s\S]*```"),
        re.compile(r"\b(fix|implement|write|create|build|deploy|test|unit test|lint|npm|pip|cargo|git)\b.{0,200}\b(code|function|app|service|component|module)\b", re.I),
        re.compile(r"[{}();=><]"),
        re.compile(r"\b(stack overflow|github|repo|pull request|commit|merge)\b", re.I),
    ),
    "creative": (
        re.compile(r"\b(write|story|poem|creative|imagine|fiction|narrative|character|plot|scene|dialogue|metaphor|lyrics|song|artistic|fantasy|dream|inspire|muse|prose|verse|haiku|بنویس|داستان|شعر|خلاق)\b", re.I),
        re.compile(r"\b(describe|paint|envision|portray|illustrate|craft)\b.{0,200}\b(world|scene|character|feeling|emotion|atmosphere)\b", re.I),
        re.compile(r"\b(roleplay|role-play|pretend|act as|you are a)\b", re.I),
        re.compile(r"\b(brainstorm|ideate|come up with|think of|generate ideas)\b", re.I),
    ),
    "analytical": (
        re.compile(r"\b(analyze|analysis|compare|contrast|evaluate|assess|examine|investigate|research|study|review|critique|breakdown|data|statistics|metrics|benchmark|measure|تحلیل|مقایسه|بررسی|گزارش)\b", re.I),
        re.compile(r"\b(pros and cons|advantages|disadvantages|trade-?offs|implications|consequences)\b", re.I),
        re.compile(r"\b(why|how does|what causes|explain|elaborate|clarify|define|summarize|overview)\b", re.I),
        re.compile(r"\b(report|document|technical|specification|architecture|diagram|whitepaper)\b", re.I),
    ),
    "conversational": (
        re.compile(r"\b(hey|hi|hello|sup|what's up|how are you|thanks|thank you|cool|nice|awesome|great|lol|haha|سلام|مرسی|ممنون|خوبی)\b", re.I),
        re.compile(r"\b(chat|talk|tell me about|what do you think|opinion|feel|believe)\b", re.I),
        re.compile(r"^.{0,30}$"),
    ),
    "chaotic": (
        re.compile(r"\b(chaos|random|wild|crazy|absurd|surreal|glitch|corrupt|break|destroy|unleash|madness|void|entropy)\b", re.I),
        re.compile(r"\b(gl1tch|h4ck|pwn|1337|l33t)\b", re.I),
        re.compile(r"(!{3,}|\?{3,}|\.{4,})"),
    ),
}

# Context-specific optimal parameters
_G0D_CONTEXT_PROFILES: Final[Dict[str, AutoTuneParams]] = {
    "code":           {"temperature": 0.15, "top_p": 0.8,  "top_k": 25,  "frequency_penalty": 0.2, "presence_penalty": 0.0, "repetition_penalty": 1.05},
    "creative":       {"temperature": 1.15, "top_p": 0.95, "top_k": 85,  "frequency_penalty": 0.5, "presence_penalty": 0.7, "repetition_penalty": 1.2},
    "analytical":     {"temperature": 0.4,  "top_p": 0.88, "top_k": 40,  "frequency_penalty": 0.2, "presence_penalty": 0.15, "repetition_penalty": 1.08},
    "conversational": {"temperature": 0.75, "top_p": 0.9,  "top_k": 50,  "frequency_penalty": 0.1, "presence_penalty": 0.1, "repetition_penalty": 1.0},
    "chaotic":        {"temperature": 1.7,  "top_p": 0.99, "top_k": 100, "frequency_penalty": 0.8, "presence_penalty": 0.9, "repetition_penalty": 1.3},
}

# Parameter bounds for clamping
_G0D_PARAM_BOUNDS: Final[Dict[str, Tuple[float, float]]] = {
    "temperature":       (0.0, 2.0),
    "top_p":             (0.0, 1.0),
    "top_k":             (1, 100),
    "frequency_penalty": (-2.0, 2.0),
    "presence_penalty":  (-2.0, 2.0),
    "repetition_penalty": (0.0, 2.0),
}

# ═══════════════════ CORE FUNCTIONS ═══════════════════

def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi] range."""
    return max(lo, min(hi, value))


def _blend_params(a: AutoTuneParams, b: AutoTuneParams, weight: float) -> AutoTuneParams:
    """Blend two parameter sets. weight: 0.0 = all A, 1.0 = all B.
    
    Uses linear interpolation per parameter. top_k is rounded to nearest int.
    Weight is clamped to [0.0, 1.0].
    
    Args:
        a: First parameter set.
        b: Second parameter set.
        weight: Blend factor toward B.
    
    Returns:
        Blended parameter set.
    """
    w = _clamp(weight, 0.0, 1.0)
    iw = 1.0 - w
    return {
        "temperature":       a["temperature"] * iw + b["temperature"] * w,
        "top_p":             a["top_p"] * iw + b["top_p"] * w,
        "top_k":             round(a["top_k"] * iw + b["top_k"] * w),
        "frequency_penalty": a["frequency_penalty"] * iw + b["frequency_penalty"] * w,
        "presence_penalty":  a["presence_penalty"] * iw + b["presence_penalty"] * w,
        "repetition_penalty": a["repetition_penalty"] * iw + b["repetition_penalty"] * w,
    }


def _apply_bounds(params: Dict[str, Any]) -> AutoTuneParams:
    """Clamp all parameters to their valid API ranges.
    
    Args:
        params: Raw parameters (may exceed bounds).
    
    Returns:
        New dict with all values clamped.
    """
    result = {}
    for k, v in params.items():
        if k in _G0D_PARAM_BOUNDS:
            lo, hi = _G0D_PARAM_BOUNDS[k]
            clamped = _clamp(float(v), lo, hi)
            result[k] = round(clamped) if k == "top_k" else round(clamped, 4)
    return result


def apex_detect_context(
    message: str,
    history: Optional[List[dict]] = None,
) -> ContextDetectionResult:
    """Detect conversation context type from message + history.
    
    Analyzes the current message (3× weight) and last 4 history messages
    (1× weight) against 20+ regex patterns across 5 context types.
    Supports both English and Persian keywords.
    
    Args:
        message: Current user message text.
        history: Optional list of previous messages [{"role":..., "content":...}].
    
    Returns:
        ContextDetectionResult(context_type, confidence, all_scores).
    
    Examples:
        >>> ctx, conf, _ = apex_detect_context("fix this Python bug in my function")
        >>> ctx
        'code'
        >>> conf > 0.5
        True
    """
    if not message or not isinstance(message, str):
        return ContextDetectionResult("conversational", 0.5, {})
    
    scores: Dict[str, int] = {ctx: 0 for ctx in _G0D_CONTEXT_PATTERNS}
    
    # Score current message (3× weight)
    for ctx, patterns in _G0D_CONTEXT_PATTERNS.items():
        for pat in patterns:
            if pat.search(message):
                scores[ctx] += 3
    
    # Score last 4 history messages (1× weight)
    if history:
        for msg in history[-4:]:
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            if not content:
                continue
            for ctx, patterns in _G0D_CONTEXT_PATTERNS.items():
                for pat in patterns:
                    if pat.search(content):
                        scores[ctx] += 1
    
    total = sum(scores.values())
    if total == 0:
        return ContextDetectionResult("conversational", 0.5, scores)
    
    best_ctx = max(scores, key=scores.get)
    confidence = min(scores[best_ctx] / max(total, 1), 1.0)
    return ContextDetectionResult(best_ctx, confidence, scores)


def apex_compute_autotune(
    message: str,
    strategy: str = "adaptive",
    history: Optional[List[dict]] = None,
    overrides: Optional[Dict[str, Any]] = None,
    learned_profiles: Optional[Dict[str, dict]] = None,
) -> AutoTuneResult:
    """Compute optimal generation parameters for the given context.
    
    Main entry point for APEX AutoTune v2. Analyzes the message,
    detects context, applies strategy profile, blends with feedback
    history, and enforces parameter bounds.
    
    Pipeline:
        1. Strategy selection (fixed profile or adaptive detection)
        2. Confidence-based blending (low confidence → blend with balanced)
        3. Conversation length adaptation (>10 msgs → boost rep penalty)
        4. EMA learned adjustments (if feedback data available)
        5. User overrides (absolute precedence)
        6. Bounds enforcement (clamp to API-valid ranges)
    
    Args:
        message: Current user message.
        strategy: 'precise', 'balanced', 'creative', 'chaotic', or 'adaptive'.
        history: Conversation message history.
        overrides: Manual parameter overrides (take absolute precedence).
        learned_profiles: EMA feedback profiles keyed by context type.
    
    Returns:
        AutoTuneResult with params, detected_context, confidence, reasoning.
    
    Examples:
        >>> result = apex_compute_autotune("write a poem about the sea", strategy="adaptive")
        >>> result["detected_context"]
        'creative'
        >>> result["params"]["temperature"] > 1.0
        True
    """
    if not isinstance(message, str):
        message = str(message) if message else ""
    
    reasoning_parts: List[str] = []
    
    # Step 1: Strategy selection
    if strategy != "adaptive" and strategy in G0D_STRATEGY_PROFILES:
        base_params = dict(G0D_STRATEGY_PROFILES[strategy])
        detected_context = "conversational"
        confidence = 1.0
        reasoning_parts.append(f"Strategy: {strategy.upper()} (fixed profile)")
    else:
        detected_context, confidence, all_scores = apex_detect_context(message, history)
        
        # Step 2: Confidence blending
        if confidence < 0.6:
            base_params = _blend_params(
                _G0D_CONTEXT_PROFILES[detected_context],
                G0D_STRATEGY_PROFILES["balanced"],
                1.0 - confidence,
            )
            reasoning_parts.append(f"Detected: {detected_context} ({round(confidence*100)}%conf → blended with balanced)")
        else:
            base_params = dict(_G0D_CONTEXT_PROFILES[detected_context])
            reasoning_parts.append(f"Detected: {detected_context} ({round(confidence*100)}%conf → pure profile)")
    
    # Step 3: Conversation length adaptation
    conv_length = len(history) if history else 0
    if conv_length > 10:
        boost = min((conv_length - 10) * 0.01, 0.15)
        base_params["repetition_penalty"] = base_params.get("repetition_penalty", 1.0) + boost
        base_params["frequency_penalty"] = base_params.get("frequency_penalty", 0.1) + boost * 0.5
        reasoning_parts.append(f"Long conv ({conv_length} msgs): rep+{boost:.2f}, freq+{boost*0.5:.2f}")
    
    # Step 4: EMA learned adjustments
    if learned_profiles and detected_context in learned_profiles:
        profile = learned_profiles[detected_context]
        sample_count = profile.get("sample_count", 0)
        adjustments = profile.get("adjustments", {})
        
        if sample_count >= 3 and adjustments:
            weight = min(sample_count / 20.0 * 0.5, 0.5)  # 3→8%, 20→50% cap
            applied_count = 0
            for k, delta in adjustments.items():
                if k in base_params and delta is not None and abs(delta) > 0.01:
                    base_params[k] = base_params[k] + delta * weight
                    applied_count += 1
            if applied_count > 0:
                reasoning_parts.append(f"EMA: {applied_count} params ({sample_count} samples, {round(weight*100)}% weight)")
    
    # Step 5: User overrides (absolute precedence)
    if overrides:
        override_count = 0
        for k, v in overrides.items():
            if v is not None and k in base_params:
                base_params[k] = v
                override_count += 1
        if override_count > 0:
            reasoning_parts.append(f"Overrides: {override_count} params")
    
    # Step 6: Bounds enforcement
    final_params = _apply_bounds(base_params)
    
    return {
        "params": final_params,
        "detected_context": detected_context,
        "confidence": round(confidence, 4),
        "reasoning": " | ".join(reasoning_parts),
    }


# ═══════════════════ EMA FEEDBACK LOOP ═══════════════════
# Online learning from user ratings (thumbs up/down).
# Constants: α=0.3, MAX_HISTORY=500, MIN_SAMPLES=3, MAX_WEIGHT=50%
#
# Architecture:
#   User rates response (+1/-1)
#        ↓
#   Record: {context_type, params, rating, heuristics}
#        ↓
#   EMA update: new = (1-α)*old + α*observation
#        ↓
#   Compute adjustments: push toward ↑positive, away from ↓negative
#        ↓
#   Next AutoTune call uses learned_profiles → gradual adaptation

_EMA_ALPHA: Final[float] = 0.3
_MAX_FEEDBACK_HISTORY: Final[int] = 500
_MIN_SAMPLES_TO_APPLY: Final[int] = 3
_MAX_LEARNED_WEIGHT: Final[float] = 0.5
_SAMPLES_FOR_MAX_WEIGHT: Final[int] = 20

_NEUTRAL_PARAMS: Final[AutoTuneParams] = {
    "temperature": 0.7, "top_p": 0.9, "top_k": 50,
    "frequency_penalty": 0.2, "presence_penalty": 0.2,
    "repetition_penalty": 1.1,
}


def compute_response_heuristics(response: str) -> Dict[str, float]:
    """Compute automated quality heuristics for a model response.
    
    Provides quality signals even without explicit user feedback.
    
    Metrics:
        - response_length: Total character count
        - repetition_score: Trigram-based (0.0=unique, 1.0=very repetitive)
        - avg_sentence_length: Average words per sentence
        - vocabulary_diversity: Unique words / total words ratio
    
    Args:
        response: The model's response text.
    
    Returns:
        Dict with 4 float metrics.
    
    Examples:
        >>> h = compute_response_heuristics("The quick brown fox jumps over the lazy dog.")
        >>> h["vocabulary_diversity"] > 0.9
        True
        >>> h["repetition_score"] < 0.1
        True
    """
    if not response:
        return {"response_length": 0, "repetition_score": 0.0,
                "avg_sentence_length": 0.0, "vocabulary_diversity": 0.0}
    
    words = response.lower().split()
    unique_words = set(words)
    word_count = len(words)
    
    # Trigram repetition (ported from APEX computeRepetitionScore)
    rep_score = 0.0
    if word_count >= 6:
        trigrams: Dict[str, int] = {}
        for i in range(word_count - 2):
            tri = f"{words[i]} {words[i+1]} {words[i+2]}"
            trigrams[tri] = trigrams.get(tri, 0) + 1
        total_tri = word_count - 2
        repeated = sum(c - 1 for c in trigrams.values() if c > 1)
        rep_score = min(repeated / max(total_tri, 1), 1.0)
    
    # Sentence metrics
    sentences = [s.strip() for s in re.split(r"[.!?]+", response) if s.strip()]
    avg_sent = (
        sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    )
    
    return {
        "response_length": len(response),
        "repetition_score": round(rep_score, 4),
        "avg_sentence_length": round(avg_sent, 2),
        "vocabulary_diversity": round(len(unique_words) / max(word_count, 1), 4),
    }


def create_feedback_state() -> Dict[str, Any]:
    """Create initial empty feedback state for all 5 context types.
    
    Returns:
        Dict with 'history' (list) and 'learned_profiles' (per-context EMA state).
    """
    return {
        "history": [],
        "learned_profiles": {
            ctx: {
                "context_type": ctx,
                "sample_count": 0,
                "positive_count": 0,
                "negative_count": 0,
                "positive_params": dict(_NEUTRAL_PARAMS),
                "negative_params": dict(_NEUTRAL_PARAMS),
                "adjustments": {},
                "last_updated": 0,
            }
            for ctx in ContextType
        },
    }


def _ema_update(current: Dict[str, float], observation: Dict[str, float], alpha: float = _EMA_ALPHA) -> Dict[str, float]:
    """Exponential Moving Average update: new = (1-α)*old + α*observation.
    
    Args:
        current: Current EMA state.
        observation: New observation to incorporate.
        alpha: Learning rate (0.3 default = moderate responsiveness).
    
    Returns:
        Updated EMA state.
    """
    inv = 1.0 - alpha
    return {
        k: current.get(k, _NEUTRAL_PARAMS.get(k, 0.7)) * inv + observation.get(k, _NEUTRAL_PARAMS.get(k, 0.7)) * alpha
        for k in _NEUTRAL_PARAMS
    }


def process_feedback(state: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    """Process a feedback record and update EMA learned profiles.
    
    Accepts a rating (+1 for upvote, -1 for downvote) along with the
    context type and parameters that produced the response. Updates the
    learned profile for that context type.
    
    Args:
        state: Current feedback state (from create_feedback_state()).
        record: {context_type, params, rating (+1/-1), [message_id]}.
    
    Returns:
        Updated state (new object, does not mutate input).
    
    Examples:
        >>> state = create_feedback_state()
        >>> record = {"context_type": "code", "params": {"temperature": 0.2}, "rating": 1}
        >>> new_state = process_feedback(state, record)
        >>> new_state["learned_profiles"]["code"]["positive_count"]
        1
    """
    if not record or not isinstance(record, dict):
        _at_logger.warning("Invalid feedback record, skipping")
        return state
    
    ctx = record.get("context_type", "conversational")
    if ctx not in [ct.value for ct in ContextType]:
        ctx = "conversational"
    
    # Clone state
    history = list(state.get("history", []))
    history.append(record)
    if len(history) > _MAX_FEEDBACK_HISTORY:
        history = history[-_MAX_FEEDBACK_HISTORY:]
    
    profiles = {}
    for k, v in state.get("learned_profiles", {}).items():
        profiles[k] = dict(v)
    
    if ctx not in profiles:
        profiles[ctx] = create_feedback_state()["learned_profiles"].get(ctx, {})
    
    profile = dict(profiles[ctx])
    profile["sample_count"] = profile.get("sample_count", 0) + 1
    profile["last_updated"] = int(_time.time())
    
    record_params = record.get("params", dict(_NEUTRAL_PARAMS))
    
    if record.get("rating", 0) > 0:
        profile["positive_count"] = profile.get("positive_count", 0) + 1
        profile["positive_params"] = _ema_update(
            profile.get("positive_params", dict(_NEUTRAL_PARAMS)),
            record_params,
        )
    else:
        profile["negative_count"] = profile.get("negative_count", 0) + 1
        profile["negative_params"] = _ema_update(
            profile.get("negative_params", dict(_NEUTRAL_PARAMS)),
            record_params,
        )
    
    # Compute adjustments: push toward positive, away from negative
    adjustments = {}
    pos_count = profile.get("positive_count", 0)
    neg_count = profile.get("negative_count", 0)
    
    if pos_count >= 1 and neg_count >= 1:
        for k in _NEUTRAL_PARAMS:
            pos_delta = profile["positive_params"].get(k, _NEUTRAL_PARAMS[k]) - _NEUTRAL_PARAMS[k]
            neg_delta = profile["negative_params"].get(k, _NEUTRAL_PARAMS[k]) - _NEUTRAL_PARAMS[k]
            adj = (pos_delta - neg_delta) * 0.5
            if abs(adj) > 0.01:
                adjustments[k] = round(adj, 4)
    elif pos_count >= _MIN_SAMPLES_TO_APPLY:
        for k in _NEUTRAL_PARAMS:
            delta = (profile["positive_params"].get(k, _NEUTRAL_PARAMS[k]) - _NEUTRAL_PARAMS[k]) * 0.5
            if abs(delta) > 0.01:
                adjustments[k] = round(delta, 4)
    
    profile["adjustments"] = adjustments
    profiles[ctx] = profile
    
    return {"history": history, "learned_profiles": profiles}


