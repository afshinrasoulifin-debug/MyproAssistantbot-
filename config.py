
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/config.py — Arki Engine v29.0.0
───────────────────────────────────────
Centralized configuration loaded from environment variables.
"""

from pathlib import Path

# ── Version: single source of truth from VERSION file ──
_VERSION_FILE = Path(__file__).parent / "VERSION"
APP_VERSION = _VERSION_FILE.read_text().strip() if _VERSION_FILE.exists() else "29.0.0"

import os
from dataclasses import dataclass, field




@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable application settings read from the environment."""

    # ── Required ──
    bot_token: str = field(default_factory=lambda: os.environ.get("BOT_TOKEN", ""))
    ai_api_key: str = field(
        default_factory=lambda: os.environ.get("AI_API_KEY", "")
    )

    # ── Optional providers ──
    groq_api_key: str = field(
        default_factory=lambda: os.environ.get("GROQ_API_KEY", "")
    )
    openrouter_api_key: str = field(
        default_factory=lambda: os.environ.get("OPENROUTER_API_KEY", "")
    )

    # ── Database ──
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL", "sqlite+aiosqlite:///bot.db"
        )
    )

    # ── AI tunables ──
    ai_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "AI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta",
        )
    )
    ai_model: str = field(
        default_factory=lambda: os.environ.get("AI_MODEL", "gemini-2.5-pro")  # v9.7.1: Pro
    )
    ai_max_history: int = field(
        default_factory=lambda: int(os.environ.get("AI_MAX_HISTORY", "200"))  # v9.7.1: Deep
    )
    ai_temperature: float = field(
        default_factory=lambda: float(os.environ.get("AI_TEMPERATURE", "0.7"))
    )
    ai_max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("AI_MAX_TOKENS", "65536"))  # v9.7.1: Pro max
    )

    # ── Admin ──
    admin_ids: list[int] = field(
        default_factory=lambda: [
            int(x.strip())
            for x in os.environ.get("ADMIN_IDS", "").split(",")
            if x.strip() and x.strip().isdigit()
        ]
    )

    # ── Rate limiting ──
    rate_limit_messages: int = field(
        default_factory=lambda: int(os.environ.get("RATE_LIMIT_MESSAGES", "50"))  # v29.0.0: safe default
    )
    rate_limit_window: int = field(
        default_factory=lambda: int(os.environ.get("RATE_LIMIT_WINDOW", "10"))
    )

    # ── v7 New Settings ──
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO").upper()
    )
    maintenance_mode: bool = field(
        default_factory=lambda: os.environ.get("MAINTENANCE_MODE", "").lower() in ("1", "true", "yes")
    )
    analytics_enabled: bool = field(
        default_factory=lambda: os.environ.get("ANALYTICS_ENABLED", "true").lower() in ("1", "true", "yes")
    )
    webhook_url: str = field(
        default_factory=lambda: os.environ.get("WEBHOOK_URL", "")
    )
    webhook_port: int = field(
        default_factory=lambda: int(os.environ.get("WEBHOOK_PORT", "8443"))
    )
    webhook_host: str = field(
        default_factory=lambda: os.environ.get("WEBHOOK_HOST", "0.0.0.0")
    )
    webhook_secret: str = field(
        default_factory=lambda: os.environ.get(
            "WEBHOOK_SECRET",
            __import__("secrets").token_urlsafe(32),  # Auto-generate if not set
        )
    )
    # v10.3: Redis URL for caching, rate limiting, sessions
    redis_url: str = field(
        default_factory=lambda: os.environ.get("REDIS_URL", "")
    )
    max_file_size_mb: int = field(
        default_factory=lambda: int(os.environ.get("MAX_FILE_SIZE_MB", "100"))
    )
    auto_backup_hours: int = field(
        default_factory=lambda: int(os.environ.get("AUTO_BACKUP_HOURS", "24"))
    )
    welcome_message: str = field(
        default_factory=lambda: os.environ.get("WELCOME_MESSAGE", "")
    )
    default_language: str = field(
        default_factory=lambda: os.environ.get("DEFAULT_LANGUAGE", "fa")
    )

    # ── TITANIUM v10 Settings ──
    titanium_enabled: bool = field(
        default_factory=lambda: os.environ.get("TITANIUM_ENABLED", "true").lower() in ("1", "true", "yes")
    )
    titanium_race_mode: bool = field(
        default_factory=lambda: os.environ.get("TITANIUM_RACE_MODE", "true").lower() in ("1", "true", "yes")
    )
    titanium_health_interval: int = field(
        default_factory=lambda: int(os.environ.get("TITANIUM_HEALTH_INTERVAL", "60"))
    )
    titanium_rate_limit_max: int = field(
        default_factory=lambda: int(os.environ.get("TITANIUM_RATE_LIMIT_MAX", "30"))
    )
    titanium_rate_limit_window: int = field(
        default_factory=lambda: int(os.environ.get("TITANIUM_RATE_LIMIT_WINDOW", "60"))
    )
    titanium_use_curl_cffi: bool = field(
        default_factory=lambda: os.environ.get("TITANIUM_USE_CURL_CFFI", "true").lower() in ("1", "true", "yes")
    )

    # ── Claude Ultra (free-claude-code proxy) ──
    claude_ultra_base_url: str = field(
        default_factory=lambda: os.environ.get("CLAUDE_ULTRA_BASE_URL", "http://localhost:8082")
    )
    claude_ultra_auth_token: str = field(
        default_factory=lambda: os.environ.get("CLAUDE_ULTRA_AUTH_TOKEN", "freecc")
    )

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


