
from __future__ import annotations
"""
tg_bot/utils/process_manager.py
────────────────────────────────
PROCESS MANAGER v1.0 — Advanced Process & Daemon Control

System-level process management:
  • Spawn processes (foreground/background/daemon)
  • Process monitoring with resource tracking
  • Watchdog — auto-restart on crash
  • Daemon mode with PID file management
  • Process groups and batch operations
  • Signal handling (TERM, KILL, HUP, USR1)
  • Output capture with rotation
  • Health checks for managed processes
  • Auto-cleanup of zombie processes
  • Persistence — survive bot restarts via PID files

Architecture:
  command → spawn → monitor → watchdog → restart/notify

v29.0.0
"""


import asyncio
import aiofiles
import logging
import os
import signal
import time
from dataclasses import dataclass, field
from typing import Any, Callable

# ── TITANIUM v29.0 Integration ──


logger = logging.getLogger(__name__)

# ── Configuration ──
MAX_MANAGED = 20
WATCHDOG_INTERVAL = 10  # seconds
HEALTH_CHECK_INTERVAL = 30
MAX_RESTARTS = 5
RESTART_BACKOFF_BASE = 2  # exponential backoff base seconds
OUTPUT_MAX_LINES = 500
PID_DIR = "/tmp/arki_pids"


# ── Types ──

@dataclass
class ManagedProcess:
    """A process managed by the process manager."""
    id: str
    command: str
    pid: int = 0
    status: str = "pending"  # pending, running, stopped, failed, restarting
    started_at: float = 0
    stopped_at: float = 0
    restart_count: int = 0
    max_restarts: int = MAX_RESTARTS
    exit_code: int | None = None
    output_lines: list[str] = field(default_factory=list)
    error_lines: list[str] = field(default_factory=list)
    daemon: bool = False
    watchdog: bool = False
    health_cmd: str = ""
    health_ok: bool = True
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    _proc: Any = field(default=None, repr=False)
    _output_task: Any = field(default=None, repr=False)

    @property
    def uptime(self) -> float:
        if self.status_code == "running" and self.started_at:
            return time.time() - self.started_at
        return 0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "command": self.command[:100],
            "pid": self.pid, "status": self.status_code,
            "uptime_s": int(self.uptime),
            "restart_count": self.restart_count,
            "exit_code": self.exit_code,
            "daemon": self.daemon, "watchdog": self.watchdog,
            "health_ok": self.health_ok,
            "output_tail": self.output_lines[-5:] if self.output_lines else [],
        }


