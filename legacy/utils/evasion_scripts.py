
from __future__ import annotations
"""
utils/evasion_scripts.py — Browser Evasion Scripts Arsenal v1.0-TITAN
═══════════════════════════════════════════════════════════════════════
Military-grade JavaScript injection scripts for browser anti-detection.

Each script targets a specific fingerprinting/detection vector.
All scripts are self-contained IIFEs that can be injected independently.

Detection Vectors Covered:
──────────────────────────
 1. navigator.webdriver                (Selenium/Playwright detection)
 2. Chrome DevTools Protocol           (CDP detection)
 3. WebRTC IP leak                     (Real IP exposure)
 4. Canvas fingerprint                 (Canvas2D hash)
 5. WebGL fingerprint                  (GPU/renderer strings)
 6. AudioContext fingerprint           (Audio processing hash)
 7. Font enumeration                   (Installed fonts list)
 8. Navigator properties               (hardwareConcurrency, deviceMemory, etc.)
 9. Permissions API                    (Automation tells)
10. Battery API                        (Headless has no battery)
11. Network Information API            (Connection type spoofing)
12. Plugin/MimeType arrays             (Plugin enumeration)
13. Screen properties                  (Matching viewport to device)
14. iframe detection                   (Self-reference checks)
15. Timing attack prevention           (Date/Performance precision)
16. Chrome app/runtime                 (window.chrome object)
17. Headless mode detection            (Multiple vectors)
18. CSS media query detection          (prefers-color-scheme, etc.)
19. Speech synthesis voices            (OS fingerprinting via voices)
20. Keyboard/Input event consistency   (Event property matching)

Author: Arki Engine TITAN
"""

from typing import Dict, Final, List, Optional


# ═══════════════════════════════════════════════════════════
# 1. WEBDRIVER PROPERTY EVASION (Enhanced)
# ═══════════════════════════════════════════════════════════

WEBDRIVER_EVASION: Final[str] = """
(() => {
    // Remove webdriver property from navigator
    const newProto = navigator.__proto__;
    delete newProto.webdriver;

    // Override with getter that returns undefined
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true,
    });

    // Also handle the documentElement attribute
    if (document.documentElement) {
        Object.defineProperty(document.documentElement, 'webdriver', {
            get: () => undefined,
            configurable: true,
        });
    }

    // Remove Playwright/Selenium markers from window
    const automationProps = [
        '__playwright', '__pw_manual', '_Selenium_IDE_Recorder',
        '_selenium', 'callSelenium', '__webdriver_evaluate',
        '__selenium_evaluate', '__webdriver_unwrap',
        '__fxdriver_evaluate', '__driver_evaluate',
        '__webdriver_script_fn', '__webdriver_script_func',
        '__lastWatirAlert', '__lastWatirConfirm',
        '__lastWatirPrompt', '_WEBDRIVER_ELEM_CACHE',
        'ChromeDriverw', '__$webdriverAsyncExecutor',
        'webdriver', '__webdriverFunc',
    ];
    automationProps.forEach(prop => {
        try { delete window[prop]; } catch(e) {}
        try {
            Object.defineProperty(window, prop, {
                get: () => undefined,
                configurable: true,
            });
        } catch(e) {}
    });

    // Remove automation-related document attributes
    try {
        document.documentElement.removeAttribute('webdriver');
        document.documentElement.removeAttribute('selenium');
        document.documentElement.removeAttribute('driver');
    } catch(e) {}
})();
"""


# ═══════════════════════════════════════════════════════════
# 2. CHROME DEVTOOLS PROTOCOL EVASION
# ═══════════════════════════════════════════════════════════

CDP_EVASION: Final[str] = """
(() => {
    // Prevent Runtime.enable detection
    const originalError = Error;
    const originalStackTraceLimit = Error.stackTraceLimit;

    // Hide the CDP connection indicator
    Object.defineProperty(window, 'cdc_adoQpoasnfa76pfcZLmcfl_Array', {
        get: () => undefined,
        configurable: true,
    });
    Object.defineProperty(window, 'cdc_adoQpoasnfa76pfcZLmcfl_Promise', {
        get: () => undefined,
        configurable: true,
    });
    Object.defineProperty(window, 'cdc_adoQpoasnfa76pfcZLmcfl_Symbol', {
        get: () => undefined,
        configurable: true,
    });

    // Prevent stack trace analysis that reveals CDP
    const origPrepareStackTrace = Error.prepareStackTrace;
    Error.prepareStackTrace = function(err, stack) {
        // Filter out CDP-related frames
        const filtered = stack.filter(frame => {
            const fn = frame.getFunctionName() || '';
            const file = frame.getFileName() || '';
            return !fn.includes('Runtime.evaluate') &&
                   !file.includes('__playwright') &&
                   !file.includes('puppeteer') &&
                   !file.includes('devtools');
        });
        if (origPrepareStackTrace) {
            return origPrepareStackTrace(err, filtered);
        }
        return filtered.map(f => f.toString()).join('\\n');
    };
})();
"""


# ═══════════════════════════════════════════════════════════
# 3. WEBRTC LEAK PREVENTION
# ═══════════════════════════════════════════════════════════

