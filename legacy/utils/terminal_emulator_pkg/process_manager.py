
"""
terminal_emulator_pkg/process_manager.py — ProcessManager
Arki Engine v29.0.0
"""
from ._base import *  # noqa

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



