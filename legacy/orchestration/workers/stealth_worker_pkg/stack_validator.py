
"""
stealth_worker_pkg/stack_validator.py — StackValidator
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class StackValidator:
    """
    Validate that UA, platform, GPU, headers, and fingerprint are
    internally consistent. Inconsistency is the #1 detection vector.

    Example: UA says Chrome/Windows but WebGL says "Apple M2" → instant block.
    """

    @staticmethod
    def validate(
        user_agent: str,
        platform_str: str,
        webgl_renderer: str,
        webgl_vendor: str,
    ) -> List[str]:
        """Return list of inconsistencies (empty = good)."""
        issues = []

        ua_lower = user_agent.lower()

        # Platform checks
        if "windows" in ua_lower:
            if "apple" in webgl_renderer.lower() and "ANGLE" not in webgl_renderer:
                issues.append("UA=Windows but WebGL says Apple GPU")
            if "mesa" in webgl_renderer.lower():
                issues.append("UA=Windows but WebGL says Mesa (Linux)")
            if platform_str not in ("Windows", "Win32"):
                issues.append(f"UA=Windows but platform={platform_str}")

        elif "macintosh" in ua_lower or "mac os" in ua_lower:
            if "direct3d" in webgl_renderer.lower():
                issues.append("UA=macOS but WebGL says Direct3D (Windows)")
            if platform_str not in ("macOS", "MacIntel"):
                issues.append(f"UA=macOS but platform={platform_str}")

        elif "linux" in ua_lower:
            if "direct3d" in webgl_renderer.lower():
                issues.append("UA=Linux but WebGL says Direct3D (Windows)")
            if "apple" in webgl_renderer.lower():
                issues.append("UA=Linux but WebGL says Apple GPU")
            if platform_str not in ("Linux", "Linux x86_64"):
                issues.append(f"UA=Linux but platform={platform_str}")

        # Vendor consistency
        if "chrome" in ua_lower and "Google" not in webgl_vendor and "Mesa" not in webgl_vendor:
            issues.append(f"UA=Chrome but WebGL vendor={webgl_vendor}")

        return issues


# ═══════════════════════════════════════════════════════════
# CAPTCHA Detection & Bypass
# ═══════════════════════════════════════════════════════════