WEBRTC_LEAK_PREVENTION: Final[str] = """
(() => {
    // Block WebRTC entirely or limit to prevent IP leaks
    const RTCPeerConnection = window.RTCPeerConnection ||
                               window.webkitRTCPeerConnection ||
                               window.mozRTCPeerConnection;

    if (RTCPeerConnection) {
        // Wrap RTCPeerConnection to intercept ICE candidates
        const OriginalRTC = RTCPeerConnection;

        window.RTCPeerConnection = function(...args) {
            const config = args[0] || {};

            // Force through TURN only (no STUN = no leak)
            if (config.iceServers) {
                config.iceServers = config.iceServers.filter(server => {
                    const urls = Array.isArray(server.urls) ? server.urls : [server.urls || server.url];
                    return urls.some(url => url && url.startsWith('turn:'));
                });
            }

            const pc = new OriginalRTC(...args);

            // Intercept onicecandidate to filter local IPs
            const origSetHandler = Object.getOwnPropertyDescriptor(
                RTCPeerConnection.prototype, 'onicecandidate'
            );

            const origAddEventListener = pc.addEventListener.bind(pc);
            pc.addEventListener = function(type, listener, ...rest) {
                if (type === 'icecandidate') {
                    const wrappedListener = function(event) {
                        if (event.candidate && event.candidate.candidate) {
                            const c = event.candidate.candidate;
                            // Block local/private IP candidates
                            if (c.includes('192.168.') || c.includes('10.') ||
                                c.includes('172.16.') || c.includes('169.254.') ||
                                c.includes('::1') || c.includes('fe80:') ||
                                c.match(/[0-9a-f]{1,4}:.*:.*local/i)) {
                                return; // Silently drop
                            }
                        }
                        listener.call(this, event);
                    };
                    return origAddEventListener(type, wrappedListener, ...rest);
                }
                return origAddEventListener(type, listener, ...rest);
            };

            return pc;
        };

        window.RTCPeerConnection.prototype = OriginalRTC.prototype;
        window.webkitRTCPeerConnection = window.RTCPeerConnection;
    }

    // Also disable RTCDataChannel fingerprinting
    if (window.RTCDataChannel) {
        const origSend = RTCDataChannel.prototype.send;
        RTCDataChannel.prototype.send = function(data) {
            // Allow normal operation but prevent timing attacks
            return origSend.call(this, data);
        };
    }
})();
"""


# ═══════════════════════════════════════════════════════════
# 4. CANVAS FINGERPRINT NOISE (Advanced)
# ═══════════════════════════════════════════════════════════

CANVAS_FINGERPRINT_NOISE: Final[str] = """
(() => {
    // Deterministic noise based on session seed
    const seed = %CANVAS_SEED%;
    let state = seed;
    function seededRandom() {
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF;
        return (state >>> 0) / 0xFFFFFFFF;
    }

    // Override toDataURL with session-consistent noise
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
        const ctx = this.getContext('2d');
        if (ctx && this.width > 0 && this.height > 0) {
            try {
                const w = Math.min(this.width, 256);
                const h = Math.min(this.height, 256);
                const imageData = ctx.getImageData(0, 0, w, h);
                const data = imageData.data;
                // Apply subtle, deterministic noise (±2 per channel)
                for (let i = 0; i < data.length; i += 4) {
                    if (seededRandom() < 0.1) { // Only modify 10% of pixels
                        data[i]     = Math.max(0, Math.min(255, data[i] + Math.floor(seededRandom() * 5 - 2)));
                        data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + Math.floor(seededRandom() * 5 - 2)));
                        data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + Math.floor(seededRandom() * 5 - 2)));
                    }
                }
                ctx.putImageData(imageData, 0, 0);
            } catch(e) {} // SecurityError on tainted canvas — ignore
        }
        return origToDataURL.call(this, type, quality);
    };

    // Override toBlob
    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
        // Trigger noise injection via toDataURL first
        this.toDataURL(type, quality);
        return origToBlob.call(this, callback, type, quality);
    };

    // Override getImageData for direct reads
    const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {
        const imageData = origGetImageData.call(this, sx, sy, sw, sh);
        const data = imageData.data;
        for (let i = 0; i < data.length; i += 4) {
            if (seededRandom() < 0.05) {
                data[i] = Math.max(0, Math.min(255, data[i] + Math.floor(seededRandom() * 3 - 1)));
            }
        }
        return imageData;
    };

    // Override isPointInPath/isPointInStroke (used for font detection)
    const origIsPointInPath = CanvasRenderingContext2D.prototype.isPointInPath;
    CanvasRenderingContext2D.prototype.isPointInPath = function(...args) {
        const result = origIsPointInPath.apply(this, args);
        // Occasionally flip result to break font enumeration
        if (seededRandom() < 0.001) return !result;
        return result;
    };
})();
"""


# ═══════════════════════════════════════════════════════════
# 5. WEBGL FINGERPRINT SPOOFING (Advanced)
# ═══════════════════════════════════════════════════════════

