
"""
terminal_emulator_pkg/terminal_emulator.py — TerminalEmulator
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class TerminalEmulator:
    """
    Multi-language terminal emulator with sandboxed execution.

    The main interface for code execution, filesystem ops, and
    session management.
    """

    def __init__(self, sandbox: Optional[SecuritySandbox] = None) -> None:
        self.sandbox = sandbox or SecuritySandbox()
        self.fs = VirtualFS()
        self.sessions: Dict[str, TerminalSession] = {}
        self.history = CommandHistory()
        self.process_manager = ProcessManager()
        self.python_executor = PythonExecutor(self.sandbox)
        self.bash_executor = BashExecutor(self.fs)
        self.audit_log: List[Dict[str, Any]] = []

        # Create default session
        self._current_session_id: Optional[str] = None

    def create_session(self, language: Language = Language.AUTO) -> str:
        """Create a new terminal session."""
        session = TerminalSession(language=language)
        self.sessions[session.id] = session
        self._current_session_id = session.id
        self._audit("session_create", {"session_id": session.id})
        return session.id

    def get_session(self, session_id: Optional[str] = None) -> TerminalSession:
        """Get a session (current or by ID)."""
        sid = session_id or self._current_session_id
        if not sid or sid not in self.sessions:
            # Auto-create
            sid = self.create_session()
        return self.sessions[sid]

    def execute(self, command: str,
                language: Optional[Language] = None,
                session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a command in the terminal.

        Auto-detects language if not specified.
        Returns dict with stdout, stderr, exit_code, duration_ms.
        """
        session = self.get_session(session_id)
        session.last_activity = time.time()

        # Resolve aliases
        command = self._resolve_aliases(command, session)

        # Detect language
        lang = language or self._detect_language(command)

        # Spawn process
        pid = self.process_manager.spawn(command, lang)
        start = time.time()

        try:
            if lang == Language.PYTHON:
                stdout, stderr, code = self.python_executor.execute(command)
            elif lang == Language.BASH:
                stdout, stderr, code = self.bash_executor.execute(command)
            else:
                # Auto: try bash first, then python
                stdout, stderr, code = self.bash_executor.execute(command)
                if code == 127:  # command not found
                    stdout, stderr, code = self.python_executor.execute(command)

            duration = (time.time() - start) * 1000
            self.process_manager.complete(pid, stdout, code)

        except Exception as e:
            duration = (time.time() - start) * 1000
            stdout = ""
            stderr = str(e)
            code = 1
            self.process_manager.fail(pid, stderr)

        # Record in history
        entry = CommandEntry(
            command=command,
            language=lang,
            output=stdout,
            error=stderr,
            exit_code=code,
            duration_ms=duration,
        )
        self.history.add(entry)
        self._audit("execute", {
            "command": command[:200],
            "language": lang.value,
            "exit_code": code,
            "duration_ms": round(duration, 2),
        })

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": code,
            "duration_ms": round(duration, 2),
            "pid": pid,
            "language": lang.value,
        }

    def _detect_language(self, command: str) -> Language:
        """Auto-detect command language."""
        command = command.strip()

        # Bash indicators
        bash_patterns = [
            r"^(ls|cd|pwd|cat|mkdir|rm|cp|mv|echo|grep|find|tree|touch|wc|head|tail|env|export|du|uname|whoami|date|clear|history)",
            r"^\$",
            r"\|",
            r"^#!",
        ]
        for pattern in bash_patterns:
            if re.match(pattern, command):
                return Language.BASH

        # Python indicators
        python_patterns = [
            r"^(import |from |def |class |print\(|if |for |while |try:|with )",
            r"^\w+\s*=\s*",
            r"^\w+\(",
        ]
        for pattern in python_patterns:
            if re.match(pattern, command):
                return Language.PYTHON

        return Language.BASH

    def _resolve_aliases(self, command: str, session: TerminalSession) -> str:
        """Resolve command aliases."""
        parts = command.strip().split(None, 1)
        if parts and parts[0] in session.aliases:
            alias_val = session.aliases[parts[0]]
            rest = parts[1] if len(parts) > 1 else ""
            return f"{alias_val} {rest}".strip()
        return command

    def set_alias(self, name: str, command: str,
                  session_id: Optional[str] = None) -> None:
        """Set a command alias."""
        session = self.get_session(session_id)
        session.aliases[name] = command

    # ─── Session Management ───────────────────────────────────────

    def snapshot_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Snapshot session state for persistence."""
        session = self.get_session(session_id)
        return {
            "id": session.id,
            "language": session.language.value,
            "cwd": session.cwd,
            "env": session.env,
            "aliases": session.aliases,
            "created_at": session.created_at,
            "filesystem": self.fs.to_dict(),
            "history": [
                {
                    "command": e.command,
                    "language": e.language.value,
                    "exit_code": e.exit_code,
                    "timestamp": e.timestamp,
                }
                for e in self.history.entries[-100:]
            ],
        }

    def restore_session(self, snapshot: Dict[str, Any]) -> str:
        """Restore session from snapshot."""
        session = TerminalSession(
            id=snapshot["id"],
            language=Language(snapshot["language"]),
            cwd=snapshot.get("cwd", "/home"),
            env=snapshot.get("env", {}),
            aliases=snapshot.get("aliases", {}),
            created_at=snapshot.get("created_at", time.time()),
        )
        self.sessions[session.id] = session
        self._current_session_id = session.id

        if "filesystem" in snapshot:
            self.fs = VirtualFS.from_dict(snapshot["filesystem"])
            self.bash_executor = BashExecutor(self.fs)

        return session.id

    def list_sessions(self) -> List[Dict[str, str]]:
        """List all sessions."""
        return [
            {
                "id": s.id,
                "language": s.language.value,
                "created": time.strftime("%H:%M:%S", time.localtime(s.created_at)),
                "active": s.id == self._current_session_id,
            }
            for s in self.sessions.values()
        ]

    def _audit(self, action: str, data: Dict[str, Any]) -> None:
        """Add audit log entry."""
        self.audit_log.append({
            "timestamp": time.time(),
            "action": action,
            **data,
        })



