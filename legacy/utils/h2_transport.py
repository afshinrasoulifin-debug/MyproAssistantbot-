
from __future__ import annotations
"""
utils/h2_transport.py — HTTP/2 Transport Fingerprint Engine v1.0-TITAN
══════════════════════════════════════════════════════════════════════════
Real HTTP/2 SETTINGS frame, WINDOW_UPDATE, pseudo-header ordering,
and PRIORITY frame emulation to match specific browser fingerprints.

Problem: HTTP/2 negotiation reveals browser identity through:
- SETTINGS frame parameter order and values
- WINDOW_UPDATE size
- Pseudo-header (:method, :authority, :path, :scheme) ordering
- PRIORITY/PRIORITY_UPDATE frame behavior
- Header compression (HPACK) table size

Solution: This module provides HTTP/2 transport profiles that can be
applied to httpx, aiohttp, or hyper sessions to match real browsers.

Author: Arki Engine TITAN
License: Proprietary
"""


import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Final, List, Tuple

logger = logging.getLogger("arki.h2_transport")


# ═══════════════════════════════════════════════════════════
# HTTP/2 Constants
# ═══════════════════════════════════════════════════════════

class H2Setting(Enum):
    """HTTP/2 SETTINGS frame parameter IDs."""
    HEADER_TABLE_SIZE = 1          # SETTINGS_HEADER_TABLE_SIZE
    ENABLE_PUSH = 2                # SETTINGS_ENABLE_PUSH
    MAX_CONCURRENT_STREAMS = 3     # SETTINGS_MAX_CONCURRENT_STREAMS
    INITIAL_WINDOW_SIZE = 4        # SETTINGS_INITIAL_WINDOW_SIZE
    MAX_FRAME_SIZE = 5             # SETTINGS_MAX_FRAME_SIZE
    MAX_HEADER_LIST_SIZE = 6       # SETTINGS_MAX_HEADER_LIST_SIZE
    ENABLE_CONNECT_PROTOCOL = 8    # RFC 8441


class H2FrameType(Enum):
    """HTTP/2 frame types."""
    DATA = 0
    HEADERS = 1
    PRIORITY = 2
    RST_STREAM = 3
    SETTINGS = 4
    PUSH_PROMISE = 5
    PING = 6
    GOAWAY = 7
    WINDOW_UPDATE = 8
    CONTINUATION = 9
    PRIORITY_UPDATE = 16   # RFC 9218


# ═══════════════════════════════════════════════════════════
# HTTP/2 Transport Profiles
# ═══════════════════════════════════════════════════════════

@dataclass
class H2TransportProfile:
    """Complete HTTP/2 transport fingerprint for a specific browser."""
    name: str
    browser: str
    version: str

    # SETTINGS frame (parameter_id → value, ORDER matters!)
    settings_order: List[Tuple[int, int]] = field(default_factory=list)

    # WINDOW_UPDATE for connection-level flow control
    connection_window_update: int = 0

    # Pseudo-header order in HEADERS frame
    pseudo_header_order: List[str] = field(default_factory=list)

    # Standard header order (non-pseudo)
    header_order: List[str] = field(default_factory=list)

    # PRIORITY behavior
    uses_priority_frames: bool = False
    uses_priority_update: bool = False  # RFC 9218 (newer browsers)

    # Stream priorities (stream_id → (dependency, weight, exclusive))
    initial_priorities: Dict[int, Tuple[int, int, bool]] = field(default_factory=dict)

    # HPACK dynamic table size
    hpack_table_size: int = 4096  # default

    # Max concurrent streams preference
    max_concurrent_streams: int = 100

    # Connection preface behavior
    send_magic_preface: bool = True  # PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n


# ── Chrome 125 ──
CHROME_125_H2 = H2TransportProfile(
    name="chrome_125",
    browser="chrome",
    version="125",
    settings_order=[
        (H2Setting.HEADER_TABLE_SIZE.value, 65536),
        (H2Setting.ENABLE_PUSH.value, 0),               # Chrome disables push
        (H2Setting.MAX_CONCURRENT_STREAMS.value, 1000),
        (H2Setting.INITIAL_WINDOW_SIZE.value, 6291456),
        (H2Setting.MAX_HEADER_LIST_SIZE.value, 262144),
    ],
    connection_window_update=15663105,
    pseudo_header_order=[":method", ":authority", ":scheme", ":path"],
    header_order=[
        "host", "connection", "content-length", "sec-ch-ua",
        "sec-ch-ua-mobile", "sec-ch-ua-platform", "upgrade-insecure-requests",
        "user-agent", "accept", "sec-fetch-site", "sec-fetch-mode",
        "sec-fetch-user", "sec-fetch-dest", "referer",
        "accept-encoding", "accept-language", "cookie",
    ],
    uses_priority_frames=False,       # Chrome dropped PRIORITY
    uses_priority_update=True,        # Uses PRIORITY_UPDATE (RFC 9218)
    hpack_table_size=65536,
    max_concurrent_streams=1000,
)