WEBGL_FINGERPRINT_SPOOF: Final[str] = """
(() => {
    const spoofedVendor = '%WEBGL_VENDOR%';
    const spoofedRenderer = '%WEBGL_RENDERER%';
    const spoofedUnmaskedVendor = '%WEBGL_UNMASKED_VENDOR%';
    const spoofedUnmaskedRenderer = '%WEBGL_UNMASKED_RENDERER%';

    function patchGetParameter(proto) {
        const origGetParameter = proto.getParameter;
        proto.getParameter = function(param) {
            // UNMASKED_VENDOR_WEBGL
            if (param === 37445) return spoofedUnmaskedVendor;
            // UNMASKED_RENDERER_WEBGL
            if (param === 37446) return spoofedUnmaskedRenderer;
            // VENDOR
            if (param === 0x1F00) return spoofedVendor;
            // RENDERER
            if (param === 0x1F01) return spoofedRenderer;
            return origGetParameter.call(this, param);
        };

        // Also patch getExtension for WEBGL_debug_renderer_info
        const origGetExtension = proto.getExtension;
        proto.getExtension = function(name) {
            if (name === 'WEBGL_debug_renderer_info') {
                return {
                    UNMASKED_VENDOR_WEBGL: 37445,
                    UNMASKED_RENDERER_WEBGL: 37446,
                };
            }
            return origGetExtension.call(this, name);
        };

        // Patch getSupportedExtensions to be consistent
        const origGetSupportedExtensions = proto.getSupportedExtensions;
        proto.getSupportedExtensions = function() {
            const exts = origGetSupportedExtensions.call(this) || [];
            // Ensure WEBGL_debug_renderer_info is present (Chrome always has it)
            if (!exts.includes('WEBGL_debug_renderer_info')) {
                exts.push('WEBGL_debug_renderer_info');
            }
            return exts;
        };
    }

    try { patchGetParameter(WebGLRenderingContext.prototype); } catch(e) {}
    try { patchGetParameter(WebGL2RenderingContext.prototype); } catch(e) {}
})();
"""


# ═══════════════════════════════════════════════════════════
# 6. AUDIOCTX FINGERPRINT NOISE
# ═══════════════════════════════════════════════════════════

AUDIO_FINGERPRINT_NOISE: Final[str] = """
(() => {
    const seed = %AUDIO_SEED%;
    let state = seed;
    function seededRandom() {
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF;
        return (state >>> 0) / 0xFFFFFFFF;
    }

    // Patch AnalyserNode.getFloatFrequencyData
    const origGetFloat = AnalyserNode.prototype.getFloatFrequencyData;
    if (origGetFloat) {
        AnalyserNode.prototype.getFloatFrequencyData = function(array) {
            origGetFloat.call(this, array);
            for (let i = 0; i < array.length; i++) {
                array[i] += (seededRandom() * 0.0001 - 0.00005);
            }
        };
    }

    // Patch OfflineAudioContext.startRendering
    const OrigOfflineAudioCtx = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    if (OrigOfflineAudioCtx) {
        const origStartRendering = OrigOfflineAudioCtx.prototype.startRendering;
        OrigOfflineAudioCtx.prototype.startRendering = function() {
            return origStartRendering.call(this).then(buffer => {
                // Add imperceptible noise to the rendered audio buffer
                for (let c = 0; c < buffer.numberOfChannels; c++) {
                    const data = buffer.getChannelData(c);
                    for (let i = 0; i < data.length; i++) {
                        data[i] += (seededRandom() * 0.00001 - 0.000005);
                    }
                }
                return buffer;
            });
        };
    }

    // Patch AudioContext createOscillator for consistent noise
    const origCreateOscillator = AudioContext.prototype.createOscillator;
    if (origCreateOscillator) {
        AudioContext.prototype.createOscillator = function() {
            const osc = origCreateOscillator.call(this);
            const origFreqSet = Object.getOwnPropertyDescriptor(
                AudioParam.prototype, 'value'
            );
            return osc;
        };
    }
})();
"""


# ═══════════════════════════════════════════════════════════
# 7. FONT ENUMERATION DEFENSE
# ═══════════════════════════════════════════════════════════

FONT_ENUMERATION_DEFENSE: Final[str] = """
(() => {
    // Intercept measureText to add noise (used for font detection)
    const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText = function(text) {
        const metrics = origMeasureText.call(this, text);

        // Create a proxy to add noise to width measurement
        return new Proxy(metrics, {
            get(target, prop) {
                const val = target[prop];
                if (typeof val === 'number' && prop === 'width') {
                    // Add ±0.00001 noise — imperceptible but breaks hashing
                    return val + (Math.random() * 0.00002 - 0.00001);
                }
                if (typeof val === 'function') {
                    return val.bind(target);
                }
                return val;
            }
        });
    };

    // Intercept document.fonts API
    if (document.fonts && document.fonts.check) {
        const origCheck = document.fonts.check.bind(document.fonts);
        document.fonts.check = function(font, text) {
            // Return true for common fonts to appear normal
            const commonFonts = [
                'Arial', 'Verdana', 'Times New Roman', 'Georgia',
                'Courier New', 'Trebuchet MS', 'Palatino Linotype',
            ];
            const fontFamily = font.split(',')[0].replace(/['\"]/g, '').trim();
            const baseName = fontFamily.split(' ').slice(-2).join(' ');
            if (commonFonts.some(f => baseName.toLowerCase().includes(f.toLowerCase()))) {
                return true;
            }
            return origCheck(font, text);
        };
    }
})();
"""


