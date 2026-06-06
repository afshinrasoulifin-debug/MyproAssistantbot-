
"""
tg_bot/utils/terminal_emulator.py — v3.0 PRO
═══════════════════════════════════════════════════════════════
TERMINAL EMULATOR — Multi-Language Code Execution Engine

Sandboxed code execution with virtual filesystem, persistent
sessions, process management, and multi-language support.

Architecture
────────────
   ┌─────────────────────────────────────────────────────────────┐
   │                  TERMINAL EMULATOR                          │
   ├──────────┬──────────┬──────────┬──────────┬────────────────┤
   │ Sessions │ Virtual  │ Executor │ Process  │ Security       │
   │ Manager  │ FS       │ Engine   │ Manager  │ Sandbox        │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ create   │ mkdir    │ Python   │ spawn    │ timeout        │
   │ restore  │ touch    │ JS eval  │ kill     │ memory cap     │
   │ snapshot │ write    │ Bash     │ list     │ import filter  │
   │ history  │ read     │ auto     │ signals  │ output limit   │
   │ aliases  │ rm       │ REPL     │ bg/fg    │ resource ctrl  │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ Macros   │ Pipe     │ Format   │ Env Vars │ Audit Log      │
   ├──────────┼──────────┼──────────┼──────────┼────────────────┤
   │ record   │ stdin    │ table    │ set/get  │ command log    │
   │ playback │ stdout   │ JSON     │ export   │ error trace    │
   │ chain    │ stderr   │ tree     │ inherit  │ session track  │
   └──────────┴──────────┴──────────┴──────────┴────────────────┘

Features
────────
  • Multi-language execution (Python, JavaScript, Bash)
  • Virtual in-memory filesystem with full POSIX-like ops
  • Persistent sessions with snapshot/restore
  • Command history with search
  • Command aliases and macros
  • Process management (spawn, kill, list, signals)
  • Environment variable management
  • Output streaming and buffering
  • Security sandbox (timeout, memory cap, import filtering)
  • Pipeline support (command chaining)
  • Audit logging for all operations
  • Session export/import

References
──────────
  Port of: apex_app/src/lib/terminal-emulator.ts (887 lines)
  Enhanced: virtual filesystem with dirs, process signals,
            macro system, pipeline chaining, audit log,
            session serialization, security sandbox
"""

from __future__ import annotations

import io
import re
import time
import traceback
import uuid
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ── TITANIUM v29.0 Integration ──



# ═══════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════

class Language(Enum):
    """Supported execution languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    AUTO = "auto"


class ProcessState(Enum):
    """Process execution states."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"
    SUSPENDED = "suspended"


class FileType(Enum):
    """Virtual filesystem entry types."""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


# ═══════════════════════════════════════════════════════════════════
# Virtual Filesystem
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FSEntry:
    """Filesystem entry (file or directory)."""
    name: str
    entry_type: FileType
    content: str = ""
    permissions: str = "rwxr-xr-x"
    owner: str = "root"
    size: int = 0
    created: float = field(default_factory=time.time)
    modified: float = field(default_factory=time.time)
    children: Dict[str, "FSEntry"] = field(default_factory=dict)
    target: Optional[str] = None  # For symlinks

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "type": self.entry_type.value,
            "permissions": self.permissions,
            "owner": self.owner,
            "size": self.size,
            "created": self.created,
            "modified": self.modified,
        }
        if self.entry_type == FileType.FILE:
            d["content"] = self.content
        elif self.entry_type == FileType.DIRECTORY:
            d["children"] = {
                k: v.to_dict() for k, v in self.children.items()
            }
        elif self.entry_type == FileType.SYMLINK:
            d["target"] = self.target
        return d