# ── Firefox 126 ──
FIREFOX_126_H2 = H2TransportProfile(
    name="firefox_126",
    browser="firefox",
    version="126",
    settings_order=[
        (H2Setting.HEADER_TABLE_SIZE.value, 65536),
        (H2Setting.INITIAL_WINDOW_SIZE.value, 131072),
        (H2Setting.MAX_FRAME_SIZE.value, 16384),
    ],
    connection_window_update=12517377,
    pseudo_header_order=[":method", ":path", ":authority", ":scheme"],
    header_order=[
        "user-agent", "accept", "accept-language", "accept-encoding",
        "referer", "content-type", "content-length", "origin",
        "connection", "cookie", "upgrade-insecure-requests",
        "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site",
        "sec-fetch-user", "priority", "te",
    ],
    uses_priority_frames=False,        # Firefox dropped PRIORITY in 126
    uses_priority_update=True,
    hpack_table_size=65536,
    max_concurrent_streams=100,
)

# ── Safari 17.5 ──
SAFARI_17_H2 = H2TransportProfile(
    name="safari_17",
    browser="safari",
    version="17.5",
    settings_order=[
        (H2Setting.HEADER_TABLE_SIZE.value, 4096),
        (H2Setting.ENABLE_PUSH.value, 0),
        (H2Setting.MAX_CONCURRENT_STREAMS.value, 100),
        (H2Setting.INITIAL_WINDOW_SIZE.value, 2097152),
        (H2Setting.MAX_FRAME_SIZE.value, 16384),
        (H2Setting.MAX_HEADER_LIST_SIZE.value, 0),      # Unlimited
        (H2Setting.ENABLE_CONNECT_PROTOCOL.value, 1),
    ],
    connection_window_update=10485760,
    pseudo_header_order=[":method", ":scheme", ":path", ":authority"],
    header_order=[
        "accept", "sec-fetch-site", "cookie", "sec-fetch-dest",
        "sec-fetch-mode", "sec-fetch-user", "accept-language",
        "upgrade-insecure-requests", "user-agent", "accept-encoding",
        "referer",
    ],
    uses_priority_frames=True,         # Safari still uses PRIORITY
    uses_priority_update=False,
    initial_priorities={
        # Safari creates background priority groups
        3: (0, 200, False),   # Urgent
        5: (0, 100, False),   # High
        7: (0, 0, False),     # Normal
        9: (3, 0, False),     # Low
        11: (3, 0, False),    # Background
    },
    hpack_table_size=4096,
    max_concurrent_streams=100,
)

# ── Edge 125 (Chromium-based, same as Chrome) ──
EDGE_125_H2 = H2TransportProfile(
    name="edge_125",
    browser="edge",
    version="125",
    settings_order=CHROME_125_H2.settings_order.copy(),
    connection_window_update=CHROME_125_H2.connection_window_update,
    pseudo_header_order=CHROME_125_H2.pseudo_header_order.copy(),
    header_order=CHROME_125_H2.header_order.copy(),
    uses_priority_frames=False,
    uses_priority_update=True,
    hpack_table_size=65536,
    max_concurrent_streams=1000,
)

# Profile registry
ALL_H2_PROFILES: Final[Dict[str, H2TransportProfile]] = {
    "chrome_125": CHROME_125_H2,
    "firefox_126": FIREFOX_126_H2,
    "safari_17": SAFARI_17_H2,
    "edge_125": EDGE_125_H2,
}


# ═══════════════════════════════════════════════════════════
# HTTP/2 Header Orderer
# ═══════════════════════════════════════════════════════════

class H2HeaderOrderer:
    """
    Reorder HTTP headers to match a browser's known order.

    Why: HTTP/2 header compression (HPACK) uses indexed references.
    The ORDER of headers in the first request of a connection creates
    a unique fingerprint. Wrong order → instant detection.
    """

    @staticmethod
    def order_headers(
        headers: Dict[str, str],
        profile: H2TransportProfile,
    ) -> List[Tuple[str, str]]:
        """Reorder headers to match the browser profile."""
        ordered: List[Tuple[str, str]] = []
        remaining = dict(headers)

        # First: add headers in profile order
        for key in profile.header_order:
            key_lower = key.lower()
            for actual_key in list(remaining.keys()):
                if actual_key.lower() == key_lower:
                    ordered.append((actual_key, remaining.pop(actual_key)))
                    break

        # Then: add any remaining headers not in profile order
        for key, value in remaining.items():
            ordered.append((key, value))

        return ordered

    @staticmethod
    def order_pseudo_headers(
        method: str,
        authority: str,
        scheme: str,
        path: str,
        profile: H2TransportProfile,
    ) -> List[Tuple[str, str]]:
        """Order pseudo-headers according to browser profile."""
        pseudo_map = {
            ":method": method,
            ":authority": authority,
            ":scheme": scheme,
            ":path": path,
        }
        return [(k, pseudo_map[k]) for k in profile.pseudo_header_order]


