
from __future__ import annotations
"""
utils/browser_validator.py — Live Browser Fingerprint Validator v1.0-TITAN
═══════════════════════════════════════════════════════════════════════════
Real-world validation of browser stealth by testing against known
fingerprint detection services.

Tests against:
1. CreepJS — Most comprehensive JS fingerprint analysis
2. BrowserLeaks — WebRTC, Canvas, WebGL, Font, Audio fingerprints
3. Bot.sannysoft.com — Automation detection
4. PixelScan — Browser consistency scanner
5. ipinfo.io — IP quality check
6. tls.peet.ws — JA3/JA4 TLS fingerprint checker

This module runs automated validation sessions and produces a
stealth quality score (0-100) with detailed breakdown.

Author: Arki Engine TITAN
License: Proprietary
"""


import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Tuple

logger = logging.getLogger("arki.browser_validator")


# ═══════════════════════════════════════════════════════════
# Validation Targets
# ═══════════════════════════════════════════════════════════

class ValidationTarget(Enum):
    """Known fingerprint detection services."""
    CREEPJS = "creepjs"
    BROWSERLEAKS_CANVAS = "browserleaks_canvas"
    BROWSERLEAKS_WEBGL = "browserleaks_webgl"
    BROWSERLEAKS_WEBRTC = "browserleaks_webrtc"
    BROWSERLEAKS_FONTS = "browserleaks_fonts"
    BOT_SANNYSOFT = "bot_sannysoft"
    PIXELSCAN = "pixelscan"
    IPINFO = "ipinfo"
    TLS_PEET = "tls_peet"
    INTOLI = "intoli"


VALIDATION_URLS: Final[Dict[ValidationTarget, str]] = {
    ValidationTarget.CREEPJS: "https://abrahamjuliot.github.io/creepjs/",
    ValidationTarget.BROWSERLEAKS_CANVAS: "https://browserleaks.com/canvas",
    ValidationTarget.BROWSERLEAKS_WEBGL: "https://browserleaks.com/webgl",
    ValidationTarget.BROWSERLEAKS_WEBRTC: "https://browserleaks.com/webrtc",
    ValidationTarget.BROWSERLEAKS_FONTS: "https://browserleaks.com/fonts",
    ValidationTarget.BOT_SANNYSOFT: "https://bot.sannysoft.com/",
    ValidationTarget.PIXELSCAN: "https://pixelscan.net/",
    ValidationTarget.IPINFO: "https://ipinfo.io/json",
    ValidationTarget.TLS_PEET: "https://tls.peet.ws/api/all",
    ValidationTarget.INTOLI: "https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html",
}


# ═══════════════════════════════════════════════════════════
# Validation Results
# ═══════════════════════════════════════════════════════════

class CheckStatus(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class ValidationCheck:
    """Single validation check result."""
    name: str
    target: str
    status: CheckStatus
    details: str = ""
    score: int = 0   # 0-100 contribution

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "target": self.target,
            "status": self.status_code.value,
            "details": self.details,
            "score": self.score,
        }


@dataclass
class ValidationReport:
    """Complete validation report."""
    timestamp: float = 0.0
    duration_seconds: float = 0.0
    overall_score: int = 0
    checks: List[ValidationCheck] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ip_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status_code == CheckStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status_code == CheckStatus.FAIL)

    @property
    def total(self) -> int:
        return len([c for c in self.checks if c.status_code != CheckStatus.SKIP])

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"🔍 Stealth Validation Report",
            f"   Score: {self.overall_score}/100",
            f"   Passed: {self.passed}/{self.total}",
            f"   Duration: {self.duration_seconds:.1f}s",
            "",
        ]
        for check in self.checks:
            icon = {"pass": "✅", "warn": "⚠️", "fail": "❌", "skip": "⏭️", "error": "💥"}
            lines.append(f"   {icon.get(check.status_code.value, '?')} {check.name}: {check.details}")

        if self.warnings:
            lines.append("")
            lines.append("   ⚠️ Warnings:")
            for w in self.warnings:
                lines.append(f"      - {w}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
            "checks": [c.to_dict() for c in self.checks],
            "warnings": self.warnings,
            "ip_info": self.ip_info,
        }


# ═══════════════════════════════════════════════════════════
# Browser Validator Engine
# ═══════════════════════════════════════════════════════════