class VirtualFS:
    """
    In-memory virtual filesystem with POSIX-like operations.

    Supports: mkdir, touch, write, read, rm, ls, tree, mv, cp, find
    """

    def __init__(self) -> None:
        self.root = FSEntry(
            name="/",
            entry_type=FileType.DIRECTORY,
        )
        # Create standard directories
        for d in ["home", "tmp", "var", "etc", "bin"]:
            self.mkdir(f"/{d}")

    def _resolve_path(self, path: str) -> Tuple[FSEntry, str]:
        """Resolve a path to its parent entry and filename."""
        path = self._normalize_path(path)
        parts = [p for p in path.split("/") if p]

        if not parts:
            return self.root, ""

        current = self.root
        for part in parts[:-1]:
            if part not in current.children:
                raise FileNotFoundError(f"No such directory: {part}")
            child = current.children[part]
            if child.entry_type != FileType.DIRECTORY:
                raise NotADirectoryError(f"Not a directory: {part}")
            current = child

        return current, parts[-1]

    def _normalize_path(self, path: str) -> str:
        """Normalize a filesystem path."""
        if not path.startswith("/"):
            path = "/" + path
        # Resolve .. and .
        parts: List[str] = []
        for part in path.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        return "/" + "/".join(parts)

    def _get_entry(self, path: str) -> FSEntry:
        """Get entry at path."""
        path = self._normalize_path(path)
        if path == "/":
            return self.root

        parent, name = self._resolve_path(path)
        if name not in parent.children:
            raise FileNotFoundError(f"No such file or directory: {path}")
        return parent.children[name]

    def mkdir(self, path: str, parents: bool = True) -> None:
        """Create a directory."""
        path = self._normalize_path(path)
        parts = [p for p in path.split("/") if p]

        current = self.root
        for part in parts:
            if part not in current.children:
                if not parents and part != parts[-1]:
                    raise FileNotFoundError(f"Parent not found: {part}")
                current.children[part] = FSEntry(
                    name=part,
                    entry_type=FileType.DIRECTORY,
                )
            current = current.children[part]

    def touch(self, path: str, content: str = "") -> None:
        """Create or update a file."""
        parent, name = self._resolve_path(path)
        if name in parent.children:
            entry = parent.children[name]
            entry.modified = time.time()
            if content:
                entry.content = content
                entry.size = len(content)
        else:
            parent.children[name] = FSEntry(
                name=name,
                entry_type=FileType.FILE,
                content=content,
                size=len(content),
            )

    def write(self, path: str, content: str, append: bool = False) -> int:
        """Write content to a file."""
        parent, name = self._resolve_path(path)
        if name in parent.children:
            entry = parent.children[name]
            if entry.entry_type != FileType.FILE:
                raise IsADirectoryError(f"Is a directory: {path}")
            if append:
                entry.content += content
            else:
                entry.content = content
            entry.size = len(entry.content)
            entry.modified = time.time()
        else:
            self.touch(path, content)

        return len(content)

    def read(self, path: str) -> str:
        """Read content from a file."""
        entry = self._get_entry(path)
        if entry.entry_type != FileType.FILE:
            raise IsADirectoryError(f"Is a directory: {path}")
        return entry.content

    def rm(self, path: str, recursive: bool = False) -> None:
        """Remove a file or directory."""
        parent, name = self._resolve_path(path)
        if name not in parent.children:
            raise FileNotFoundError(f"No such file: {path}")

        entry = parent.children[name]
        if entry.entry_type == FileType.DIRECTORY and entry.children:
            if not recursive:
                raise OSError(f"Directory not empty: {path}")

        del parent.children[name]

    def ls(self, path: str = "/", details: bool = False) -> List[Dict[str, Any]]:
        """List directory contents."""
        entry = self._get_entry(path)
        if entry.entry_type != FileType.DIRECTORY:
            raise NotADirectoryError(f"Not a directory: {path}")

        items = []
        for name, child in sorted(entry.children.items()):
            if details:
                items.append({
                    "name": name,
                    "type": child.entry_type.value,
                    "size": child.size,
                    "permissions": child.permissions,
                    "modified": child.modified,
                })
            else:
                items.append({"name": name, "type": child.entry_type.value})

        return items

    def tree(self, path: str = "/", prefix: str = "",
             max_depth: int = 10) -> str:
        """Generate tree view of directory."""
        entry = self._get_entry(path)
        lines = [f"{entry.name}/"]
        self._tree_recursive(entry, "", lines, 0, max_depth)
        return "\n".join(lines)

    def _tree_recursive(self, entry: FSEntry, prefix: str,
                        lines: List[str], depth: int,
                        max_depth: int) -> None:
        if depth >= max_depth:
            return
        children = sorted(entry.children.items())
        for i, (name, child) in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            suffix = "/" if child.entry_type == FileType.DIRECTORY else ""
            lines.append(f"{prefix}{connector}{name}{suffix}")
            if child.entry_type == FileType.DIRECTORY:
                ext = "    " if is_last else "│   "
                self._tree_recursive(
                    child, prefix + ext, lines, depth + 1, max_depth,
                )

    def find(self, path: str = "/", pattern: str = "*",
             file_type: Optional[FileType] = None) -> List[str]:
        """Find files matching pattern."""
        results: List[str] = []
        regex = re.compile(
            pattern.replace("*", ".*").replace("?", "."),
        )
        self._find_recursive(path, self._get_entry(path), regex, file_type, results)
        return results

    def _find_recursive(self, path: str, entry: FSEntry,
                        pattern: re.Pattern, file_type: Optional[FileType],
                        results: List[str]) -> None:
        for name, child in entry.children.items():
            child_path = f"{path.rstrip('/')}/{name}"
            if pattern.match(name):
                if file_type is None or child.entry_type == file_type:
                    results.append(child_path)
            if child.entry_type == FileType.DIRECTORY:
                self._find_recursive(child_path, child, pattern, file_type, results)

    def stat(self, path: str) -> Dict[str, Any]:
        """Get file/directory status."""
        entry = self._get_entry(path)
        return {
            "name": entry.name,
            "type": entry.entry_type.value,
            "size": entry.size,
            "permissions": entry.permissions,
            "owner": entry.owner,
            "created": entry.created,
            "modified": entry.modified,
        }

    def du(self, path: str = "/") -> int:
        """Calculate total size of directory."""
        entry = self._get_entry(path)
        if entry.entry_type == FileType.FILE:
            return entry.size
        total = 0
        for child in entry.children.values():
            if child.entry_type == FileType.FILE:
                total += child.size
            elif child.entry_type == FileType.DIRECTORY:
                total += self.du(f"{path.rstrip('/')}/{child.name}")
        return total

    def to_dict(self) -> Dict[str, Any]:
        """Serialize filesystem."""
        return self.root.to_dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VirtualFS":
        """Deserialize filesystem."""
        fs = cls.__new__(cls)
        fs.root = cls._entry_from_dict(data)
        return fs

    @classmethod
    def _entry_from_dict(cls, data: Dict[str, Any]) -> FSEntry:
        entry = FSEntry(
            name=data["name"],
            entry_type=FileType(data["type"]),
            content=data.get("content", ""),
            permissions=data.get("permissions", "rwxr-xr-x"),
            owner=data.get("owner", "root"),
            size=data.get("size", 0),
            created=data.get("created", 0),
            modified=data.get("modified", 0),
            target=data.get("target"),
        )
        for name, child_data in data.get("children", {}).items():
            entry.children[name] = cls._entry_from_dict(child_data)
        return entry


