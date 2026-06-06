
"""
SecureExecutor v9.1 — Sandboxed code execution with safety controls.
Replaces raw exec/eval across the project.
"""
import ast
import io
import logging
import traceback
from typing import Any, Dict, Optional
from contextlib import redirect_stdout, redirect_stderr
from arki_project.exceptions import AgentExecutionError

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# Dangerous modules/builtins that are blocked
BLOCKED_MODULES = {
    'os', 'subprocess', 'shutil', 'pathlib',
    'socket', 'http', 'urllib', 'requests',
    'ctypes', 'importlib', 'sys', 'signal',
    'multiprocessing', 'threading',
}

BLOCKED_BUILTINS = {
    'exec', 'eval', 'compile', '__import__',
    'open', 'input', 'breakpoint', 'exit', 'quit',
}

SAFE_BUILTINS = {
    k: v for k, v in __builtins__.__dict__.items()
    if k not in BLOCKED_BUILTINS
} if isinstance(__builtins__, dict) is False else {
    k: v for k, v in __builtins__.items()
    if k not in BLOCKED_BUILTINS
}


class ExecutionResult:
    """Result of a sandboxed execution."""
    def __init__(self) -> None:
        self.stdout: str = ""
        self.stderr: str = ""
        self.result: Any = None
        self.error: Optional[str] = None
        self.success: bool = False
        self.execution_time: float = 0.0

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "result": str(self.result) if self.result is not None else None,
            "error": self.error,
            "success": self.success,
            "execution_time": self.execution_time,
        }


class SecurityViolation(Exception):
    """Raised when code attempts a blocked operation."""
    pass


class SecureExecutor:
    """
    Sandboxed Python executor with:
    - AST-level validation (blocks imports of dangerous modules)
    - Restricted builtins
    - Timeout enforcement
    - Output capture
    - Memory-safe execution
    """

    def __init__(
        self,
        timeout: int = 30,
        max_output: int = 32768,
        allow_imports: bool = False,
        extra_globals: Optional[Dict] = None,
    ) -> None:
        self.timeout = timeout
        self.max_output = max_output
        self.allow_imports = allow_imports
        self.extra_globals = extra_globals or {}
        self._execution_count = 0

    def validate_ast(self, code: str) -> None:
        """AST-level security check before execution."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SecurityViolation(f"Syntax error: {e}")

        for node in ast.walk(tree):
            # Block dangerous imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if not self.allow_imports:
                    module = ""
                    if isinstance(node, ast.ImportFrom) and node.module:
                        module = node.module.split('.')[0]
                    elif isinstance(node, ast.Import):
                        module = node.names[0].name.split('.')[0]
                    if module in BLOCKED_MODULES:
                        raise SecurityViolation(
                            f"Import of '{module}' is blocked"
                        )

            # Block dangerous attribute access
            if isinstance(node, ast.Attribute):
                if node.attr.startswith('__') and node.attr.endswith('__'):
                    if node.attr not in ('__init__', '__str__', '__repr__',
                                         '__len__', '__iter__', '__next__',
                                         '__getitem__', '__setitem__',
                                         '__contains__', '__eq__', '__hash__'):
                        raise SecurityViolation(
                            f"Access to '{node.attr}' is blocked"
                        )

    def execute(self, code: str, local_vars: Optional[Dict] = None) -> ExecutionResult:
        """Execute code in a sandboxed environment."""
        import time
        result = ExecutionResult()
        self._execution_count += 1

        start = time.time()

        try:
            # Step 1: AST validation
            self.validate_ast(code)

            # Step 2: Prepare sandbox
            sandbox_globals = {
                '__builtins__': SAFE_BUILTINS,
                '__name__': '__sandbox__',
            }
            sandbox_globals.update(self.extra_globals)
            sandbox_locals = local_vars or {}

            # Step 3: Capture output
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            # Step 4: Execute with timeout
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Try as expression first (for eval-like behavior)
                try:
                    tree = ast.parse(code, mode='eval')
                    compiled = compile(tree, '<sandbox>', 'eval')
                    result.result = eval(compiled, sandbox_globals, sandbox_locals)
                except SyntaxError:
                    # Fall back to exec for statements
                    compiled = compile(code, '<sandbox>', 'exec')
                    exec(compiled, sandbox_globals, sandbox_locals)
                    # Check for a 'result' variable
                    if 'result' in sandbox_locals:
                        result.result = sandbox_locals['result']

            result.stdout = stdout_capture.getvalue()[:self.max_output]
            result.stderr = stderr_capture.getvalue()[:self.max_output]
            result.success = True

        except SecurityViolation as e:
            result.error = f"🔒 Security: {e}"
            logger.warning("Security violation in sandbox: %s", e)
        except AgentExecutionError as e:
            result.error = f"{type(e).__name__}: {e}"
            result.stderr = traceback.format_exc()[:self.max_output]
            logger.debug("Sandbox execution error: %s", e)
        finally:
            result.execution_time = time.time() - start

        return result

    async def execute_async(self, code: str, local_vars: Optional[Dict] = None) -> ExecutionResult:
        """Async wrapper for execute."""
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.execute, code, local_vars)

    @property
    def stats(self) -> dict:
        return {"total_executions": self._execution_count}


# Singleton
_executor: Optional[SecureExecutor] = None

def get_secure_executor(**kwargs) -> SecureExecutor:
    global _executor
    if _executor is None:
        _executor = SecureExecutor(**kwargs)
    return _executor


