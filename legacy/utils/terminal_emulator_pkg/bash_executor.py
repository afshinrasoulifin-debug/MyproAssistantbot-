
"""
terminal_emulator_pkg/bash_executor.py — BashExecutor
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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