class ConfigError(RuntimeError):
    """Raised when configuration is invalid."""


def load_settings() -> Settings:
    """Create, validate, and return a Settings instance."""
    s = Settings()

    # ── Required checks ──
    if not s.bot_token or s.bot_token == "your-telegram-bot-token":
        raise ConfigError("BOT_TOKEN is required. Set it in .env or environment.")

    # v25.0 AUTONOMOUS: API keys are OPTIONAL — FreeAccessRouter handles all models
    # via OpenRouter :free, cross-provider fallback, and Smart Fallback chains.
    if not s.ai_api_key and not s.groq_api_key:
        import logging as _log
        _log.getLogger(__name__).info(
            "🤖 AUTONOMOUS MODE: No AI_API_KEY/GROQ_API_KEY — "
            "FreeAccessRouter handles all 116 models via free infrastructure"
        )

    # ── Range checks ──
    if not (0.0 <= s.ai_temperature <= 2.0):
        raise ConfigError(f"AI_TEMPERATURE must be 0.0–2.0, got {s.ai_temperature}")

    if s.ai_max_tokens < 1:
        raise ConfigError(f"AI_MAX_TOKENS must be 1–1048576, got {s.ai_max_tokens}")

    if s.ai_max_history < 1:
        raise ConfigError(f"AI_MAX_HISTORY must be 1–500, got {s.ai_max_history}")

    # v9.7.1: Relaxed validation
    if s.rate_limit_messages < 0:
        raise ConfigError(f"RATE_LIMIT_MESSAGES must be ≥0, got {s.rate_limit_messages}")

    if s.rate_limit_window < 1:
        raise ConfigError(f"RATE_LIMIT_WINDOW must be ≥1, got {s.rate_limit_window}")

    if s.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        raise ConfigError(f"LOG_LEVEL must be DEBUG/INFO/WARNING/ERROR/CRITICAL, got {s.log_level}")

    # ── Database URL format ──
    if not s.database_url.startswith(("sqlite", "postgresql", "mysql")):
        raise ConfigError(f"DATABASE_URL looks invalid: {s.database_url[:30]}…")

    return s


# ── Infrastructure Configuration ──
# Infrastructure configuration — read from environment
INFRA_ENABLED = os.environ.get("INFRA_ENABLED", "true").lower() in ("1", "true", "yes")
# ── v17.3: APEX TERMINATED — Production_Strict Mode ──
# INFRA_APEX is permanently disabled. Any attempt to enable triggers kernel panic.
INFRA_APEX = False  # HARDENED: cannot be overridden via env

PRODUCTION_STRICT = True  # v17.3: All subsystems run in strict production mode
_apex_env = os.environ.get("INFRA_APEX", "").lower()
if _apex_env in ("1", "true", "yes"):
    import sys
    print("\n" + "=" * 60, file=sys.stderr)
    print("  ⛔ KERNEL PANIC: INFRA_APEX=true is TERMINATED", file=sys.stderr)
    print("  System cannot boot with apex enabled.", file=sys.stderr)
    print("  Remove INFRA_APEX from environment to proceed.", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)
    sys.exit(78)  # EX_CONFIG
INFRA_MAX_TOKENS = int(os.environ.get("INFRA_MAX_TOKENS", "65536"))
INFRA_RATE_LIMIT = os.environ.get("INFRA_RATE_LIMIT", "true").lower() in ("1", "true", "yes")
INFRA_ALL_MODELS = os.environ.get("INFRA_ALL_MODELS", "true").lower() in ("1", "true", "yes")
INFRA_SAFETY_FILTER = os.environ.get("INFRA_SAFETY_FILTER", "true").lower() in ("1", "true", "yes")


_cached_settings = None

def get_settings() -> Settings:
    """Get cached settings singleton."""
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = load_settings()
    return _cached_settings


# v10.3 addition
def validate_startup_config(settings: Settings) -> list[str]:
    """Startup validation — returns warnings for non-fatal issues.

    v29.0: Added BOT_TOKEN, DATABASE_URL, and model checks.
    """
    warnings = []
    # v29.0: Critical checks
    if not settings.bot_token:
        warnings.append("🚨 BOT_TOKEN is empty — bot cannot start! Set BOT_TOKEN env var.")
    if not settings.database_url:
        warnings.append("⚠️ DATABASE_URL not set — will use SQLite default")
    if not settings.admin_ids:
        warnings.append("⚠️ ADMIN_IDS is empty — nobody can use admin commands")
    if settings.ai_temperature > 1.5:
        warnings.append(f"⚠️ AI_TEMPERATURE={settings.ai_temperature} is very high — responses may be chaotic")
    if settings.ai_max_tokens > 100000:
        warnings.append(f"⚠️ AI_MAX_TOKENS={settings.ai_max_tokens} is very high — may increase costs")
    # v10.3: redis_url check
    if not settings.redis_url:
        warnings.append("ℹ️ REDIS_URL not set — rate limiting uses in-memory fallback")

    # v10.3.1: Disk space + log directory checks
    try:
        import shutil as _shutil_chk
        _, _, free = _shutil_chk.disk_usage(os.path.dirname(os.path.abspath(__file__)))
        free_gb = free / (1024 ** 3)
        if free_gb < 1.0:
            warnings.append(f"⚠️ Disk space low: {free_gb:.1f} GB free")
    except ArkiBaseError:
        pass  # v29.0: disk check optional — don't crash boot

    try:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
    except PermissionError:
        warnings.append("⚠️ Cannot create logs/ directory — check permissions")

    return warnings


