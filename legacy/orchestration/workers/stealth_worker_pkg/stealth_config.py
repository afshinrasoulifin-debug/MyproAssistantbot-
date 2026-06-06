
"""
stealth_worker_pkg/stealth_config.py — StealthConfig
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class StealthConfig:
    """Configuration for a stealth session."""
    engine: BrowserEngine = BrowserEngine.CHROMIUM
    headless: bool = True
    timeout_ms: int = 60000
    navigation_timeout_ms: int = 30000
    # Fingerprint
    inject_canvas_noise: bool = True
    inject_webgl_noise: bool = True
    inject_audio_noise: bool = True
    randomize_viewport: bool = True
    randomize_locale: bool = True
    randomize_timezone: bool = True
    # Behavior
    simulate_human_behavior: bool = True
    min_page_dwell_ms: int = 3000
    max_page_dwell_ms: int = 8000
    # Network
    block_trackers: bool = True
    block_images: bool = False   # Keep images for CAPTCHA detection
    intercept_requests: bool = True
    # Retry
    max_retries: int = 3
    retry_delay_base: float = 5.0
    # Capture
    capture_screenshots: bool = True
    capture_dom: bool = False
    screenshots_dir: str = "sessions/screenshots"
    # Proxy (per-context)
    proxy_url: Optional[str] = None   # e.g. "socks5://user:pass@host:port"
    proxy_bypass: str = ""            # Bypass list (comma-separated domains)
    # WAF-aware behavior
    waf_adaptive: bool = True         # Auto-adapt to detected WAF
    use_evasion_arsenal: bool = True   # Use full 18-script evasion (vs legacy 4)


# ═══════════════════════════════════════════════════════════
# Legacy fallback scripts (used when evasion_scripts module unavailable)
# ═══════════════════════════════════════════════════════════



