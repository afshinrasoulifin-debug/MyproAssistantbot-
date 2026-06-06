
from __future__ import annotations
"""
architecture.helper.runtime_helper — RuntimeHelper, ShellHelper, SystemHelper
════════════════════════════════════════════════════════════════════════════
Runtime utilities and shell integration helpers.
Covers: runtime-helper, shell-helper, system-helper, helper
"""
import logging, os, platform, time
from typing import Any, Dict

logger = logging.getLogger(__name__)

class RuntimeHelper:
    """Runtime utility functions."""
    @staticmethod
    def system_info() -> Dict[str, Any]:
        return {
            "python": platform.python_version(),
            "os": platform.system(),
            "platform": platform.platform(),
            "pid": os.getpid(),
        }

    @staticmethod
    def memory_usage() -> Dict[str, float]:
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {"max_rss_mb": usage.ru_maxrss / 1024}
        except Exception:
            return {"max_rss_mb": 0}

    @staticmethod
    def uptime_since(start_time: float) -> Dict[str, float]:
        elapsed = time.time() - start_time
        return {"seconds": round(elapsed, 1), "minutes": round(elapsed/60, 2),
                "hours": round(elapsed/3600, 3)}

class ShellHelper:
    """Shell command execution helper."""
    @staticmethod
    async def execute(command: str, timeout: float = 30.0) -> Dict[str, Any]:
        import asyncio
        try:
            # v9.8.7: Use subprocess_exec instead of shell to prevent injection
            proc = await asyncio.create_subprocess_exec(
                "/bin/sh", "-c", command,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {"returncode": proc.returncode,
                    "stdout": stdout.decode().strip(),
                    "stderr": stderr.decode().strip()}
        except asyncio.TimeoutError:
            return {"returncode": -1, "error": "timeout"}
        except Exception as exc:
            return {"returncode": -1, "error": str(exc)}

class SystemHelper:
    """System-level utility functions."""
    @staticmethod
    def env_get(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    @staticmethod
    def file_exists(path: str) -> bool:
        return os.path.exists(path)

    @staticmethod
    def disk_usage(path: str = ".") -> Dict[str, float]:
        try:
            import shutil
            usage = shutil.disk_usage(path)
            return {"total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2)}
        except Exception:
            return {}


