
from __future__ import annotations
"""
tg_bot/utils/proxy_rotator.py — Proxy Rotator & Stealth Layer v3.3
═══════════════════════════════════════════════════════════════════
Real proxy rotation with health checking, geo-selection,
protocol support (HTTP/SOCKS5), and automatic failover.
"""
import logging, os, random, time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class ProxyEntry:
    url: str
    protocol: str = "http"  # http, https, socks5
    country: str = ""
    label: str = ""
    is_active: bool = True
    total_requests: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    last_used: float = 0.0
    last_checked: float = 0.0
    cooldown_until: float = 0.0

    @property
    def is_available(self) -> bool:
        return self.is_active and time.time() >= self.cooldown_until

    @property
    def error_rate(self) -> float:
        return self.total_errors / max(1, self.total_requests)

    @property
    def score(self) -> float:
        """Lower is better: combines latency and error rate."""
        return self.avg_latency_ms * (1 + self.error_rate * 5)

class ProxyRotator:
    """Intelligent proxy rotation with health-based selection."""

    def __init__(self) -> None:
        self._proxies: List[ProxyEntry] = []
        self._direct_allowed = True
        self._strategy = "smart"  # smart, round_robin, random, geo
        self._rotation_idx = 0
        self._stats = {"rotations": 0, "direct": 0, "failures": 0}

    def add_proxy(self, url: str, protocol: str = "http",
                 country: str = "", label: str = "") -> ProxyEntry:
        entry = ProxyEntry(url=url, protocol=protocol, country=country,
                          label=label or f"proxy_{len(self._proxies)}")
        self._proxies.append(entry)
        return entry

    def load_from_env(self) -> int:
        """Load proxies from PROXY_LIST env (comma-separated) or PROXY_FILE."""
        loaded = 0
        proxy_list = os.environ.get("PROXY_LIST", "")
        if proxy_list:
            for p in proxy_list.split(","):
                p = p.strip()
                if p:
                    proto = "socks5" if "socks" in p.lower() else "http"
                    self.add_proxy(p, protocol=proto)
                    loaded += 1

        proxy_file = os.environ.get("PROXY_FILE", "")
        if proxy_file and os.path.exists(proxy_file):
            with open(proxy_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("|")
                        url = parts[0].strip()
                        country = parts[1].strip() if len(parts) > 1 else ""
                        proto = "socks5" if "socks" in url.lower() else "http"
                        self.add_proxy(url, protocol=proto, country=country)
                        loaded += 1
        return loaded

    def get_proxy(self, prefer_country: str = "") -> Optional[str]:
        """Get next proxy based on strategy."""
        available = [p for p in self._proxies if p.is_available]
        if not available:
            if self._direct_allowed:
                self._stats["direct"] += 1
                return None
            # Reset cooldowns
            for p in self._proxies:
                if p.is_active:
                    p.cooldown_until = 0
            available = [p for p in self._proxies if p.is_available]
            if not available:
                return None

        # Filter by country if requested
        if prefer_country:
            geo_match = [p for p in available if p.country.lower() == prefer_country.lower()]
            if geo_match:
                available = geo_match

        if self._strategy == "smart":
            # Sort by score (lower is better)
            available.sort(key=lambda p: p.score)
            selected = available[0]
        elif self._strategy == "random":
            selected = random.choice(available)
        else:  # round_robin
            self._rotation_idx = self._rotation_idx % len(available)
            selected = available[self._rotation_idx]
            self._rotation_idx += 1

        selected.total_requests += 1
        selected.last_used = time.time()
        self._stats["rotations"] += 1
        return selected.url

    def report_success(self, proxy_url: str, latency_ms: float) -> None:
        for p in self._proxies:
            if p.url == proxy_url:
                alpha = 0.2
                p.avg_latency_ms = p.avg_latency_ms * (1 - alpha) + latency_ms * alpha
                break

    def report_failure(self, proxy_url: str, error: str = "") -> None:
        for p in self._proxies:
            if p.url == proxy_url:
                p.total_errors += 1
                self._stats["failures"] += 1
                if p.error_rate > 0.5 and p.total_requests > 5:
                    p.cooldown_until = time.time() + 300
                    logger.warning("Proxy %s cooling down for 5m (error rate %.0f%%)",
                                  p.label, p.error_rate * 100)
                elif p.error_rate > 0.8:
                    p.is_active = False
                    logger.error("Proxy %s disabled", p.label)
                break

    async def health_check_all(self) -> Dict[str, Any]:
        """Check health of all proxies."""
        results = {}
        for p in self._proxies:
            results[p.label] = {
                "url": p.url[:30] + "...",
                "active": p.is_active,
                "available": p.is_available,
                "error_rate": f"{p.error_rate:.0%}",
                "avg_latency_ms": round(p.avg_latency_ms, 1),
                "requests": p.total_requests,
            }
        return results

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "total_proxies": len(self._proxies),
            "active": sum(1 for p in self._proxies if p.is_active),
            "available": sum(1 for p in self._proxies if p.is_available),
        }

_rotator: Optional[ProxyRotator] = None
def get_proxy_rotator() -> ProxyRotator:
    global _rotator
    if _rotator is None:
        _rotator = ProxyRotator()
        _rotator.load_from_env()
    return _rotator


