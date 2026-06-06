
"""
autotune_pkg/multi_armed_bandit.py — MultiArmedBandit
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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



