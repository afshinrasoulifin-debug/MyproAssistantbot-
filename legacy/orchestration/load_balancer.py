
from __future__ import annotations
"""
arki_project/orchestration/load_balancer.py — Latency-Aware Load Balancer
═══════════════════════════════════════════════════════════════════
Distributes requests across providers and model variants using multiple strategies.

Author: Manus AI
"""


import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Final, Any, Set

from .types import ProviderName

# Configure logging
logger = logging.getLogger("arki.orchestration.load_balancer")

# ── TITANIUM v29.0 Integration ──
try:
    _TITANIUM_ACTIVE: Final[bool] = True
except ImportError:
    _TITANIUM_ACTIVE: Final[bool] = False


class Strategy(str, Enum):
    """Available load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LATENCY_AWARE = "latency_aware"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_RANDOM = "weighted_random"


@dataclass(slots=True)
class EndpointStats:
    """
    Real-time statistics for a single endpoint (provider + model).
    
    Attributes:
        endpoint_id (str): Unique identifier for the endpoint.
        provider (ProviderName): The AI provider.
        model_id (str): The specific model ID.
        weight (float): Base weight for selection.
        active_connections (int): Current number of ongoing requests.
        latencies (deque): Rolling window of recent latencies in milliseconds.
        total_requests (int): Cumulative count of requests.
        total_errors (int): Cumulative count of failed requests.
        last_used (float): Timestamp of the last request.
    """
    endpoint_id: str
    provider: ProviderName
    model_id: str
    weight: float = 1.0
    active_connections: int = 0
    latencies: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    total_requests: int = 0
    total_errors: int = 0
    last_used: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Calculates the average latency from the rolling window."""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def p99_latency_ms(self) -> float:
        """Calculates the 99th percentile latency."""
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = min(int(len(sorted_lat) * 0.99), len(sorted_lat) - 1)
        return sorted_lat[idx]

    @property
    def error_rate(self) -> float:
        """Calculates the current error rate (errors / total)."""
        if self.total_requests == 0:
            return 0.0
        return self.total_errors / self.total_requests