# ═══════════════════════════════════════════════════════════
# HTTP/2 Settings Frame Builder
# ═══════════════════════════════════════════════════════════

class H2SettingsBuilder:
    """
    Build HTTP/2 SETTINGS frames that match browser fingerprints.

    The settings frame is sent immediately after the connection preface.
    The ORDER of settings and their VALUES form a fingerprint.
    """

    @staticmethod
    def build_settings_payload(profile: H2TransportProfile) -> bytes:
        """
        Build raw SETTINGS frame payload.

        Each setting is 6 bytes: 2 bytes ID + 4 bytes value.
        """
        import struct
        payload = b""
        for setting_id, value in profile.settings_order:
            payload += struct.pack("!HI", setting_id, value)
        return payload

    @staticmethod
    def build_window_update_payload(profile: H2TransportProfile) -> bytes:
        """Build WINDOW_UPDATE frame payload for stream 0 (connection-level)."""
        import struct
        if profile.connection_window_update > 0:
            return struct.pack("!I", profile.connection_window_update)
        return b""

    @staticmethod
    def get_settings_dict(profile: H2TransportProfile) -> Dict[int, int]:
        """Get settings as dict for hyper/h2 library configuration."""
        return dict(profile.settings_order)

    @staticmethod
    def build_priority_frames(profile: H2TransportProfile) -> List[bytes]:
        """Build PRIORITY frames for Safari-like browsers."""
        import struct
        frames = []
        if profile.uses_priority_frames and profile.initial_priorities:
            for stream_id, (dep, weight, exclusive) in profile.initial_priorities.items():
                dep_val = dep | (0x80000000 if exclusive else 0)
                payload = struct.pack("!IB", dep_val, weight)
                frames.append((stream_id, payload))
        return frames


# ═══════════════════════════════════════════════════════════
# HTTP/2 Fingerprint Validator
# ═══════════════════════════════════════════════════════════

class H2FingerprintValidator:
    """
    Validate HTTP/2 fingerprint consistency.

    Checks that the HTTP/2 settings and behavior match the claimed browser.
    """

    # Known fingerprint signatures
    BROWSER_SIGNATURES: Final[Dict[str, Dict[str, Any]]] = {
        "chrome": {
            "window_update_range": (15000000, 16000000),
            "initial_window_range": (6000000, 7000000),
            "push_disabled": True,
            "uses_priority": False,
            "header_table_size": 65536,
        },
        "firefox": {
            "window_update_range": (12000000, 13000000),
            "initial_window_range": (100000, 200000),
            "push_disabled": False,
            "uses_priority": False,
            "header_table_size": 65536,
        },
        "safari": {
            "window_update_range": (10000000, 11000000),
            "initial_window_range": (2000000, 3000000),
            "push_disabled": True,
            "uses_priority": True,
            "header_table_size": 4096,
        },
    }

    @classmethod
    def validate(cls, profile: H2TransportProfile) -> List[str]:
        """Validate profile for consistency. Returns list of issues."""
        issues = []
        sig = cls.BROWSER_SIGNATURES.get(profile.browser, {})
        if not sig:
            return issues

        # Window update size
        wu_range = sig.get("window_update_range")
        if wu_range and not (wu_range[0] <= profile.connection_window_update <= wu_range[1]):
            issues.append(
                f"WINDOW_UPDATE {profile.connection_window_update} outside expected "
                f"range {wu_range} for {profile.browser}"
            )

        # PRIORITY usage
        expected_priority = sig.get("uses_priority", False)
        if profile.uses_priority_frames != expected_priority:
            issues.append(
                f"PRIORITY frames {'used' if profile.uses_priority_frames else 'not used'} "
                f"but {profile.browser} {'uses' if expected_priority else 'does not use'} them"
            )

        # Pseudo-header order validation
        if profile.browser == "chrome" and profile.pseudo_header_order != [":method", ":authority", ":scheme", ":path"]:
            issues.append(f"Chrome pseudo-header order wrong: {profile.pseudo_header_order}")
        elif profile.browser == "firefox" and profile.pseudo_header_order != [":method", ":path", ":authority", ":scheme"]:
            issues.append(f"Firefox pseudo-header order wrong: {profile.pseudo_header_order}")
        elif profile.browser == "safari" and profile.pseudo_header_order != [":method", ":scheme", ":path", ":authority"]:
            issues.append(f"Safari pseudo-header order wrong: {profile.pseudo_header_order}")

        return issues

    @classmethod
    def score(cls, profile: H2TransportProfile) -> int:
        """Score profile consistency (0-100)."""
        issues = cls.validate(profile)
        return max(0, 100 - len(issues) * 25)


