
from __future__ import annotations
"""
utils/titanium/config.py — TITANIUM v29.0 Central Configuration
═════════════════════════════════════════════════════════════════════
Single source of truth for all TITANIUM settings.
"""

from typing import Any, Optional


TITANIUM_CONFIG = {
    "version": "29.0.0",
    "codename": "TITANIUM",

    # ── ShieldedClient ──
    "max_connections": 500,
    "max_connections_per_host": 100,
    "default_timeout": 300.0,
    "retry_attempts": 5,
    "retry_backoff_base": 1.0,
    "retry_backoff_max": 30.0,
    # ── v10.4 Advanced Security ──
    "security_csp_enabled": True,
    "security_cors_origins": ["*"],
    "security_rate_limit_per_user": 100,
    "security_max_payload_mb": 10,
    "security_session_timeout": 3600,
    "security_brute_force_lockout": 5,
    "security_input_sanitize": True,
    "security_sql_parameterized_only": True,
    
    # ── v10.4 Advanced AI ──
    "ai_fallback_chain": ["gemini", "groq", "openrouter", "pollinations"],
    "ai_auto_model_selection": True,
    "ai_context_window_adaptive": True,
    "ai_response_quality_threshold": 0.7,
    "ai_multi_provider_consensus": True,
    
    # ── v10.4 Performance ──
    "perf_connection_pool_warmup": True,
    "perf_dns_cache_ttl": 300,
    "perf_tcp_keepalive": True,
    "perf_http2_enabled": True,
    "perf_compression": "gzip",
    "perf_lazy_load_modules": True,


    # ── Circuit Breaker ──
    "circuit_failure_threshold": 5,
    "circuit_reset_timeout": 60.0,
    "circuit_half_open_max": 3,

    # ── Rate Limiter ──
    "rate_limit_mode": "unlimited",
    "rate_limit_max_requests": 0,
    "rate_limit_abuse_threshold": 1000,
    "rate_limit_window_seconds": 60,

    # ── Header Entropy ──
    "header_language_count": 36,
    "header_ua_count": 17,
    "header_browser_brands": 8,

    # ── AI Orchestrator ──
    "ai_orchestrator_timeout": 600.0,
    "ai_max_retries": 5,
    "ai_cache_size": 2000,
    "ai_cache_ttl": 600.0,
    "ai_consensus_min": 2,
    "ai_adaptive_ema_alpha": 0.3,

    # ── Streaming ──
    "stream_chunk_timeout": 30.0,
    "stream_buffer_size": 8192,

    # ── DNS Warmup ──
    "dns_warmup_hosts": [
        "openrouter.ai",
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
        "api.together.xyz",
        "r.jina.ai",
        "image.pollinations.ai",
    ],

    # ── Fingerprints ──
    "fingerprints": [
        "chrome124",
        "chrome120",
        "chrome119",
        "edge101",
        "safari17_0",
    ],

    # ── Health Monitor ──
    "health_check_interval": 120,
    "health_probe_timeout": 10.0,
    "health_penalize_degraded": 0.5,
    "health_penalize_unhealthy": 0.1,

    # ── Security ──
    "hmac_algorithm": "sha256",
    "request_id_prefix": "T-",
    "request_id_entropy_bytes": 16,

    # ── Limits (NONE) ──
    "enforce_limits": False,
}


def get(key: str, default: Optional[Any]=None) -> Any:
    """Get a TITANIUM config value."""
    return TITANIUM_CONFIG.get(key, default)


def set_config(key: str, value: str) -> None:
    """Override a TITANIUM config value at runtime."""
    TITANIUM_CONFIG[key] = value


