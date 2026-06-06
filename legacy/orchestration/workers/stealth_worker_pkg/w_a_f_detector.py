
"""
stealth_worker_pkg/w_a_f_detector.py — WAFDetector
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class WAFDetector:
    """
    Detect which WAF/bot-protection is active on a page.

    Detection is performed via response headers, cookies, and page content
    markers. Knowing the WAF allows the bypass pipeline to use the right
    strategy (e.g., Cloudflare needs JS challenge wait, DataDome needs
    behavioral simulation, PerimeterX needs canvas/WebGL consistency).
    """

    # Header signatures
    HEADER_SIGNATURES: Final[Dict[WAFType, List[str]]] = {
        WAFType.CLOUDFLARE: ["cf-ray", "cf-cache-status", "cf-request-id"],
        WAFType.AKAMAI: ["x-akamai-transformed", "akamai-grn", "x-akamai-session-info"],
        WAFType.DATADOME: ["x-datadome", "x-dd-b", "x-dd-type"],
        WAFType.IMPERVA: ["x-iinfo", "x-cdn"],
        WAFType.SUCURI: ["x-sucuri-id", "x-sucuri-cache"],
        WAFType.AWS_WAF: ["x-amzn-requestid", "x-amz-cf-id"],
    }

    # Cookie signatures
    COOKIE_SIGNATURES: Final[Dict[WAFType, List[str]]] = {
        WAFType.CLOUDFLARE: ["__cf_bm", "cf_clearance", "_cfuvid"],
        WAFType.DATADOME: ["datadome"],
        WAFType.PERIMETERX: ["_px3", "_pxvid", "_px"],
        WAFType.KASADA: ["__kpsdk_ct", "kpsdk-im", "kpsdk-cd"],
        WAFType.AKAMAI: ["_abck", "ak_bmsc", "bm_sz"],
        WAFType.IMPERVA: ["visid_incap_", "incap_ses_"],
    }

    # HTML content markers
    CONTENT_SIGNATURES: Final[Dict[WAFType, List[str]]] = {
        WAFType.CLOUDFLARE: ["cf-challenge-running", "cf-turnstile", "challenges.cloudflare.com"],
        WAFType.PERIMETERX: ["_pxAppId", "perimeterx.com", "px-captcha"],
        WAFType.DATADOME: ["datadome.co", "dd.js"],
        WAFType.KASADA: ["ips.js", "ips-d.kasada.io"],
        WAFType.AKAMAI: ["_abck", "akamaized.net"],
    }

    @classmethod
    async def detect(cls, page, response=None) -> List[WAFType]:
        """Detect all active WAFs on the current page."""
        detected: List[WAFType] = []

        try:
            # Check response headers
            if response:
                headers = response.headers
                for waf_type, sigs in cls.HEADER_SIGNATURES.items():
                    if any(sig in headers for sig in sigs):
                        if waf_type not in detected:
                            detected.append(waf_type)

            # Check cookies
            try:
                cookies = await page.context.cookies()
                cookie_names = {c["name"] for c in cookies}
                for waf_type, sigs in cls.COOKIE_SIGNATURES.items():
                    if any(sig in name for sig in sigs for name in cookie_names):
                        if waf_type not in detected:
                            detected.append(waf_type)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

            # Check HTML content
            try:
                html = await page.content()
                for waf_type, sigs in cls.CONTENT_SIGNATURES.items():
                    if any(sig in html for sig in sigs):
                        if waf_type not in detected:
                            detected.append(waf_type)
            except Exception as _err:
                logger.warning("Suppressed error: %s", _err)

        except Exception as e:
            logger.debug("WAF detection error: %s", e)

        if detected:
            logger.info("🛡️ WAF detected: %s", [w.value for w in detected])
        return detected

    @classmethod
    def recommend_strategy(cls, waf_types: List[WAFType]) -> Dict[str, Any]:
        """Recommend bypass strategy based on detected WAFs."""
        strategy: Dict[str, Any] = {
            "use_full_evasion": True,
            "extra_wait_seconds": 0,
            "simulate_behavior_duration": 5.0,
            "use_residential_proxy": False,
            "retry_with_different_engine": False,
        }

        for waf in waf_types:
            if waf == WAFType.CLOUDFLARE:
                strategy["extra_wait_seconds"] = max(strategy["extra_wait_seconds"], 10)
                strategy["simulate_behavior_duration"] = max(strategy["simulate_behavior_duration"], 8.0)
            elif waf == WAFType.DATADOME:
                strategy["simulate_behavior_duration"] = max(strategy["simulate_behavior_duration"], 12.0)
                strategy["use_residential_proxy"] = True
            elif waf == WAFType.PERIMETERX:
                strategy["use_full_evasion"] = True
                strategy["simulate_behavior_duration"] = max(strategy["simulate_behavior_duration"], 10.0)
            elif waf == WAFType.KASADA:
                strategy["use_residential_proxy"] = True
                strategy["retry_with_different_engine"] = True
            elif waf == WAFType.AKAMAI:
                strategy["extra_wait_seconds"] = max(strategy["extra_wait_seconds"], 5)
                strategy["simulate_behavior_duration"] = max(strategy["simulate_behavior_duration"], 7.0)

        return strategy


# ═══════════════════════════════════════════════════════════
# Browser Stack Consistency Validator
# ═══════════════════════════════════════════════════════════



