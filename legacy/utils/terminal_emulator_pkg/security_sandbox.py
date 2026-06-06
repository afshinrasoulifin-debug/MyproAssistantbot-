
"""
terminal_emulator_pkg/security_sandbox.py — SecuritySandbox
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class SecuritySandbox:
    """
    Security constraints for code execution.

    Enforces timeouts, memory limits, and import restrictions.
    """

    # Dangerous modules to block
    BLOCKED_IMPORTS: Set[str] = {
        "subprocess", "shutil", "ctypes", "importlib",
        "signal", "resource", "pty", "fcntl",
        "multiprocessing", "threading",
    }

    # Dangerous builtins to mask
    BLOCKED_BUILTINS: Set[str] = {
        "exec", "eval", "compile", "__import__",
        "open", "input", "breakpoint",
    }

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_output_lines: int = 1000,
        max_output_bytes: int = 100_000,
        max_memory_mb: int = 256,
    ) -> None:
        self.timeout = timeout_seconds
        self.max_output_lines = max_output_lines
        self.max_output_bytes = max_output_bytes
        self.max_memory_mb = max_memory_mb

    def check_code(self, code: str) -> List[str]:
        """Check code for security violations. Returns list of issues."""
        issues: List[str] = []

        for module in self.BLOCKED_IMPORTS:
            if re.search(rf"\bimport\s+{module}\b", code):
                issues.append(f"Blocked import: {module}")
            if re.search(rf"\bfrom\s+{module}\b", code):
                issues.append(f"Blocked import: from {module}")

        if "os.system" in code:
            issues.append("Blocked: os.system()")
        if "os.popen" in code:
            issues.append("Blocked: os.popen()")

        return issues

    def get_safe_globals(self) -> Dict[str, Any]:
        """Get safe globals dict for execution."""
        safe_builtins = {
            k: v for k, v in __builtins__.__dict__.items()
            if k not in self.BLOCKED_BUILTINS
        } if hasattr(__builtins__, '__dict__') else {}

        return {
            "__builtins__": safe_builtins,
            "print": print,
            "len": len,
            "range": range,
            "int": int,
            "float": float,
            "str": str,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "bool": bool,
            "abs": abs,
            "max": max,
            "min": min,
            "sum": sum,
            "sorted": sorted,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "type": type,
            "isinstance": isinstance,
            "math": __import__("math"),
            "json": __import__("json"),
            "re": __import__("re"),
            "time": __import__("time"),
            "random": __import__("random"),
            "datetime": __import__("datetime"),
            "collections": __import__("collections"),
        }

    def truncate_output(self, output: str) -> str:
        """Truncate output to limits."""
        lines = output.split("\n")
        if len(lines) > self.max_output_lines:
            lines = lines[:self.max_output_lines]
            lines.append(f"... (truncated, {self.max_output_lines} line limit)")

        result = "\n".join(lines)
        if len(result) > self.max_output_bytes:
            result = result[:self.max_output_bytes]
            result += f"\n... (truncated, {self.max_output_bytes} byte limit)"

        return result


# ═══════════════════════════════════════════════════════════════════
# Python Executor
# ═══════════════════════════════════════════════════════════════════



