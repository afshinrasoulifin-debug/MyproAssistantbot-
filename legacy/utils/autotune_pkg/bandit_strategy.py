
"""
autotune_pkg/bandit_strategy.py — BanditStrategy
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class BanditStrategy(Enum):
    UCB1 = "ucb1"
    EPSILON_GREEDY = "epsilon_greedy"
    THOMPSON = "thompson"
    BOLTZMANN = "boltzmann"
    EXP3 = "exp3"


# ═══════════════════════════════════════════════════════════════════
# Parameter Space
# ═══════════════════════════════════════════════════════════════════