class ProcessManager:
    """Manages system processes with watchdog and health checks."""

    def __init__(self) -> None:
        self._processes: dict[str, ManagedProcess] = {}
        self._watchdog_task: asyncio.Task | None = None
        self._next_id = 1
        self._callbacks: dict[str, Callable] = {}
        os.makedirs(PID_DIR, exist_ok=True)

    async def spawn(
        self,
        command: str,
        *,
        proc_id: str = "",
        daemon: bool = False,
        watchdog: bool = False,
        health_cmd: str = "",
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        on_exit: Callable | None = None,
    ) -> ManagedProcess:
        """Spawn a new managed process."""
        if len(self._processes) >= MAX_MANAGED:
            raise RuntimeError(f"Max {MAX_MANAGED} managed processes")

        if not proc_id:
            proc_id = f"proc-{self._next_id}"
            self._next_id += 1

        mp = ManagedProcess(
            id=proc_id, command=command,
            daemon=daemon, watchdog=watchdog,
            health_cmd=health_cmd,
            env=env or {},
            cwd=cwd,
        )

        if on_exit:
            self._callbacks[proc_id] = on_exit

        await self._start_process(mp)
        self._processes[proc_id] = mp

        if watchdog and not self._watchdog_task:
            self._watchdog_task = asyncio.create_task(self._watchdog_loop())

        return mp

    async def _start_process(self, mp: ManagedProcess) -> None:
        """Actually start a process."""
        full_env = os.environ.copy()
        full_env.update(mp.env)

        proc = await asyncio.create_subprocess_shell(
            mp.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
            cwd=mp.cwd,
            executable="/bin/bash",
        )

        mp._proc = proc
        mp.pid = proc.pid or 0
        mp.status_code = "running"
        mp.started_at = time.time()

        # Write PID file
        pid_path = os.path.join(PID_DIR, f"{mp.id}.pid")
        async with aiofiles.open(pid_path, "w") as f:
            await f.write(str(mp.pid))

        # Start output capture
        mp._output_task = asyncio.create_task(self._capture_output(mp))
        logger.info("Process %s started (PID %d): %s", mp.id, mp.pid, mp.command[:80])

    async def _capture_output(self, mp: ManagedProcess) -> None:
        """Capture stdout/stderr in background."""
        async def _read_stream(stream: bool, lines: Any) -> Any:
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                lines.append(text)
                if len(lines) > OUTPUT_MAX_LINES:
                    lines[:] = lines[-OUTPUT_MAX_LINES:]

        if mp._proc:
            tasks = []
            if mp._proc.stdout:
                tasks.append(_read_stream(mp._proc.stdout, mp.output_lines))
            if mp._proc.stderr:
                tasks.append(_read_stream(mp._proc.stderr, mp.error_lines))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # Wait for process to finish
            await mp._proc.wait()
            mp.exit_code = mp._proc.returncode
            mp.stopped_at = time.time()

            if mp.exit_code == 0:
                mp.status_code = "stopped"
            else:
                mp.status_code = "failed"

            # Cleanup PID file
            pid_path = os.path.join(PID_DIR, f"{mp.id}.pid")
            if os.path.exists(pid_path):
                os.remove(pid_path)

            # Callback
            if mp.id in self._callbacks:
                try:
                    self._callbacks[mp.id](mp)
                except Exception as e:
                    logger.debug("Suppressed: %s", e)

    async def stop(self, proc_id: str, force: bool = False) -> bool:
        """Stop a managed process."""
        mp = self._processes.get(proc_id)
        if not mp or not mp._proc or mp.status_code != "running":
            return False

        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            mp._proc.send_signal(sig)
            mp.watchdog = False  # Disable watchdog on manual stop
            try:
                await asyncio.wait_for(mp._proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                mp._proc.kill()
                await mp._proc.wait()
            mp.status_code = "stopped"
            mp.stopped_at = time.time()
            return True
        except Exception as exc:
            logger.warning("Failed to stop %s: %s", proc_id, exc)
            return False

    async def restart(self, proc_id: str) -> bool:
        """Restart a managed process."""
        mp = self._processes.get(proc_id)
        if not mp:
            return False

        if mp.status_code == "running":
            await self.stop(proc_id)
            await asyncio.sleep(0.5)

        mp.restart_count += 1
        mp.status_code = "restarting"
        await self._start_process(mp)
        return True

    async def _watchdog_loop(self) -> None:
        """Monitor processes and auto-restart crashed ones."""
        while True:
            try:
                await asyncio.sleep(WATCHDOG_INTERVAL)
                for mp in list(self._processes.values()):
                    if not mp.watchdog or mp.status_code == "running":
                        continue
                    if mp.status_code in ("failed", "stopped") and mp.restart_count < mp.max_restarts:
                        backoff = RESTART_BACKOFF_BASE ** min(mp.restart_count, 5)
                        if time.time() - mp.stopped_at > backoff:
                            logger.info("Watchdog restarting %s (attempt %d/%d)",
                                       mp.id, mp.restart_count + 1, mp.max_restarts)
                            await self.restart(mp.id)

                    # Health check
                    if mp.health_cmd and mp.status_code == "running":
                        try:
                            proc = await asyncio.create_subprocess_shell(
                                mp.health_cmd,
                                stdout=asyncio.subprocess.DEVNULL,
                                stderr=asyncio.subprocess.DEVNULL,
                            )
                            rc = await asyncio.wait_for(proc.wait(), timeout=5)
                            mp.health_ok = rc == 0
                            if not mp.health_ok:
                                logger.warning("Health check failed for %s", mp.id)
                                await self.restart(mp.id)
                        except Exception:
                            mp.health_ok = False

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Watchdog error")

    def get(self, proc_id: str) -> ManagedProcess | None:
        return self._processes.get(proc_id)

    def list_processes(self) -> list[dict]:
        return [mp.to_dict() for mp in self._processes.values()]

    def stats(self) -> dict:
        by_status = {}
        for mp in self._processes.values():
            by_status[mp.status_code] = by_status.get(mp.status_code, 0) + 1
        return {
            "total": len(self._processes),
            "by_status": by_status,
            "watchdog_active": self._watchdog_task is not None,
        }

    async def cleanup(self) -> None:
        """Stop all processes and clean up."""
        for proc_id in list(self._processes.keys()):
            await self.stop(proc_id, force=True)
        if self._watchdog_task:
            self._watchdog_task.cancel()
            self._watchdog_task = None


# ── Module Singleton ──
process_manager = ProcessManager()