class LoadBalancer:
    """
    Multi-strategy load balancer with real-time latency and error tracking.
    
    Each endpoint represents a unique (provider, model_id) pair.
    The balancer selects the most suitable endpoint based on the active strategy.
    """

    def __init__(self, strategy: Strategy = Strategy.LATENCY_AWARE) -> None:
        """
        Initializes the LoadBalancer.
        
        Args:
            strategy (Strategy): The selection strategy to use.
        """
        self._strategy: Strategy = strategy
        self._endpoints: Dict[str, EndpointStats] = {}
        self._rr_index: int = 0  # Index for round-robin strategy

    def add_endpoint(
        self,
        provider: ProviderName,
        model_id: str,
        weight: float = 1.0,
    ) -> str:
        """
        Registers a new endpoint for load balancing.
        
        Args:
            provider (ProviderName): The provider name.
            model_id (str): The model identifier.
            weight (float): Selection weight. Defaults to 1.0.
            
        Returns:
            str: The unique endpoint_id.
        """
        eid: str = f"{provider.value}:{model_id}"
        self._endpoints[eid] = EndpointStats(
            endpoint_id=eid,
            provider=provider,
            model_id=model_id,
            weight=weight,
        )
        logger.debug(f"LB endpoint added: {eid} (weight={weight:.1f})")
        return eid

    def remove_endpoint(self, endpoint_id: str) -> None:
        """Removes an endpoint from the pool."""
        self._endpoints.pop(endpoint_id, None)

    def set_strategy(self, strategy: Strategy) -> None:
        """Updates the active selection strategy."""
        self._strategy = strategy

    def pick(
        self,
        candidates: Optional[List[str]] = None,
        exclude: Optional[Set[str]] = None,
    ) -> Optional[EndpointStats]:
        """
        Selects the best endpoint using the current strategy.
        
        Args:
            candidates (Optional[List[str]]): Specific endpoint IDs to consider.
            exclude (Optional[Set[str]]): Endpoint IDs to skip.
            
        Returns:
            Optional[EndpointStats]: The selected endpoint stats, or None if no pool available.
        """
        pool = self._get_pool(candidates, exclude)
        if not pool:
            return None

        if self._strategy == Strategy.ROUND_ROBIN:
            return self._pick_round_robin(pool)
        elif self._strategy == Strategy.LATENCY_AWARE:
            return self._pick_latency_aware(pool)
        elif self._strategy == Strategy.LEAST_CONNECTIONS:
            return self._pick_least_connections(pool)
        elif self._strategy == Strategy.WEIGHTED_RANDOM:
            return self._pick_weighted_random(pool)
        else:
            return pool[0]

    def _get_pool(
        self,
        candidates: Optional[List[str]],
        exclude: Optional[Set[str]],
    ) -> List[EndpointStats]:
        """Filters registered endpoints into a valid candidate pool."""
        if candidates:
            pool = [self._endpoints[c] for c in candidates if c in self._endpoints]
        else:
            pool = list(self._endpoints.values())
            
        if exclude:
            pool = [ep for ep in pool if ep.endpoint_id not in exclude]
        return pool

    def _pick_round_robin(self, pool: List[EndpointStats]) -> EndpointStats:
        """Simple round-robin selection."""
        self._rr_index = (self._rr_index + 1) % len(pool)
        return pool[self._rr_index]

    def _pick_latency_aware(self, pool: List[EndpointStats]) -> EndpointStats:
        """
        Selects the endpoint with the lowest weighted latency.
        
        New endpoints (with fewer than 5 requests) are prioritized to encourage exploration.
        A penalty is applied based on the current error rate.
        """
        def score(ep: EndpointStats) -> float:
            if ep.total_requests < 5:
                return 0.0  # Exploration bonus
            # Apply error penalty (latency * (1 + 5 * error_rate))
            err_penalty = 1.0 + ep.error_rate * 5
            return ep.avg_latency_ms * err_penalty

        return min(pool, key=score)

    def _pick_least_connections(self, pool: List[EndpointStats]) -> EndpointStats:
        """Selects the endpoint with the fewest active connections."""
        return min(pool, key=lambda ep: ep.active_connections)

    def _pick_weighted_random(self, pool: List[EndpointStats]) -> EndpointStats:
        """
        Selects an endpoint using weighted random selection.
        
        Uses TITANIUM's cryptographically secure weighted choice if available.
        """
        weights = [ep.weight for ep in pool]
        try:
            from arki_project.utils.titanium.crypto import csprng_weighted_choice
            return csprng_weighted_choice(pool, weights)
        except ImportError:
            import random as _rnd
            return _rnd.choices(pool, weights=weights, k=1)[0]

    def on_request_start(self, endpoint_id: str) -> None:
        """Updates stats at the beginning of a request."""
        ep = self._endpoints.get(endpoint_id)
        if ep:
            ep.active_connections += 1
            ep.total_requests += 1
            ep.last_used = time.monotonic()

    def on_request_end(
        self,
        endpoint_id: str,
        latency_ms: float,
        success: bool = True,
    ) -> None:
        """Updates stats after a request completes."""
        ep = self._endpoints.get(endpoint_id)
        if ep:
            ep.active_connections = max(0, ep.active_connections - 1)
            ep.latencies.append(latency_ms)
            if not success:
                ep.total_errors += 1

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Returns a snapshot of current statistics for all endpoints."""
        return {
            eid: {
                "provider": ep.provider.value,
                "model_id": ep.model_id,
                "avg_latency_ms": round(ep.avg_latency_ms, 1),
                "p99_latency_ms": round(ep.p99_latency_ms, 1),
                "active": ep.active_connections,
                "total": ep.total_requests,
                "error_rate": round(ep.error_rate, 3),
            }
            for eid, ep in self._endpoints.items()
        }