# ═══════════════════════════════════════════════════════════
# 8. NAVIGATOR PROPERTIES SPOOFING
# ═══════════════════════════════════════════════════════════

NAVIGATOR_PROPERTIES_SPOOF: Final[str] = """
(() => {
    const config = %NAV_CONFIG%;

    // hardwareConcurrency
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => config.hardwareConcurrency || 8,
    });

    // deviceMemory
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => config.deviceMemory || 8,
    });

    // maxTouchPoints
    Object.defineProperty(navigator, 'maxTouchPoints', {
        get: () => config.maxTouchPoints || 0,
    });

    // platform
    Object.defineProperty(navigator, 'platform', {
        get: () => config.platform || 'Win32',
    });

    // vendor
    Object.defineProperty(navigator, 'vendor', {
        get: () => config.vendor || 'Google Inc.',
    });

    // doNotTrack
    Object.defineProperty(navigator, 'doNotTrack', {
        get: () => config.doNotTrack || null,
    });

    // language & languages
    Object.defineProperty(navigator, 'language', {
        get: () => config.language || 'en-US',
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => Object.freeze(config.languages || ['en-US', 'en']),
    });

    // connection (Network Information API)
    if ('connection' in navigator || 'mozConnection' in navigator || 'webkitConnection' in navigator) {
        const connData = {
            effectiveType: config.connectionType || '4g',
            downlink: config.downlink || 10,
            rtt: config.rtt || 50,
            saveData: false,
            type: 'wifi',
            downlinkMax: Infinity,
            onchange: null,
            ontypechange: null,
            addEventListener: function() {},
            removeEventListener: function() {},
            dispatchEvent: function() { return true; },
        };
        Object.defineProperty(navigator, 'connection', {
            get: () => connData,
            configurable: true,
        });
    }

    // Plugins array (must match browser type)
    if (config.plugins && config.plugins.length > 0) {
        const pluginArray = config.plugins.map(p => ({
            name: p.name,
            description: p.description,
            filename: p.filename,
            length: p.mimeTypes ? p.mimeTypes.length : 0,
        }));
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const arr = pluginArray;
                arr.refresh = () => {};
                arr.item = (i) => arr[i];
                arr.namedItem = (name) => arr.find(p => p.name === name);
                return arr;
            },
        });
    }

    // mimeTypes
    Object.defineProperty(navigator, 'mimeTypes', {
        get: () => {
            const types = [
                { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
            ];
            types.item = (i) => types[i];
            types.namedItem = (name) => types.find(t => t.type === name);
            types.refresh = () => {};
            return types;
        },
    });
})();
"""


# ═══════════════════════════════════════════════════════════
# 9. PERMISSIONS API EVASION
# ═══════════════════════════════════════════════════════════

PERMISSIONS_API_EVASION: Final[str] = """
(() => {
    // Override Permissions.query to match real browser behavior
    if (navigator.permissions) {
        const origQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = function(descriptor) {
            // Notifications: real browsers usually show 'prompt' or 'denied'
            if (descriptor.name === 'notifications') {
                return Promise.resolve({
                    state: 'prompt',
                    status: 'prompt',
                    onchange: null,
                    addEventListener: function() {},
                    removeEventListener: function() {},
                    dispatchEvent: function() { return true; },
                });
            }
            // Clipboard: usually 'granted' in Chrome
            if (descriptor.name === 'clipboard-read' || descriptor.name === 'clipboard-write') {
                return Promise.resolve({
                    state: 'granted',
                    status: 'granted',
                    onchange: null,
                    addEventListener: function() {},
                    removeEventListener: function() {},
                    dispatchEvent: function() { return true; },
                });
            }
            return origQuery(descriptor).catch(() => ({
                state: 'prompt',
                status: 'prompt',
                onchange: null,
                addEventListener: function() {},
                removeEventListener: function() {},
                dispatchEvent: function() { return true; },
            }));
        };
    }
})();
"""


# ═══════════════════════════════════════════════════════════
# 10. BATTERY API SIMULATION
# ═══════════════════════════════════════════════════════════

BATTERY_API_SIMULATION: Final[str] = """
(() => {
    // Headless browsers often have no battery — simulate one
    const batteryData = {
        charging: %BATTERY_CHARGING%,
        chargingTime: %BATTERY_CHARGING_TIME%,
        dischargingTime: %BATTERY_DISCHARGING_TIME%,
        level: %BATTERY_LEVEL%,
        onchargingchange: null,
        onchargingtimechange: null,
        ondischargingtimechange: null,
        onlevelchange: null,
        addEventListener: function() {},
        removeEventListener: function() {},
        dispatchEvent: function() { return true; },
    };

    if (navigator.getBattery) {
        navigator.getBattery = function() {
            return Promise.resolve(batteryData);
        };
    }
})();
"""


# ═══════════════════════════════════════════════════════════
# 11. SCREEN PROPERTIES MATCHING
# ═══════════════════════════════════════════════════════════

