
"""
terminal_emulator_pkg/python_executor.py — PythonExecutor
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PythonExecutor:
    """Execute Python code in a sandboxed environment."""

    def __init__(self, sandbox: SecuritySandbox) -> None:
        self.sandbox = sandbox
        self.persistent_globals: Dict[str, Any] = {}

    def execute(self, code: str,
                variables: Optional[Dict[str, Any]] = None) -> Tuple[str, str, int]:
        """
        Execute Python code.

        Returns: (stdout, stderr, exit_code)
        """
        # Security check
        issues = self.sandbox.check_code(code)
        if issues:
            return "", f"Security: {'; '.join(issues)}", 1

        # Set up execution environment
        safe_globals = self.sandbox.get_safe_globals()
        safe_globals.update(self.persistent_globals)
        if variables:
            safe_globals.update(variables)

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, safe_globals)

            # Update persistent state
            for key, val in safe_globals.items():
                if not key.startswith("_"):
                    self.persistent_globals[key] = val

            stdout = self.sandbox.truncate_output(stdout_capture.getvalue())
            stderr = stderr_capture.getvalue()
            return stdout, stderr, 0

        except Exception as e:
            stderr = f"{type(e).__name__}: {str(e)}\n"
            stderr += traceback.format_exc()
            return stdout_capture.getvalue(), stderr, 1


# ═══════════════════════════════════════════════════════════════════
# Bash Executor (Simulated)
# ═══════════════════════════════════════════════════════════════════



