
from __future__ import annotations
"""
tg_bot/utils/code_interpreter.py — Safe Code Interpreter v9.4
Execute user code in a restricted sandbox environment.
"""
import asyncio
import logging
import tempfile
import os
from dataclasses import dataclass
from typing import Optional

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

ALLOWED_IMPORTS = {
    "math", "random", "datetime", "json", "re", "collections",
    "itertools", "functools", "string", "hashlib", "base64",
    "statistics", "fractions", "decimal", "textwrap",
}

BLOCKED_PATTERNS = [
    "import os", "import sys", "import subprocess",
    "import shutil", "import pathlib",
    "__import__", "eval(", "exec(",
    "open(", "file(", "compile(",
    "getattr(", "setattr(", "delattr(",
    "globals(", "locals(",
    "import socket", "import http",
    "import urllib", "import requests",
]


@dataclass
class CodeResult:
    output: str = ""
    error: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0.0
    truncated: bool = False


class CodeInterpreter:
    """Safe code execution sandbox."""

    def __init__(self, timeout: float = 10.0, max_output: int = 4000) -> None:
        self.timeout = timeout
        self.max_output = max_output

    def validate_code(self, code: str) -> Optional[str]:
        """Check code for dangerous patterns. Returns error message or None."""
        for pattern in BLOCKED_PATTERNS:
            if pattern in code:
                return f"❌ عملیات غیرمجاز: `{pattern}`"
        return None

    async def execute(self, code: str, language: str = "python") -> CodeResult:
        """Execute code in sandbox."""
        # Validate
        if language == "python":
            error = self.validate_code(code)
            if error:
                return CodeResult(error=error, exit_code=1)

        # Create temp file
        suffix = ".py" if language == "python" else ".js"
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            cmd = ["python3", temp_path] if language == "python" else ["node", temp_path]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/tmp",
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return CodeResult(
                    error="⏱ اجرای کد بیش از حد طول کشید",
                    exit_code=-1,
                    execution_time_ms=self.timeout * 1000,
                )

            output = stdout.decode('utf-8', errors='replace')
            error = stderr.decode('utf-8', errors='replace')

            truncated = False
            if len(output) > self.max_output:
                output = output[:self.max_output] + "\n... (truncated)"
                truncated = True

            return CodeResult(
                output=output,
                error=error,
                exit_code=proc.returncode or 0,
                truncated=truncated,
            )
        finally:
            os.unlink(temp_path)


_interpreter: Optional[CodeInterpreter] = None

def get_code_interpreter() -> CodeInterpreter:
    global _interpreter
    if _interpreter is None:
        _interpreter = CodeInterpreter()
    return _interpreter