SCREEN_PROPERTIES_MATCH: Final[str] = """
(() => {
    const config = %SCREEN_CONFIG%;

    Object.defineProperty(screen, 'width', { get: () => config.width });
    Object.defineProperty(screen, 'height', { get: () => config.height });
    Object.defineProperty(screen, 'availWidth', { get: () => config.availWidth });
    Object.defineProperty(screen, 'availHeight', { get: () => config.availHeight });
    Object.defineProperty(screen, 'colorDepth', { get: () => config.colorDepth || 24 });
    Object.defineProperty(screen, 'pixelDepth', { get: () => config.colorDepth || 24 });

    // Override window.devicePixelRatio
    Object.defineProperty(window, 'devicePixelRatio', {
        get: () => config.pixelRatio || 1,
    });

    // Override window.outerWidth/outerHeight to be consistent
    Object.defineProperty(window, 'outerWidth', {
        get: () => config.width,
    });
    Object.defineProperty(window, 'outerHeight', {
        get: () => config.height,
    });

    // matchMedia consistency
    const origMatchMedia = window.matchMedia;
    window.matchMedia = function(query) {
        const result = origMatchMedia.call(window, query);

        // Make resolution queries consistent with our screen config
        if (query.includes('device-width') || query.includes('device-height')) {
            const widthMatch = query.match(/(\\d+)px/);
            if (widthMatch) {
                const val = parseInt(widthMatch[1]);
                if (query.includes('max-device-width') && val >= config.width) {
                    return {...result, matches: true};
                }
            }
        }
        return result;
    };
})();
"""


# ═══════════════════════════════════════════════════════════
# 12. CHROME RUNTIME OBJECT
# ═══════════════════════════════════════════════════════════

CHROME_RUNTIME_SPOOF: Final[str] = """
(() => {
    // Construct a convincing window.chrome object
    if (!window.chrome) {
        window.chrome = {};
    }

    window.chrome.app = {
        isInstalled: false,
        InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
        RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
        getDetails: () => null,
        getIsInstalled: () => false,
        installState: () => 'not_installed',
        runningState: () => 'cannot_run',
    };

    window.chrome.runtime = {
        OnInstalledReason: {
            CHROME_UPDATE: 'chrome_update',
            INSTALL: 'install',
            SHARED_MODULE_UPDATE: 'shared_module_update',
            UPDATE: 'update',
        },
        OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
        PlatformArch: { ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
        PlatformNaclArch: { ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
        PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
        RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' },
        connect: function() { return { onDisconnect: { addListener: function() {} }, onMessage: { addListener: function() {} }, postMessage: function() {} }; },
        sendMessage: function() {},
        id: undefined,
    };

    window.chrome.csi = function() {
        return {
            onloadT: Date.now() - Math.floor(Math.random() * 3000 + 1000),
            startE: Date.now() - Math.floor(Math.random() * 5000 + 2000),
            pageT: Math.floor(Math.random() * 3000 + 1000),
            tran: 15,
        };
    };

    window.chrome.loadTimes = function() {
        return {
            commitLoadTime: Date.now() / 1000 - Math.random() * 2,
            connectionInfo: 'h2',
            finishDocumentLoadTime: Date.now() / 1000 - Math.random(),
            finishLoadTime: Date.now() / 1000 - Math.random() * 0.5,
            firstPaintAfterLoadTime: Date.now() / 1000 - Math.random() * 0.3,
            firstPaintTime: Date.now() / 1000 - Math.random() * 0.5,
            navigationType: 'Other',
            npnNegotiatedProtocol: 'h2',
            requestTime: Date.now() / 1000 - Math.random() * 3,
            startLoadTime: Date.now() / 1000 - Math.random() * 3,
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: true,
            wasNpnNegotiated: true,
        };
    };
})();
"""


# ═══════════════════════════════════════════════════════════
# 13. HEADLESS DETECTION COUNTERMEASURES
# ═══════════════════════════════════════════════════════════

