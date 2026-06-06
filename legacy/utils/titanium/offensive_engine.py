
from __future__ import annotations
"""
utils/titanium/offensive_engine.py — Offensive WAF Penetration Engine v1.0
═══════════════════════════════════════════════════════════════════════════
Implements active target fingerprinting, dynamic signature reconstruction,
and advanced H2 frame control for high-stakes penetration.
"""


import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from arki_project.utils.h2_transport import h2_profile_selector
from arki_project.utils.tls_fingerprint import tls_engine

logger = logging.getLogger("arki.titanium.offensive")

class WAFType:
    CLOUDFLARE = "cloudflare"
    AKAMAI = "akamai"
    DATADOME = "datadome"
    PERIMETERX = "perimeterx"
    AWS_WAF = "aws_waf"
    UNKNOWN = "unknown"

@dataclass
class TargetSignature:
    """Detailed fingerprint of the target's defense layer."""
    waf: str = WAFType.UNKNOWN
    h2_support: bool = True
    tls_version: str = "1.3"
    challenges: List[str] = field(default_factory=list)
    latency_threshold: float = 500.0

class OffensiveEngine:
    """
    TITANIUM's offensive engine for active WAF penetration.
    """

    def __init__(self) -> None:
        self._target_cache: Dict[str, TargetSignature] = {}

    def fingerprint_target(self, domain: str, headers: Dict[str, str]) -> TargetSignature:
        """
        Identify the WAF and defense characteristics of the target.
        """
        if domain in self._target_cache:
            return self._target_cache[domain]

        h_str = str(headers).lower()
        waf = WAFType.UNKNOWN
        
        # Detection logic (based on response headers)
        if any(s in h_str for s in ["cf-ray", "cf-cache-status", "cloudflare"]):
            waf = WAFType.CLOUDFLARE
        elif any(s in h_str for s in ["x-akamai", "ak_bmsc", "akamai"]):
            waf = WAFType.AKAMAI
        elif "datadome" in h_str:
            waf = WAFType.DATADOME
        elif "perimeterx" in h_str:
            waf = WAFType.PERIMETERX
        elif "awswaf" in h_str:
            waf = WAFType.AWS_WAF

        sig = TargetSignature(waf=waf)
        self._target_cache[domain] = sig
        logger.info("🎯 Offensive Engine: Target %s identified as %s", domain, waf)
        return sig

    def reconstruct_signature(self, sig: TargetSignature, browser: str = "chrome") -> Dict[str, Any]:
        """
        Reconstruct the network signature (TLS/H2) based on the detected WAF.
        """
        config = {
            "tls_profile": None,
            "h2_profile": None,
            "h2_settings": {},
        }

        # WAF-specific tuning
        if sig.waf == WAFType.CLOUDFLARE:
            # Cloudflare is sensitive to JA3/JA4 and H2 Settings order
            config["tls_profile"] = tls_engine.select_profile(browser, "windows")
            config["h2_profile"] = h2_profile_selector.select(browser)
            # Cloudflare prefers larger initial window sizes
            config["h2_settings"] = {4: 6291456, 1: 65536} 

        elif sig.waf == WAFType.AKAMAI:
            # Akamai checks header order and cookie consistency heavily
            config["tls_profile"] = tls_engine.select_profile(browser, "macos")
            config["h2_profile"] = h2_profile_selector.select(browser)
            # Akamai often expects smaller frame sizes
            config["h2_settings"] = {5: 16384}

        else:
            # Default to modern Chrome signature
            config["tls_profile"] = tls_engine.select_profile("chrome", "windows")
            config["h2_profile"] = h2_profile_selector.select("chrome")

        return config

offensive_engine = OffensiveEngine()


