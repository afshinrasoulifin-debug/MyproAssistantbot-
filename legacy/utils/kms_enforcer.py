
from __future__ import annotations
"""
utils/kms_enforcer.py — KMS Enforcement & Kill-Switch
═════════════════════════════════════════════════════════
Ensures ALL secret handling goes through KMS.
Mandatory kill-switch for unauthenticated access attempts.

Enforces:
1. No direct os.environ.get() for API keys in production code
2. No hardcoded key patterns in source
3. Automatic kill-switch on unauthorized key access
4. Audit trail for all secret access
"""

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Final, List, Optional, Set

logger = logging.getLogger(__name__)

# Env vars that MUST go through KMS
_PROTECTED_VARS: Final[Set[str]] = {
    "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "BOT_TOKEN", "TELEGRAM_BOT_TOKEN",
    "TWO_CAPTCHA_KEY", "CAPTCHA_API_KEY",
    "DATABASE_URL", "REDIS_URL",
}

# Patterns that indicate hardcoded secrets
_HARDCODED_PATTERNS: Final[List[str]] = [
    r"sk-[a-zA-Z0-9]{20,}",          # OpenAI
    r"gsk_[a-zA-Z0-9]{20,}",         # Groq
    r"AIza[a-zA-Z0-9_-]{35}",        # Google/Gemini
    r"[0-9]{8,10}:[A-Za-z0-9_-]{35}", # Telegram bot token
]


@dataclass
class AccessAttempt:
    """Record of a secret access attempt."""
    timestamp: float
    key_name: str
    source: str  # module/function that attempted access
    authorized: bool
    action_taken: str = ""


class KillSwitch:
    """Emergency kill-switch for unauthorized secret access."""

    def __init__(self, max_violations: int = 5, lockout_seconds: int = 300) -> None:
        self._max_violations = max_violations
        self._lockout_seconds = lockout_seconds
        self._violations: List[AccessAttempt] = []
        self._locked_until: float = 0.0
        self._callbacks: List[Callable] = []

    @property
    def is_locked(self) -> bool:
        return time.time() < self._locked_until

    def record_violation(self, key_name: str, source: str) -> None:
        """Record an unauthorized access attempt."""
        attempt = AccessAttempt(
            timestamp=time.time(),
            key_name=key_name,
            source=source,
            authorized=False,
            action_taken="violation_recorded",
        )
        self._violations.append(attempt)
        logger.warning("KMS VIOLATION: Unauthorized access to %s from %s "
                     "(violation %d/%d)",
                     key_name, source, len(self._violations), self._max_violations)

        # Clean old violations (>10 min)
        cutoff = time.time() - 600
        self._violations = [v for v in self._violations if v.timestamp > cutoff]

        # Trigger lockout if threshold exceeded
        if len(self._violations) >= self._max_violations:
            self._engage_lockout()

    def _engage_lockout(self) -> None:
        """Engage kill-switch lockout."""
        self._locked_until = time.time() + self._lockout_seconds
        logger.critical("KMS KILL-SWITCH ENGAGED: All secret access locked for %ds "
                      "due to %d violations",
                      self._lockout_seconds, len(self._violations))
        for cb in self._callbacks:
            try:
                cb(self._violations)
            except Exception as e:
                logger.error("Kill-switch callback error: %s", e)

    def on_lockout(self, callback: Callable) -> None:
        """Register callback for lockout events."""
        self._callbacks.append(callback)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "is_locked": self.is_locked,
            "violations": len(self._violations),
            "max_violations": self._max_violations,
            "locked_until": self._locked_until if self.is_locked else None,
        }


class KMSEnforcer:
    """
    Enforces KMS-only secret handling across the application.

    Usage:
        enforcer = get_kms_enforcer()

        # Get a key (goes through KMS, not raw env)
        key = enforcer.get_key("gemini")

        # Scan source for hardcoded secrets
        issues = enforcer.scan_source("/path/to/project")
    """

    def __init__(self) -> None:
        self._kill_switch = KillSwitch()
        self._access_log: List[AccessAttempt] = []
        self._kms = None

    def _get_kms(self) -> Any:
        if self._kms is None:
            try:
                from arki_project.utils.kms import get_kms
                self._kms = get_kms()
            except ImportError:
                logger.error("KMS module not available — enforcer running in audit-only mode")
        return self._kms

    def get_key(self, provider: str, source: str = "") -> Optional[str]:
        """Get a key through KMS with enforcement."""
        if self._kill_switch.is_locked:
            logger.error("KMS access denied: kill-switch is engaged")
            return None

        kms = self._get_kms()
        if kms:
            key = kms.get_key(provider)
            self._access_log.append(AccessAttempt(
                timestamp=time.time(),
                key_name=provider,
                source=source or "unknown",
                authorized=True,
                action_taken="kms_access",
            ))
            return key

        # Fallback: direct env access (with violation logging)
        self._kill_switch.record_violation(provider, source or "fallback")
        return None

    def scan_source(self, base_path: str) -> List[Dict[str, str]]:
        """Scan source code for hardcoded secrets and direct env access."""
        issues = []
        compiled_patterns = [re.compile(p) for p in _HARDCODED_PATTERNS]

        for root, dirs, files in os.walk(base_path, followlinks=False):
            dirs[:] = [d for d in dirs if d not in {
                "__pycache__", "arki_project", ".git", "node_modules"
            }]
            for f in files:
                if not f.endswith(".py") or f.startswith("test_"):
                    continue
                fp = os.path.join(root, f)
                try:
                    content = open(fp).read()
                except Exception:
                    continue

                rel = os.path.relpath(fp, base_path)

                # Check for hardcoded secret patterns
                for pattern in compiled_patterns:
                    matches = pattern.findall(content)
                    for m in matches:
                        issues.append({
                            "file": rel,
                            "type": "hardcoded_secret",
                            "pattern": m[:20] + "...",
                        })

                # Check for direct env access of protected vars
                for var in _PROTECTED_VARS:
                    if f'os.environ.get("{var}"' in content or f"os.environ['{var}']" in content:
                        # Skip if it's in kms.py or config.py (legitimate)
                        if f not in ("kms.py", "config.py", "kms_enforcer.py"):
                            issues.append({
                                "file": rel,
                                "type": "direct_env_access",
                                "variable": var,
                            })

        return issues

    @property
    def kill_switch(self) -> KillSwitch:
        return self._kill_switch

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_access": len(self._access_log),
            "kill_switch": self._kill_switch.stats,
            "kms_available": self._kms is not None,
        }


_enforcer: Optional[KMSEnforcer] = None

def get_kms_enforcer() -> KMSEnforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = KMSEnforcer()
    return _enforcer