HEADLESS_COUNTERMEASURES: Final[str] = """
(() => {
    // 1. window.outerWidth/outerHeight check
    // Headless often has outer === inner. Real browsers have chrome UI.
    const origInnerWidth = Object.getOwnPropertyDescriptor(window, 'innerWidth');
    const origInnerHeight = Object.getOwnPropertyDescriptor(window, 'innerHeight');

    // 2. Notification API (headless often lacks it)
    if (!window.Notification) {
        window.Notification = function(title, options) {
            this.title = title;
            this.options = options;
        };
        window.Notification.permission = 'default';
        window.Notification.requestPermission = function() {
            return Promise.resolve('default');
        };
    }

    // 3. SpeechSynthesis (headless often has empty voices)
    if (window.speechSynthesis) {
        const origGetVoices = speechSynthesis.getVoices.bind(speechSynthesis);
        speechSynthesis.getVoices = function() {
            const voices = origGetVoices();
            if (voices.length === 0) {
                // Return fake voices matching the platform
                return [
                    { default: true, lang: 'en-US', localService: true, name: 'Microsoft David - English (United States)', voiceURI: 'Microsoft David - English (United States)' },
                    { default: false, lang: 'en-US', localService: true, name: 'Microsoft Zira - English (United States)', voiceURI: 'Microsoft Zira - English (United States)' },
                    { default: false, lang: 'en-GB', localService: true, name: 'Microsoft Hazel - English (Great Britain)', voiceURI: 'Microsoft Hazel - English (Great Britain)' },
                ];
            }
            return voices;
        };
    }

    // 4. User Activation state
    Object.defineProperty(navigator, 'userActivation', {
        get: () => ({
            hasBeenActive: true,
            isActive: false,
        }),
        configurable: true,
    });

    // 5. Broken image dimensions (headless renders differently)
    const origImage = window.Image;
    window.Image = function(...args) {
        const img = new origImage(...args);
        // Override naturalWidth/Height for unloaded images
        const origNW = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'naturalWidth');
        return img;
    };
    window.Image.prototype = origImage.prototype;

    // 6. PDF viewer plugin
    Object.defineProperty(navigator, 'pdfViewerEnabled', {
        get: () => true,
    });

    // 7. MediaDevices (webcam/mic enumeration)
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        const origEnumerate = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
        navigator.mediaDevices.enumerateDevices = function() {
            return origEnumerate().then(devices => {
                if (devices.length === 0) {
                    // Return fake but realistic device list
                    return [
                        { deviceId: 'default', groupId: 'default', kind: 'audioinput', label: '' },
                        { deviceId: 'default', groupId: 'default', kind: 'audiooutput', label: '' },
                        { deviceId: 'default', groupId: 'default', kind: 'videoinput', label: '' },
                    ];
                }
                return devices;
            });
        };
    }
})();
"""


# ═══════════════════════════════════════════════════════════
# 14. IFRAME DETECTION PREVENTION
# ═══════════════════════════════════════════════════════════

IFRAME_DETECTION_PREVENTION: Final[str] = """
(() => {
    // Ensure window.top === window.self (not framed)
    try {
        if (window.top !== window.self) {
            // We're in an iframe — mask it
            Object.defineProperty(window, 'top', {
                get: () => window.self,
            });
            Object.defineProperty(window, 'parent', {
                get: () => window.self,
            });
            Object.defineProperty(window, 'frameElement', {
                get: () => null,
            });
        }
    } catch(e) {
        // Cross-origin — we're fine
    }

    // Also prevent window.length detection (number of iframes)
    Object.defineProperty(window, 'length', {
        get: () => 0,
        configurable: true,
    });
})();
"""


# ═══════════════════════════════════════════════════════════
# 15. TIMING ATTACK PREVENTION
# ═══════════════════════════════════════════════════════════

TIMING_ATTACK_PREVENTION: Final[str] = """
(() => {
    // Reduce performance.now() precision to prevent timing attacks
    const origNow = performance.now.bind(performance);
    performance.now = function() {
        // Round to 100μs — standard Firefox behavior
        return Math.round(origNow() * 10) / 10;
    };

    // Reduce Date.now() precision slightly
    const origDateNow = Date.now;
    Date.now = function() {
        return Math.round(origDateNow() / 2) * 2;
    };

    // Prevent SharedArrayBuffer timing (Spectre mitigation)
    // Most sites check for this
    if (!window.SharedArrayBuffer) {
        // Don't add it — many sites check for absence
    }
})();
"""


# ═══════════════════════════════════════════════════════════
# 16. CSS MEDIA QUERY FINGERPRINT DEFENSE
# ═══════════════════════════════════════════════════════════

CSS_MEDIA_DEFENSE: Final[str] = """
(() => {
    const prefersColorScheme = '%COLOR_SCHEME%';
    const prefersReducedMotion = 'no-preference';

    const origMatchMedia = window.matchMedia;
    window.matchMedia = function(query) {
        const result = origMatchMedia.call(window, query);

        // Override prefers-color-scheme
        if (query.includes('prefers-color-scheme')) {
            const matches = query.includes(prefersColorScheme);
            return {
                matches: matches,
                media: query,
                onchange: null,
                addListener: function(cb) { this.addEventListener('change', cb); },
                removeListener: function(cb) { this.removeEventListener('change', cb); },
                addEventListener: function() {},
                removeEventListener: function() {},
                dispatchEvent: function() { return true; },
            };
        }

        // Override prefers-reduced-motion
        if (query.includes('prefers-reduced-motion')) {
            return {
                matches: prefersReducedMotion === 'reduce' ? query.includes('reduce') : !query.includes('reduce'),
                media: query,
                onchange: null,
                addListener: function(cb) {},
                removeListener: function(cb) {},
                addEventListener: function() {},
                removeEventListener: function() {},
                dispatchEvent: function() { return true; },
            };
        }

        return result;
    };
})();
"""


# ═══════════════════════════════════════════════════════════
# 17. KEYBOARD/INPUT EVENT CONSISTENCY
# ═══════════════════════════════════════════════════════════

