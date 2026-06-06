
"""
multi_llm_orchestrator_pkg/race_config.py — RaceConfig
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class RaceConfig(TypedDict, total=False):
    """Configuration for model racing."""
    min_results: int        # Min successful before grace (default: 5)
    grace_period: float     # Seconds after min_results (default: 5.0)
    hard_timeout: float     # Max total seconds (default: 45.0)
    wave_size: int          # Models per wave (default: 12)
    wave_delay: float       # Seconds between waves (default: 0.15)


# Type for the query function callback