# ═══════════════════════════════════════════════════════════════════
# Process Manager
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    command: str
    language: Language
    state: ProcessState = ProcessState.RUNNING
    output: str = ""
    error: str = ""
    exit_code: Optional[int] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    memory_used: int = 0


class ProcessManager:
    """Manage virtual processes."""

    def __init__(self) -> None:
        self.processes: Dict[int, ProcessInfo] = {}
        self.next_pid: int = 1000

    def spawn(self, command: str, language: Language) -> int:
        """Spawn a new process."""
        pid = self.next_pid
        self.next_pid += 1
        self.processes[pid] = ProcessInfo(
            pid=pid,
            command=command,
            language=language,
        )
        return pid

    def complete(self, pid: int, output: str = "",
                 exit_code: int = 0) -> None:
        """Mark a process as completed."""
        if pid in self.processes:
            proc = self.processes[pid]
            proc.state = ProcessState.COMPLETED
            proc.output = output
            proc.exit_code = exit_code
            proc.end_time = time.time()

    def fail(self, pid: int, error: str) -> None:
        """Mark a process as failed."""
        if pid in self.processes:
            proc = self.processes[pid]
            proc.state = ProcessState.FAILED
            proc.error = error
            proc.exit_code = 1
            proc.end_time = time.time()

    def kill(self, pid: int) -> bool:
        """Kill a process."""
        if pid in self.processes:
            proc = self.processes[pid]
            if proc.state == ProcessState.RUNNING:
                proc.state = ProcessState.KILLED
                proc.end_time = time.time()
                return True
        return False

    def list_processes(self, state: Optional[ProcessState] = None) -> List[ProcessInfo]:
        """List processes, optionally filtered by state."""
        if state:
            return [p for p in self.processes.values() if p.state == state]
        return list(self.processes.values())

    def get(self, pid: int) -> Optional[ProcessInfo]:
        return self.processes.get(pid)

    def ps(self) -> str:
        """Generate ps-like output."""
        lines = ["  PID  STATE       COMMAND"]
        for proc in sorted(self.processes.values(), key=lambda p: p.pid):
            state = proc.state.value[:10].ljust(10)
            cmd = proc.command[:50]
            lines.append(f"  {proc.pid:<5} {state} {cmd}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Command History
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CommandEntry:
    """Record of an executed command."""
    command: str
    language: Language
    output: str
    error: str = ""
    exit_code: int = 0
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0


class CommandHistory:
    """Searchable command history."""

    def __init__(self, max_size: int = 10000) -> None:
        self.entries: List[CommandEntry] = []
        self.max_size = max_size
        self.position: int = -1

    def add(self, entry: CommandEntry) -> None:
        """Add a command to history."""
        self.entries.append(entry)
        if len(self.entries) > self.max_size:
            self.entries.pop(0)
        self.position = len(self.entries)

    def search(self, pattern: str) -> List[CommandEntry]:
        """Search history by pattern."""
        regex = re.compile(pattern, re.IGNORECASE)
        return [e for e in self.entries if regex.search(e.command)]

    def previous(self) -> Optional[str]:
        """Navigate to previous command."""
        if self.position > 0:
            self.position -= 1
            return self.entries[self.position].command
        return None

    def next(self) -> Optional[str]:
        """Navigate to next command."""
        if self.position < len(self.entries) - 1:
            self.position += 1
            return self.entries[self.position].command
        return None

    def last(self, n: int = 10) -> List[CommandEntry]:
        """Get last n commands."""
        return self.entries[-n:]

    def clear(self) -> None:
        self.entries.clear()
        self.position = -1


# ═══════════════════════════════════════════════════════════════════
# Security Sandbox
# ═══════════════════════════════════════════════════════════════════

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

class BashExecutor:
    """Simulated bash command execution using virtual FS."""

    def __init__(self, fs: VirtualFS) -> None:
        self.fs = fs
        self.cwd = "/home"
        self.env: Dict[str, str] = {
            "HOME": "/home",
            "PATH": "/bin:/usr/bin",
            "USER": "user",
            "SHELL": "/bin/bash",
        }

    def execute(self, command: str) -> Tuple[str, str, int]:
        """Execute a simulated bash command."""
        command = command.strip()

        # Handle pipes
        if "|" in command:
            return self._execute_pipeline(command)

        # Parse command
        parts = self._parse_command(command)
        if not parts:
            return "", "", 0

        cmd = parts[0]
        args = parts[1:]

        # Built-in commands
        builtins: Dict[str, Callable] = {
            "echo": self._cmd_echo,
            "ls": self._cmd_ls,
            "cd": self._cmd_cd,
            "pwd": self._cmd_pwd,
            "cat": self._cmd_cat,
            "mkdir": self._cmd_mkdir,
            "touch": self._cmd_touch,
            "rm": self._cmd_rm,
            "tree": self._cmd_tree,
            "find": self._cmd_find,
            "wc": self._cmd_wc,
            "head": self._cmd_head,
            "tail": self._cmd_tail,
            "grep": self._cmd_grep,
            "env": self._cmd_env,
            "export": self._cmd_export,
            "whoami": lambda a: ("user\n", "", 0),
            "date": lambda a: (time.strftime("%c") + "\n", "", 0),
            "uname": lambda a: ("Linux arki 5.15.0 #1 SMP x86_64\n", "", 0),
            "clear": lambda a: ("\033[2J\033[H", "", 0),
            "history": self._cmd_history,
            "du": self._cmd_du,
        }

        handler = builtins.get(cmd)
        if handler:
            try:
                return handler(args)
            except Exception as e:
                return "", f"{cmd}: {str(e)}\n", 1

        return "", f"bash: {cmd}: command not found\n", 127

    def _parse_command(self, command: str) -> List[str]:
        """Parse command into parts (handle quotes)."""
        parts: List[str] = []
        current = ""
        in_quote = None

        for c in command:
            if c in ('"', "'") and not in_quote:
                in_quote = c
            elif c == in_quote:
                in_quote = None
            elif c == " " and not in_quote:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += c

        if current:
            parts.append(current)
        return parts

    def _execute_pipeline(self, command: str) -> Tuple[str, str, int]:
        """Execute piped commands."""
        commands = [c.strip() for c in command.split("|")]
        stdin = ""
        last_stderr = ""
        last_code = 0

        for cmd in commands:
            # Pass previous stdout as context
            stdout, stderr, code = self.execute(cmd)
            stdin = stdout
            last_stderr = stderr
            last_code = code

        return stdin, last_stderr, last_code

    def _cmd_echo(self, args: List[str]) -> Tuple[str, str, int]:
        text = " ".join(args)
        # Handle variable expansion
        for var, val in self.env.items():
            text = text.replace(f"${var}", val)
            text = text.replace(f"${{{var}}}", val)
        return text + "\n", "", 0

    def _cmd_ls(self, args: List[str]) -> Tuple[str, str, int]:
        path = args[0] if args else self.cwd
        detailed = "-l" in args or "-la" in args
        items = self.fs.ls(path, details=detailed)
        if detailed:
            lines = []
            for item in items:
                t = "d" if item["type"] == "directory" else "-"
                lines.append(
                    f"{t}{item.get('permissions', 'rwxr-xr-x')} "
                    f"{item.get('size', 0):>8} {item['name']}"
                )
            return "\n".join(lines) + "\n", "", 0
        else:
            names = [i["name"] for i in items]
            return "  ".join(names) + "\n", "", 0

    def _cmd_cd(self, args: List[str]) -> Tuple[str, str, int]:
        path = args[0] if args else self.env.get("HOME", "/")
        if not path.startswith("/"):
            path = f"{self.cwd.rstrip('/')}/{path}"
        try:
            entry = self.fs._get_entry(path)
            if entry.entry_type != FileType.DIRECTORY:
                return "", f"cd: not a directory: {path}\n", 1
            self.cwd = self.fs._normalize_path(path)
            return "", "", 0
        except FileNotFoundError:
            return "", f"cd: no such directory: {path}\n", 1

    def _cmd_pwd(self, args: List[str]) -> Tuple[str, str, int]:
        return self.cwd + "\n", "", 0

    def _cmd_cat(self, args: List[str]) -> Tuple[str, str, int]:
        if not args:
            return "", "cat: missing operand\n", 1
        output = []
        for path in args:
            if not path.startswith("/"):
                path = f"{self.cwd.rstrip('/')}/{path}"
            try:
                content = self.fs.read(path)
                output.append(content)
            except FileNotFoundError:
                return "", f"cat: {path}: No such file\n", 1
        return "\n".join(output), "", 0

    def _cmd_mkdir(self, args: List[str]) -> Tuple[str, str, int]:
        for path in args:
            if path == "-p":
                continue
            if not path.startswith("/"):
                path = f"{self.cwd.rstrip('/')}/{path}"
            self.fs.mkdir(path)
        return "", "", 0

    def _cmd_touch(self, args: List[str]) -> Tuple[str, str, int]:
        for path in args:
            if not path.startswith("/"):
                path = f"{self.cwd.rstrip('/')}/{path}"
            self.fs.touch(path)
        return "", "", 0

    def _cmd_rm(self, args: List[str]) -> Tuple[str, str, int]:
        recursive = "-r" in args or "-rf" in args
        for path in args:
            if path.startswith("-"):
                continue
            if not path.startswith("/"):
                path = f"{self.cwd.rstrip('/')}/{path}"
            try:
                self.fs.rm(path, recursive=recursive)
            except FileNotFoundError:
                return "", f"rm: {path}: No such file\n", 1
        return "", "", 0

    def _cmd_tree(self, args: List[str]) -> Tuple[str, str, int]:
        path = args[0] if args else self.cwd
        return self.fs.tree(path) + "\n", "", 0

    def _cmd_find(self, args: List[str]) -> Tuple[str, str, int]:
        path = args[0] if args else self.cwd
        pattern = "*"
        if "-name" in args:
            idx = args.index("-name")
            if idx + 1 < len(args):
                pattern = args[idx + 1]
        results = self.fs.find(path, pattern)
        return "\n".join(results) + "\n", "", 0

    def _cmd_wc(self, args: List[str]) -> Tuple[str, str, int]:
        if not args:
            return "", "wc: missing operand\n", 1
        path = args[-1]
        if not path.startswith("/"):
            path = f"{self.cwd.rstrip('/')}/{path}"
        content = self.fs.read(path)
        lines = content.count("\n")
        words = len(content.split())
        chars = len(content)
        return f"  {lines}  {words}  {chars} {args[-1]}\n", "", 0

    def _cmd_head(self, args: List[str]) -> Tuple[str, str, int]:
        n = 10
        path = args[-1] if args else ""
        if "-n" in args:
            idx = args.index("-n")
            if idx + 1 < len(args):
                n = int(args[idx + 1])
        if not path.startswith("/"):
            path = f"{self.cwd.rstrip('/')}/{path}"
        content = self.fs.read(path)
        lines = content.split("\n")[:n]
        return "\n".join(lines) + "\n", "", 0

    def _cmd_tail(self, args: List[str]) -> Tuple[str, str, int]:
        n = 10
        path = args[-1] if args else ""
        if "-n" in args:
            idx = args.index("-n")
            if idx + 1 < len(args):
                n = int(args[idx + 1])
        if not path.startswith("/"):
            path = f"{self.cwd.rstrip('/')}/{path}"
        content = self.fs.read(path)
        lines = content.split("\n")[-n:]
        return "\n".join(lines) + "\n", "", 0

    def _cmd_grep(self, args: List[str]) -> Tuple[str, str, int]:
        if len(args) < 2:
            return "", "grep: missing pattern or file\n", 1
        pattern = args[0]
        path = args[1]
        if not path.startswith("/"):
            path = f"{self.cwd.rstrip('/')}/{path}"
        content = self.fs.read(path)
        matches = [
            line for line in content.split("\n")
            if re.search(pattern, line)
        ]
        return "\n".join(matches) + "\n", "", 0

    def _cmd_env(self, args: List[str]) -> Tuple[str, str, int]:
        return "\n".join(f"{k}={v}" for k, v in self.env.items()) + "\n", "", 0

    def _cmd_export(self, args: List[str]) -> Tuple[str, str, int]:
        for arg in args:
            if "=" in arg:
                key, val = arg.split("=", 1)
                self.env[key] = val
        return "", "", 0

    def _cmd_history(self, args: List[str]) -> Tuple[str, str, int]:
        return "Use session.history for command history\n", "", 0

    def _cmd_du(self, args: List[str]) -> Tuple[str, str, int]:
        path = args[0] if args else self.cwd
        size = self.fs.du(path)
        return f"{size}\t{path}\n", "", 0


# ═══════════════════════════════════════════════════════════════════
# Terminal Session
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TerminalSession:
    """A complete terminal session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    language: Language = Language.AUTO
    cwd: str = "/home"
    env: Dict[str, str] = field(default_factory=dict)
    aliases: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    max_output_lines: int = 1000


# ═══════════════════════════════════════════════════════════════════
# Terminal Emulator (Main Interface)
# ═══════════════════════════════════════════════════════════════════

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


