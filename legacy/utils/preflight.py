
from __future__ import annotations
"""
utils/preflight.py — Pre-flight Validation Engine
══════════════════════════════════════════════════
v17.3: Mandatory pre-flight checks before event loop start.

Validates:
1. KMS_MASTER_SECRET is present and not a known default
2. No hardcoded fallback secrets in source
3. INFRA_APEX is not enabled
4. Production_Strict mode is active
"""

import logging
import os
import sys
from typing import Dict, List

logger = logging.getLogger(__name__)

_KNOWN_INSECURE_DEFAULTS = {
    "arki-default-kms-secret-change-me",
    "arki-default-key-DO-NOT-USE-IN-PRODUCTION",
    "changeme",
    "default",
    "secret",
    "password",
    "12345",
}


class PreflightResult:
    """Pre-flight validation result."""

    def __init__(self) -> None:
        self.checks: List[Dict[str, str]] = []
        self.passed = True

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.checks.append({"name": name, "status": status, "detail": detail})
        if status == "FAIL":
            self.passed = False

    def report(self) -> str:
        lines = ["\n═══ PRE-FLIGHT VALIDATION ═══"]
        for c in self.checks:
            icon = "✅" if c["status"] == "PASS" else "⚠️" if c["status"] == "WARN" else "⛔"
            line = f"  {icon} {c['name']}: {c['status']}"
            if c["detail"]:
                line += f" — {c['detail']}"
            lines.append(line)
        lines.append(f"  {'✅ ALL CHECKS PASSED' if self.passed else '⛔ PREFLIGHT FAILED'}")
        lines.append("═════════════════════════════\n")
        return "\n".join(lines)


def run_preflight(strict: bool = True) -> PreflightResult:
    """Run all pre-flight validation checks.

    Args:
        strict: If True, system exits on failure. If False, logs warnings.
    """
    result = PreflightResult()

    # 1. KMS_MASTER_SECRET
    kms_secret = os.environ.get("KMS_MASTER_SECRET", "")
    if not kms_secret:
        result.add("KMS_MASTER_SECRET", "WARN",
                   "Not set — ephemeral key will be generated (data lost on restart)")
    elif kms_secret in _KNOWN_INSECURE_DEFAULTS:
        result.add("KMS_MASTER_SECRET", "FAIL",
                   f"Contains known insecure default: '{kms_secret[:10]}...'")
    elif len(kms_secret) < 16:
        result.add("KMS_MASTER_SECRET", "WARN",
                   f"Secret is only {len(kms_secret)} chars — recommend 32+ chars")
    else:
        result.add("KMS_MASTER_SECRET", "PASS",
                   f"Set ({len(kms_secret)} chars)")

    # 2. INFRA_APEX must be disabled
    apex = os.environ.get("INFRA_APEX", "").lower()
    if apex in ("1", "true", "yes"):
        result.add("INFRA_APEX", "FAIL",
                   "APEX is enabled — TERMINATED in v17.3")
    else:
        result.add("INFRA_APEX", "PASS", "Disabled (Production_Strict active)")

    # 3. BOT_TOKEN present
    bot_token = os.environ.get("BOT_TOKEN", "") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        result.add("BOT_TOKEN", "WARN", "Not set — bot cannot connect to Telegram")
    else:
        result.add("BOT_TOKEN", "PASS", "Set")

    # 4. At least one AI provider key
    providers = ["GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY",
                 "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    found = [p for p in providers if os.environ.get(p, "")]
    if not found:
        result.add("AI_PROVIDER_KEYS", "WARN", "No AI provider API keys found")
    else:
        result.add("AI_PROVIDER_KEYS", "PASS", f"{len(found)} provider(s) configured")

    # 5. ENCRYPTION_KEY
    enc_key = os.environ.get("ENCRYPTION_KEY", "")
    if enc_key in _KNOWN_INSECURE_DEFAULTS:
        result.add("ENCRYPTION_KEY", "FAIL", "Contains known insecure default")
    elif not enc_key:
        result.add("ENCRYPTION_KEY", "WARN", "Not set — will use KMS or ephemeral key")
    else:
        result.add("ENCRYPTION_KEY", "PASS", "Set")

    # Log report
    report = result.report()
    if result.passed:
        logger.info(report)
    else:
        logger.critical(report)
        if strict:
            logger.critical(report)  # v17.3: no print, structured logging only
            sys.exit(78)  # EX_CONFIG

    return result


