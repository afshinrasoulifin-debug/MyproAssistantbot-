
from __future__ import annotations
"""
infrastructure.core.entropy — Behavioral Entropy Engine
══════════════════════════════════════════════════════
Generates human-like timing and behavioral noise to evade 
advanced behavioral analysis from WAFs and bot detectors.
"""
import random
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

class BehavioralEntropy:
    """
    Engine to simulate human-like delays and interaction patterns.
    Uses Gaussian distributions and Chaos Theory to avoid linear patterns.
    """
    
    def __init__(self, aggressiveness: float = 1.0) -> None:
        self.aggressiveness = aggressiveness # 0.1 (stealthy) to 5.0 (aggressive)

    async def human_delay(self, context: str = "default") -> Any:
        """
        Generates a delay based on the operation context.
        - 'page_load': Simulates reading time (2-8s)
        - 'api_call': Simulates UI interaction (0.5-2s)
        - 'recon': High stealth (5-15s)
        """
        base_delays = {
            "page_load": (2.0, 8.0),
            "api_call": (0.5, 2.5),
            "recon": (5.0, 20.0),
            "default": (1.0, 3.0)
        }
        
        min_d, max_d = base_delays.get(context, base_delays["default"])
        
        # Adjust by aggressiveness (higher aggressiveness = lower delay)
        min_d /= self.aggressiveness
        max_d /= self.aggressiveness
        
        # Use a non-linear distribution (Skew-Normal approximation)
        # Most human delays are short, but some are long (long tail)
        mu = (min_d + max_d) / 2
        sigma = (max_d - min_d) / 4
        
        delay = random.gauss(mu, sigma)
        delay = max(min_d, min(max_d, delay)) # Clamp
        
        # Add "jitter" (chaos factor)
        if random.random() < 0.1: # 10% chance of a "distraction" delay
            delay *= random.uniform(1.5, 3.0)
            
        logger.debug(f"🧠 Behavioral Entropy: Injecting {delay:.2f}s delay for {context}")
        await asyncio.sleep(delay)

    def generate_noise_headers(self) -> dict:
        """Generates realistic noise headers that vary slightly."""
        # Some headers that appear/disappear or change in browsers
        noise = {}
        if random.random() > 0.7:
            noise["DNT"] = "1" # Do Not Track
        
        # Randomize Sec-CH-UA values slightly (adding/removing hints)
        return noise


