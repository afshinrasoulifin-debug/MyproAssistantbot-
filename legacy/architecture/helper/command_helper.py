
from __future__ import annotations
"""
architecture.helper.command_helper — CommandHelper, PlatformHelper, RemoteHelper
══════════════════════════════════════════════════════════════════════════════
Command parsing, platform detection, and remote helpers.
Covers: command-helper, platform-helper, remote-helper
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class CommandHelper:
    """Parse and validate bot commands."""
    @staticmethod
    def parse(text: str) -> Tuple[str, List[str]]:
        parts = text.strip().split()
        if not parts:
            return "", []
        cmd = parts[0].lstrip("/").lower()
        args = parts[1:]
        return cmd, args

    @staticmethod
    def validate_args(args: List[str], min_args: int = 0, max_args: int = -1) -> bool:
        if len(args) < min_args:
            return False
        if max_args >= 0 and len(args) > max_args:
            return False
        return True

    @staticmethod
    def extract_options(args: List[str]) -> Tuple[List[str], Dict[str, str]]:
        positional = []
        options = {}
        i = 0
        while i < len(args):
            if args[i].startswith("--"):
                key = args[i][2:]
                val = args[i+1] if i+1 < len(args) and not args[i+1].startswith("--") else "true"
                options[key] = val
                if val != "true":
                    i += 1
            else:
                positional.append(args[i])
            i += 1
        return positional, options

class PlatformHelper:
    """Platform detection and compatibility."""
    @staticmethod
    def detect_platform() -> str:
        import sys
        return sys.platform

    @staticmethod
    def is_linux() -> bool:
        import sys
        return sys.platform.startswith("linux")

    @staticmethod
    def python_version() -> str:
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

class RemoteHelper:
    """Helper for remote API interactions."""
    @staticmethod
    def build_url(base: str, path: str, params: Optional[Dict[str, str]] = None) -> str:
        url = base.rstrip('/') + '/' + path.lstrip('/')
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url += f"?{query}"
        return url

    @staticmethod
    def parse_response(data: Any) -> Dict[str, Any]:
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                import json
                return json.loads(data)
            except Exception:
                return {"raw": data}
        return {"data": data}