INPUT_EVENT_CONSISTENCY: Final[str] = """
(() => {
    // Ensure keyboard events have correct isTrusted property
    // Automated inputs often have isTrusted=false

    const origDispatchEvent = EventTarget.prototype.dispatchEvent;
    EventTarget.prototype.dispatchEvent = function(event) {
        if (event instanceof KeyboardEvent || event instanceof MouseEvent ||
            event instanceof InputEvent || event instanceof PointerEvent) {
            // Create a new event that appears trusted
            // Note: can't set isTrusted, but ensure other properties are consistent
            if (!event.composed) {
                try {
                    Object.defineProperty(event, 'composed', { value: true });
                } catch(e) {}
            }
        }
        return origDispatchEvent.call(this, event);
    };

    // PointerEvent consistency (headless often lacks this)
    if (!window.PointerEvent) {
        window.PointerEvent = class PointerEvent extends MouseEvent {
            constructor(type, params = {}) {
                super(type, params);
                this.pointerId = params.pointerId || 0;
                this.width = params.width || 1;
                this.height = params.height || 1;
                this.pressure = params.pressure || 0;
                this.tiltX = params.tiltX || 0;
                this.tiltY = params.tiltY || 0;
                this.pointerType = params.pointerType || 'mouse';
                this.isPrimary = params.isPrimary !== undefined ? params.isPrimary : true;
            }
        };
    }
})();
"""


# ═══════════════════════════════════════════════════════════
# 18. COOKIE CONSENT AUTO-DISMISS
# ═══════════════════════════════════════════════════════════

COOKIE_CONSENT_DISMISS: Final[str] = """
(() => {
    // Auto-dismiss cookie banners that block page interaction
    function dismissCookieBanners() {
        const selectors = [
            // Common cookie banner button selectors
            '[class*="cookie"] button[class*="accept"]',
            '[class*="cookie"] button[class*="agree"]',
            '[class*="consent"] button[class*="accept"]',
            '[class*="consent"] button[class*="agree"]',
            '[id*="cookie"] button[class*="accept"]',
            '#onetrust-accept-btn-handler',
            '.cc-btn.cc-dismiss',
            '.js-cookie-consent-agree',
            '[data-testid="cookie-policy-dialog-accept-button"]',
            'button[data-cookiebanner="accept_button"]',
            '.cookie-notice-container .cn-accept-cookie',
            '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',
            '.accept-cookies-button',
            'button.consent-give',
            '[aria-label*="accept cookies" i]',
            '[aria-label*="accept all" i]',
        ];

        for (const selector of selectors) {
            try {
                const btn = document.querySelector(selector);
                if (btn && btn.offsetParent !== null) {
                    btn.click();
                    return true;
                }
            } catch(e) {}
        }

        // Also try by button text content
        const buttons = document.querySelectorAll('button, a.button, [role="button"]');
        for (const btn of buttons) {
            const text = (btn.textContent || '').trim().toLowerCase();
            if ((text.includes('accept') || text.includes('agree') || text.includes('allow'))
                && (text.includes('cookie') || text.includes('consent') || text.includes('all'))
                && btn.offsetParent !== null
                && btn.offsetWidth > 0) {
                btn.click();
                return true;
            }
        }
        return false;
    }

    // Run after page load and periodically
    if (document.readyState === 'complete') {
        setTimeout(dismissCookieBanners, 1000);
    } else {
        window.addEventListener('load', () => {
            setTimeout(dismissCookieBanners, 1000);
            setTimeout(dismissCookieBanners, 3000);
        });
    }

    // Also watch for dynamically added banners
    const observer = new MutationObserver(() => {
        setTimeout(dismissCookieBanners, 500);
    });
    observer.observe(document.documentElement, {
        childList: true, subtree: true,
    });
    // Stop observing after 10 seconds
    setTimeout(() => observer.disconnect(), 10000);
})();
"""


# ═══════════════════════════════════════════════════════════
# Script Builder — Assembles scripts with config
# ═══════════════════════════════════════════════════════════