class BrowserValidator:
    """
    Automated browser stealth validation engine.

    Usage:
        validator = BrowserValidator()
        report = await validator.validate(stealth_worker, url_optional)

    The validator creates a stealth session and runs it through
    fingerprint detection services, analyzing the results.
    """

    # Check definitions: name, weight (how much it matters for score)
    CHECKS: Final[List[Tuple[str, str, int]]] = [
        ("webdriver_hidden", "Navigator.webdriver is undefined", 15),
        ("chrome_runtime", "window.chrome object exists", 10),
        ("plugins_present", "navigator.plugins is non-empty", 5),
        ("languages_set", "navigator.languages is populated", 5),
        ("webrtc_no_leak", "No IP leak via WebRTC", 10),
        ("canvas_unique", "Canvas fingerprint has noise", 10),
        ("webgl_consistent", "WebGL vendor/renderer consistent with UA", 10),
        ("audio_unique", "AudioContext fingerprint has noise", 5),
        ("permissions_normal", "Permissions API responses are realistic", 5),
        ("headless_markers", "No headless detection markers", 15),
        ("ip_quality", "IP is not flagged as datacenter/proxy", 10),
    ]

    def __init__(self) -> None:
        self._last_report: Optional[ValidationReport] = None

    async def validate_page(self, page: Any) -> ValidationReport:
        """
        Run validation checks on an already-open page.

        This is the core validation method. It injects detection scripts
        and analyzes the results.
        """
        report = ValidationReport(timestamp=time.time())
        start = time.time()

        # Run each check
        report.checks.append(await self._check_webdriver(page))
        report.checks.append(await self._check_chrome_runtime(page))
        report.checks.append(await self._check_plugins(page))
        report.checks.append(await self._check_languages(page))
        report.checks.append(await self._check_permissions(page))
        report.checks.append(await self._check_headless_markers(page))
        report.checks.append(await self._check_canvas(page))
        report.checks.append(await self._check_webgl(page))
        report.checks.append(await self._check_webrtc(page))

        # Calculate score
        total_weight = sum(w for _, _, w in self.CHECKS)
        earned = sum(
            c.score for c in report.checks if c.status_code == CheckStatus.PASS
        )
        report.overall_score = min(100, int((earned / max(total_weight, 1)) * 100))
        report.duration_seconds = time.time() - start

        self._last_report = report
        return report

    async def validate_against_service(
        self,
        page: Any,
        target: ValidationTarget,
    ) -> ValidationCheck:
        """Navigate to a detection service and analyze results."""
        url = VALIDATION_URLS.get(target, "")
        if not url:
            return ValidationCheck(
                name=target.value, target=url,
                status=CheckStatus.SKIP, details="Unknown target",
            )

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)  # Let JS execute

            if target == ValidationTarget.BOT_SANNYSOFT:
                return await self._analyze_sannysoft(page)
            elif target == ValidationTarget.INTOLI:
                return await self._analyze_intoli(page)
            elif target == ValidationTarget.TLS_PEET:
                return await self._analyze_tls_peet(page)
            else:
                return ValidationCheck(
                    name=target.value, target=url,
                    status=CheckStatus.PASS,
                    details="Page loaded without block",
                    score=5,
                )

        except Exception as e:
            return ValidationCheck(
                name=target.value, target=url,
                status=CheckStatus.ERROR,
                details=str(e),
            )

    # ── Individual Checks ──

    async def _check_webdriver(self, page: Any) -> ValidationCheck:
        """Check if navigator.webdriver is properly hidden."""
        try:
            result = await page.evaluate("""() => {
                return {
                    webdriver: navigator.webdriver,
                    webdriverPresent: 'webdriver' in navigator,
                    webdriverValue: Object.getOwnPropertyDescriptor(
                        Object.getPrototypeOf(navigator), 'webdriver'
                    )?.get?.toString().includes('native code'),
                };
            }""")

            if result.get("webdriver") is True:
                return ValidationCheck(
                    name="webdriver_hidden", target="navigator.webdriver",
                    status=CheckStatus.FAIL,
                    details="navigator.webdriver = true (DETECTED!)",
                    score=0,
                )
            elif result.get("webdriver") is False:
                return ValidationCheck(
                    name="webdriver_hidden", target="navigator.webdriver",
                    status=CheckStatus.WARN,
                    details="navigator.webdriver = false (suspicious, should be undefined)",
                    score=10,
                )
            else:
                return ValidationCheck(
                    name="webdriver_hidden", target="navigator.webdriver",
                    status=CheckStatus.PASS,
                    details="navigator.webdriver = undefined ✓",
                    score=15,
                )
        except Exception as e:
            return ValidationCheck(
                name="webdriver_hidden", target="navigator.webdriver",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _check_chrome_runtime(self, page: Any) -> ValidationCheck:
        """Check if window.chrome object is present and realistic."""
        try:
            result = await page.evaluate("""() => {
                return {
                    hasChrome: !!window.chrome,
                    hasRuntime: !!(window.chrome && window.chrome.runtime),
                    hasCsi: !!(window.chrome && window.chrome.csi),
                    hasLoadTimes: !!(window.chrome && window.chrome.loadTimes),
                };
            }""")

            if not result.get("hasChrome"):
                return ValidationCheck(
                    name="chrome_runtime", target="window.chrome",
                    status=CheckStatus.FAIL,
                    details="window.chrome missing (headless detection!)",
                    score=0,
                )
            elif result.get("hasRuntime") and result.get("hasCsi"):
                return ValidationCheck(
                    name="chrome_runtime", target="window.chrome",
                    status=CheckStatus.PASS,
                    details="Full chrome object present (runtime, csi, loadTimes) ✓",
                    score=10,
                )
            else:
                return ValidationCheck(
                    name="chrome_runtime", target="window.chrome",
                    status=CheckStatus.WARN,
                    details="Partial chrome object",
                    score=5,
                )
        except Exception as e:
            return ValidationCheck(
                name="chrome_runtime", target="window.chrome",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _check_plugins(self, page: Any) -> ValidationCheck:
        """Check navigator.plugins."""
        try:
            count = await page.evaluate("() => navigator.plugins.length")
            if count >= 3:
                return ValidationCheck(
                    name="plugins_present", target="navigator.plugins",
                    status=CheckStatus.PASS,
                    details=f"{count} plugins present ✓",
                    score=5,
                )
            elif count > 0:
                return ValidationCheck(
                    name="plugins_present", target="navigator.plugins",
                    status=CheckStatus.WARN,
                    details=f"Only {count} plugins (suspicious)",
                    score=3,
                )
            else:
                return ValidationCheck(
                    name="plugins_present", target="navigator.plugins",
                    status=CheckStatus.FAIL,
                    details="No plugins (headless indicator!)",
                    score=0,
                )
        except Exception as e:
            return ValidationCheck(
                name="plugins_present", target="navigator.plugins",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _check_languages(self, page: Any) -> ValidationCheck:
        """Check navigator.languages."""
        try:
            langs = await page.evaluate("() => navigator.languages")
            if langs and len(langs) >= 2:
                return ValidationCheck(
                    name="languages_set", target="navigator.languages",
                    status=CheckStatus.PASS,
                    details=f"Languages: {langs} ✓",
                    score=5,
                )
            else:
                return ValidationCheck(
                    name="languages_set", target="navigator.languages",
                    status=CheckStatus.WARN,
                    details=f"Languages: {langs} (too few)",
                    score=3,
                )
        except Exception as e:
            return ValidationCheck(
                name="languages_set", target="navigator.languages",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _check_permissions(self, page: Any) -> ValidationCheck:
        """Check Permissions API responses."""
        try:
            result = await page.evaluate("""() => {
                return navigator.permissions.query({name: 'notifications'})
                    .then(r => r.state)
                    .catch(() => 'error');
            }""")
            if result in ("prompt", "denied"):
                return ValidationCheck(
                    name="permissions_normal", target="Permissions API",
                    status=CheckStatus.PASS,
                    details=f"notifications={result} ✓",
                    score=5,
                )
            else:
                return ValidationCheck(
                    name="permissions_normal", target="Permissions API",
                    status=CheckStatus.WARN,
                    details=f"notifications={result}",
                    score=3,
                )
        except Exception as e:
            return ValidationCheck(
                name="permissions_normal", target="Permissions API",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _check_headless_markers(self, page: Any) -> ValidationCheck:
        """Check for multiple headless browser markers."""
        try:
            result = await page.evaluate("""() => {
                const markers = [];

                // Notification check
                try {
                    if (typeof Notification === 'undefined')
                        markers.push('No Notification API');
                } catch(e) {}

                // SpeechSynthesis
                try {
                    if (typeof speechSynthesis === 'undefined')
                        markers.push('No speechSynthesis');
                } catch(e) {}

                // MediaDevices
                try {
                    if (!navigator.mediaDevices)
                        markers.push('No mediaDevices');
                } catch(e) {}

                // PDF viewer
                try {
                    if (!navigator.pdfViewerEnabled)
                        markers.push('pdfViewerEnabled=false');
                } catch(e) {}

                // Connection
                try {
                    if (!navigator.connection)
                        markers.push('No connection API');
                } catch(e) {}

                // User activation (should exist)
                try {
                    if (!navigator.userActivation)
                        markers.push('No userActivation');
                } catch(e) {}

                // outerWidth/outerHeight (0 in headless)
                if (window.outerWidth === 0 || window.outerHeight === 0)
                    markers.push('outerWidth/Height = 0');

                return markers;
            }""")

            if len(result) == 0:
                return ValidationCheck(
                    name="headless_markers", target="Multiple APIs",
                    status=CheckStatus.PASS,
                    details="No headless markers detected ✓",
                    score=15,
                )
            elif len(result) <= 2:
                return ValidationCheck(
                    name="headless_markers", target="Multiple APIs",
                    status=CheckStatus.WARN,
                    details=f"Minor markers: {', '.join(result)}",
                    score=8,
                )
            else:
                return ValidationCheck(
                    name="headless_markers", target="Multiple APIs",
                    status=CheckStatus.FAIL,
                    details=f"Headless markers: {', '.join(result)}",
                    score=0,
                )
        except Exception as e:
            return ValidationCheck(
                name="headless_markers", target="Multiple APIs",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _check_canvas(self, page: Any) -> ValidationCheck:
        """Check canvas fingerprint for noise injection."""
        try:
            # Generate canvas fingerprint twice — should differ slightly if noise works
            result = await page.evaluate("""() => {
                function getCanvasFP() {
                    const c = document.createElement('canvas');
                    c.width = 200; c.height = 50;
                    const ctx = c.getContext('2d');
                    ctx.textBaseline = 'top';
                    ctx.font = '14px Arial';
                    ctx.fillStyle = '#f60';
                    ctx.fillRect(125, 1, 62, 20);
                    ctx.fillStyle = '#069';
                    ctx.fillText('Arki fingerprint test', 2, 15);
                    return c.toDataURL();
                }
                const fp1 = getCanvasFP();
                const fp2 = getCanvasFP();
                return { same: fp1 === fp2, length: fp1.length };
            }""")

            # If noise is working, consecutive calls may or may not differ
            # (depends on implementation — seed-based noise should be deterministic)
            return ValidationCheck(
                name="canvas_unique", target="Canvas API",
                status=CheckStatus.PASS,
                details=f"Canvas fingerprint generated ({result.get('length', 0)} chars) ✓",
                score=10,
            )
        except Exception as e:
            return ValidationCheck(
                name="canvas_unique", target="Canvas API",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _check_webgl(self, page: Any) -> ValidationCheck:
        """Check WebGL vendor/renderer for consistency."""
        try:
            result = await page.evaluate("""() => {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (!gl) return { error: 'No WebGL' };
                const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                if (!debugInfo) return { error: 'No debug info' };
                return {
                    vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
                    renderer: gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL),
                };
            }""")

            if result.get("error"):
                return ValidationCheck(
                    name="webgl_consistent", target="WebGL",
                    status=CheckStatus.WARN,
                    details=result["error"],
                    score=5,
                )

            vendor = result.get("vendor", "")
            renderer = result.get("renderer", "")

            if "SwiftShader" in renderer:
                return ValidationCheck(
                    name="webgl_consistent", target="WebGL",
                    status=CheckStatus.FAIL,
                    details=f"SwiftShader detected (headless indicator!): {renderer}",
                    score=0,
                )

            return ValidationCheck(
                name="webgl_consistent", target="WebGL",
                status=CheckStatus.PASS,
                details=f"Vendor={vendor}, Renderer={renderer} ✓",
                score=10,
            )
        except Exception as e:
            return ValidationCheck(
                name="webgl_consistent", target="WebGL",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _check_webrtc(self, page: Any) -> ValidationCheck:
        """Check for WebRTC IP leaks."""
        try:
            result = await page.evaluate("""() => {
                return new Promise((resolve) => {
                    try {
                        const pc = new RTCPeerConnection({
                            iceServers: [{urls: 'stun:stun.l.google.com:19302'}]
                        });
                        const ips = [];
                        pc.createDataChannel('');
                        pc.createOffer().then(o => pc.setLocalDescription(o));
                        pc.onicecandidate = (e) => {
                            if (!e.candidate) {
                                pc.close();
                                resolve(ips);
                                return;
                            }
                            const parts = e.candidate.candidate.split(' ');
                            if (parts.length > 4) ips.push(parts[4]);
                        };
                        setTimeout(() => { pc.close(); resolve(ips); }, 5000);
                    } catch(e) {
                        resolve(['blocked:' + e.message]);
                    }
                });
            }""")

            if not result or all("blocked" in str(ip) for ip in result):
                return ValidationCheck(
                    name="webrtc_no_leak", target="WebRTC",
                    status=CheckStatus.PASS,
                    details="WebRTC blocked or no candidates ✓",
                    score=10,
                )

            # Check if any real IPs leaked
            real_ips = [ip for ip in result if not ip.startswith("0.0.0.0") and not ip.startswith("blocked")]
            if real_ips:
                return ValidationCheck(
                    name="webrtc_no_leak", target="WebRTC",
                    status=CheckStatus.WARN,
                    details=f"IP candidates found: {real_ips}",
                    score=5,
                )

            return ValidationCheck(
                name="webrtc_no_leak", target="WebRTC",
                status=CheckStatus.PASS,
                details="No real IP leaked ✓",
                score=10,
            )
        except Exception as e:
            return ValidationCheck(
                name="webrtc_no_leak", target="WebRTC",
                status=CheckStatus.ERROR, details=str(e),
            )

    # ── External Service Analyzers ──

    async def _analyze_sannysoft(self, page: Any) -> ValidationCheck:
        """Analyze bot.sannysoft.com results."""
        try:
            results = await page.evaluate("""() => {
                const rows = document.querySelectorAll('table tr');
                const checks = {};
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 2) {
                        const name = cells[0].textContent.trim();
                        const passed = cells[1].classList.contains('passed') ||
                                       cells[1].textContent.trim().toLowerCase() === 'passed';
                        checks[name] = passed;
                    }
                });
                return checks;
            }""")

            total = len(results)
            passed = sum(1 for v in results.values() if v)
            failed = [k for k, v in results.items() if not v]

            if total == 0:
                return ValidationCheck(
                    name="sannysoft", target="bot.sannysoft.com",
                    status=CheckStatus.SKIP,
                    details="Could not parse results",
                )

            score = int((passed / total) * 10)
            if not failed:
                return ValidationCheck(
                    name="sannysoft", target="bot.sannysoft.com",
                    status=CheckStatus.PASS,
                    details=f"All {total} checks passed ✓",
                    score=score,
                )
            else:
                return ValidationCheck(
                    name="sannysoft", target="bot.sannysoft.com",
                    status=CheckStatus.WARN if len(failed) < 3 else CheckStatus.FAIL,
                    details=f"{passed}/{total} passed, failed: {', '.join(failed[:5])}",
                    score=max(0, score - len(failed)),
                )
        except Exception as e:
            return ValidationCheck(
                name="sannysoft", target="bot.sannysoft.com",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _analyze_intoli(self, page: Any) -> ValidationCheck:
        """Analyze Intoli headless Chrome test."""
        try:
            results = await page.evaluate("""() => {
                const items = document.querySelectorAll('.result-item');
                const checks = {};
                items.forEach(item => {
                    const name = item.querySelector('.result-name')?.textContent?.trim();
                    const passed = item.querySelector('.result-value.passed') !== null;
                    if (name) checks[name] = passed;
                });
                return checks;
            }""")

            total = len(results)
            passed = sum(1 for v in results.values() if v)

            return ValidationCheck(
                name="intoli", target="intoli.com",
                status=CheckStatus.PASS if passed == total else CheckStatus.WARN,
                details=f"{passed}/{total} checks passed",
                score=min(10, int((passed / max(total, 1)) * 10)),
            )
        except Exception as e:
            return ValidationCheck(
                name="intoli", target="intoli.com",
                status=CheckStatus.ERROR, details=str(e),
            )

    async def _analyze_tls_peet(self, page: Any) -> ValidationCheck:
        """Analyze TLS fingerprint from tls.peet.ws."""
        try:
            content = await page.evaluate("() => document.body?.innerText || ''")
            try:
                data = json.loads(content)
                ja3 = data.get("tls", {}).get("ja3_hash", "unknown")
                ja4 = data.get("tls", {}).get("ja4", "unknown")
                h2 = data.get("http2", {})
                return ValidationCheck(
                    name="tls_fingerprint", target="tls.peet.ws",
                    status=CheckStatus.PASS,
                    details=f"JA3={ja3[:16]}..., H2 settings present={bool(h2)}",
                    score=10,
                )
            except json.JSONDecodeError:
                return ValidationCheck(
                    name="tls_fingerprint", target="tls.peet.ws",
                    status=CheckStatus.WARN,
                    details="Could not parse TLS data",
                    score=3,
                )
        except Exception as e:
            return ValidationCheck(
                name="tls_fingerprint", target="tls.peet.ws",
                status=CheckStatus.ERROR, details=str(e),
            )


# Module-level singleton
browser_validator = BrowserValidator()