# ═══════════════════════════════════════════════════════════
# HTTP/2 Connection Preface Builder
# ═══════════════════════════════════════════════════════════

class H2ConnectionPreface:
    """
    Build the complete HTTP/2 connection preface sequence.

    A real browser sends:
    1. Connection preface magic string
    2. SETTINGS frame
    3. WINDOW_UPDATE frame (connection-level)
    4. PRIORITY frames (Safari only)

    The exact bytes and order form a fingerprint.
    """

    # Magic preface: "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
    MAGIC: Final[bytes] = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"

    @classmethod
    def build(cls, profile: H2TransportProfile) -> List[Dict[str, Any]]:
        """
        Build the sequence of frames for connection preface.

        Returns a list of frame descriptors for the HTTP/2 library to send.
        """
        frames = []

        # 1. SETTINGS
        settings = H2SettingsBuilder.get_settings_dict(profile)
        frames.append({
            "type": "SETTINGS",
            "stream_id": 0,
            "settings": settings,
        })

        # 2. WINDOW_UPDATE (connection-level)
        if profile.connection_window_update > 0:
            frames.append({
                "type": "WINDOW_UPDATE",
                "stream_id": 0,
                "increment": profile.connection_window_update,
            })

        # 3. PRIORITY frames (Safari)
        if profile.uses_priority_frames:
            for stream_id, (dep, weight, exclusive) in profile.initial_priorities.items():
                frames.append({
                    "type": "PRIORITY",
                    "stream_id": stream_id,
                    "depends_on": dep,
                    "weight": weight,
                    "exclusive": exclusive,
                })

        return frames

    @classmethod
    def apply_to_h2_connection(cls, h2_conn: Any, profile: H2TransportProfile) -> None:
        """
        Apply profile settings to an h2 library connection object.

        Works with the 'h2' Python library (hyper-h2).
        """
        try:
            import h2.connection
            import h2.config
            import h2.settings

            if not isinstance(h2_conn, h2.connection.H2Connection):
                logger.warning("Not an h2 connection object")
                return

            # Apply settings
            settings_dict = H2SettingsBuilder.get_settings_dict(profile)
            # h2 library maps settings differently
            setting_map = {
                1: h2.settings.SettingCodes.HEADER_TABLE_SIZE,
                2: h2.settings.SettingCodes.ENABLE_PUSH,
                3: h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS,
                4: h2.settings.SettingCodes.INITIAL_WINDOW_SIZE,
                5: h2.settings.SettingCodes.MAX_FRAME_SIZE,
                6: h2.settings.SettingCodes.MAX_HEADER_LIST_SIZE,
            }

            for sid, value in settings_dict.items():
                mapped = setting_map.get(sid)
                if mapped:
                    h2_conn.local_settings[mapped] = value

        except ImportError:
            logger.debug("h2 library not available")
        except Exception as e:
            logger.warning("Failed to apply H2 profile: %s", e)


# ═══════════════════════════════════════════════════════════
# Profile Selector
# ═══════════════════════════════════════════════════════════

class H2ProfileSelector:
    """Select the correct HTTP/2 profile based on browser identity."""

    @staticmethod
    def select(browser: str, version: str = "") -> H2TransportProfile:
        """Select profile by browser name."""
        browser_lower = browser.lower()
        if "chrome" in browser_lower or "edge" in browser_lower:
            return CHROME_125_H2
        elif "firefox" in browser_lower:
            return FIREFOX_126_H2
        elif "safari" in browser_lower:
            return SAFARI_17_H2
        return CHROME_125_H2  # Default

    @staticmethod
    def select_by_ua(user_agent: str) -> H2TransportProfile:
        """Select profile by parsing User-Agent string."""
        ua_lower = user_agent.lower()
        if "firefox" in ua_lower:
            return FIREFOX_126_H2
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            return SAFARI_17_H2
        elif "edg/" in ua_lower:
            return EDGE_125_H2
        return CHROME_125_H2


# Module-level convenience
h2_profile_selector = H2ProfileSelector()