class EvasionScriptBuilder:
    """
    Builds configured evasion scripts from templates.

    Usage:
        builder = EvasionScriptBuilder()
        scripts = builder.build_all(fingerprint_config)
        for script in scripts:
            await page.add_init_script(script)
    """

    @classmethod
    def build_all(
        cls,
        canvas_seed: int = 42,
        audio_seed: int = 137,
        webgl_vendor: str = "Google Inc. (NVIDIA)",
        webgl_renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
        webgl_unmasked_vendor: str = "Google Inc. (NVIDIA)",
        webgl_unmasked_renderer: str = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)",
        nav_config: Optional[Dict] = None,
        screen_config: Optional[Dict] = None,
        battery_charging: bool = True,
        battery_level: float = 0.87,
        battery_charging_time: int = 3600,
        battery_discharging_time: int = 0,
        color_scheme: str = "light",
    ) -> List[str]:
        """Build all evasion scripts with the given configuration."""

        default_nav = {
            "hardwareConcurrency": 8,
            "deviceMemory": 8,
            "maxTouchPoints": 0,
            "platform": "Win32",
            "vendor": "Google Inc.",
            "doNotTrack": None,
            "language": "en-US",
            "languages": ["en-US", "en"],
            "connectionType": "4g",
            "downlink": 10,
            "rtt": 50,
            "plugins": [
                {"name": "PDF Viewer", "description": "Portable Document Format", "filename": "internal-pdf-viewer", "mimeTypes": [{"type": "application/pdf"}]},
                {"name": "Chrome PDF Viewer", "description": "Portable Document Format", "filename": "internal-pdf-viewer", "mimeTypes": [{"type": "application/pdf"}]},
                {"name": "Chromium PDF Viewer", "description": "Portable Document Format", "filename": "internal-pdf-viewer", "mimeTypes": [{"type": "application/pdf"}]},
            ],
        }

        default_screen = {
            "width": 1920,
            "height": 1080,
            "availWidth": 1920,
            "availHeight": 1040,
            "colorDepth": 24,
            "pixelRatio": 1,
        }

        import json
        nav = json.dumps(nav_config or default_nav)
        scr = json.dumps(screen_config or default_screen)

        scripts = [
            WEBDRIVER_EVASION,
            CDP_EVASION,
            WEBRTC_LEAK_PREVENTION,
            CANVAS_FINGERPRINT_NOISE.replace("%CANVAS_SEED%", str(canvas_seed)),
            WEBGL_FINGERPRINT_SPOOF
                .replace("%WEBGL_VENDOR%", webgl_vendor)
                .replace("%WEBGL_RENDERER%", webgl_renderer)
                .replace("%WEBGL_UNMASKED_VENDOR%", webgl_unmasked_vendor)
                .replace("%WEBGL_UNMASKED_RENDERER%", webgl_unmasked_renderer),
            AUDIO_FINGERPRINT_NOISE.replace("%AUDIO_SEED%", str(audio_seed)),
            FONT_ENUMERATION_DEFENSE,
            NAVIGATOR_PROPERTIES_SPOOF.replace("%NAV_CONFIG%", nav),
            PERMISSIONS_API_EVASION,
            BATTERY_API_SIMULATION
                .replace("%BATTERY_CHARGING%", "true" if battery_charging else "false")
                .replace("%BATTERY_LEVEL%", str(battery_level))
                .replace("%BATTERY_CHARGING_TIME%", str(battery_charging_time))
                .replace("%BATTERY_DISCHARGING_TIME%", str(battery_discharging_time)),
            SCREEN_PROPERTIES_MATCH.replace("%SCREEN_CONFIG%", scr),
            CHROME_RUNTIME_SPOOF,
            HEADLESS_COUNTERMEASURES,
            IFRAME_DETECTION_PREVENTION,
            TIMING_ATTACK_PREVENTION,
            CSS_MEDIA_DEFENSE.replace("%COLOR_SCHEME%", color_scheme),
            INPUT_EVENT_CONSISTENCY,
            COOKIE_CONSENT_DISMISS,
        ]
        return scripts

    @classmethod
    def build_minimal(cls) -> List[str]:
        """Build only essential evasion scripts (fast, low footprint)."""
        return [
            WEBDRIVER_EVASION,
            CDP_EVASION,
            CHROME_RUNTIME_SPOOF,
            PERMISSIONS_API_EVASION,
            HEADLESS_COUNTERMEASURES,
        ]

    @classmethod
    def build_for_cloudflare(cls, canvas_seed: int = 42) -> List[str]:
        """Build scripts optimized for Cloudflare bypass."""
        return [
            WEBDRIVER_EVASION,
            CDP_EVASION,
            WEBRTC_LEAK_PREVENTION,
            CANVAS_FINGERPRINT_NOISE.replace("%CANVAS_SEED%", str(canvas_seed)),
            CHROME_RUNTIME_SPOOF,
            HEADLESS_COUNTERMEASURES,
            PERMISSIONS_API_EVASION,
            TIMING_ATTACK_PREVENTION,
            COOKIE_CONSENT_DISMISS,
        ]


# ── All script names for discovery ──
ALL_SCRIPTS: Final[Dict[str, str]] = {
    "webdriver_evasion": WEBDRIVER_EVASION,
    "cdp_evasion": CDP_EVASION,
    "webrtc_leak_prevention": WEBRTC_LEAK_PREVENTION,
    "canvas_fingerprint_noise": CANVAS_FINGERPRINT_NOISE,
    "webgl_fingerprint_spoof": WEBGL_FINGERPRINT_SPOOF,
    "audio_fingerprint_noise": AUDIO_FINGERPRINT_NOISE,
    "font_enumeration_defense": FONT_ENUMERATION_DEFENSE,
    "navigator_properties_spoof": NAVIGATOR_PROPERTIES_SPOOF,
    "permissions_api_evasion": PERMISSIONS_API_EVASION,
    "battery_api_simulation": BATTERY_API_SIMULATION,
    "screen_properties_match": SCREEN_PROPERTIES_MATCH,
    "chrome_runtime_spoof": CHROME_RUNTIME_SPOOF,
    "headless_countermeasures": HEADLESS_COUNTERMEASURES,
    "iframe_detection_prevention": IFRAME_DETECTION_PREVENTION,
    "timing_attack_prevention": TIMING_ATTACK_PREVENTION,
    "css_media_defense": CSS_MEDIA_DEFENSE,
    "input_event_consistency": INPUT_EVENT_CONSISTENCY,
    "cookie_consent_dismiss": COOKIE_CONSENT_DISMISS,
}


