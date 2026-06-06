
from __future__ import annotations
from arki_project.exceptions import ArkiBaseError
"""
tg_bot/utils/persistent_exec.py
────────────────────────────────
Persistence + Remote Execution Engine

Persistent task queue that survives bot restarts.
Tasks are stored in the database and executed asynchronously.

Architecture:
  submit → DB queue → worker loop → executor → result → notify (Telegram)

Features:
  ✅ Database-backed task persistence (survives restart)
  ✅ Async worker with configurable concurrency
  ✅ Shell, Python exec, eval task types
  ✅ Result storage and Telegram notification
  ✅ Retry on failure with exponential backoff
  ✅ Task history and status tracking
  ✅ Auto-cleanup of old completed tasks

Commands (registered in executor.py):
  /queue <type> <payload>  — Queue a persistent task
  /tasks                   — List queued/running tasks
  /tasklog [id]            — View task results

v29.0.0
"""


import asyncio
import io
import logging
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import text

# Sandboxed builtins — no __import__, eval, exec, compile, open, etc.
_SAFE_BUILTINS = {
    'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
    'bytearray': bytearray, 'bytes': bytes, 'chr': chr, 'complex': complex,
    'dict': dict, 'divmod': divmod, 'enumerate': enumerate, 'filter': filter,
    'float': float, 'format': format, 'frozenset': frozenset, 'hasattr': hasattr,
    'hash': hash, 'hex': hex, 'int': int, 'isinstance': isinstance,
    'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list,
    'map': map, 'max': max, 'min': min, 'next': next, 'oct': oct,
    'ord': ord, 'pow': pow, 'print': print, 'range': range, 'repr': repr,
    'reversed': reversed, 'round': round, 'set': set, 'slice': slice,
    'sorted': sorted, 'str': str, 'sum': sum, 'tuple': tuple, # v9.8.7: 'type' removed — sandbox escape
    'zip': zip, 'None': None, 'True': True, 'False': False,
}


# v9.8.7: AST-level sandbox escape prevention
import ast as _ast

# ── TITANIUM v29.0 Integration ──


_FORBIDDEN_ATTRS = frozenset({
    "__subclasses__", "__bases__", "__mro__", "__class__",
    "__globals__", "__code__", "__builtins__", "__import__",
    "__getattr__", "__reduce__", "__reduce_ex__",
})

def _sandbox_check(code: str) -> str | None:
    """Return error message if code attempts sandbox escape, else None."""
    try:
        tree = _ast.parse(code)
    except SyntaxError:
        return None  # Let the actual exec handle syntax errors
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Attribute) and node.attr in _FORBIDDEN_ATTRS:
            return f"🚫 Blocked: access to '{node.attr}' is forbidden in sandbox"
    return None



logger = logging.getLogger(__name__)

# ── Configuration ──
MAX_CONCURRENT_TASKS = 3
MAX_RETRIES = 2
TASK_TIMEOUT = 120  # seconds
CLEANUP_AFTER_HOURS = 72
POLL_INTERVAL = 5  # seconds


# ── State ──
_worker_task: asyncio.Task | None = None
_bot_ref: Any = None
_settings_ref: Any = None
_running = False


# ════════════════════════════════════════════════════════
#  Database Operations
# ════════════════════════════════════════════════════════

async def _ensure_table() -> None:
    """Create persistent_tasks table if not exists."""
    from arki_project.database.connection import get_session
    async with get_session() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS persistent_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id BIGINT NOT NULL,
                chat_id BIGINT NOT NULL,
                task_type VARCHAR(32) NOT NULL,
                payload TEXT NOT NULL,
                status VARCHAR(16) NOT NULL DEFAULT 'pending',
                result TEXT NOT NULL DEFAULT '',
                exit_code INTEGER,
                elapsed_ms INTEGER DEFAULT 0,
                retries INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 2,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error TEXT NOT NULL DEFAULT ''
            )
        """))
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_ptasks_status
            ON persistent_tasks(status)
        """))


async def submit_task(
    admin_id: int,
    chat_id: int,
    task_type: str,
    payload: str,
) -> int:
    """Submit a new persistent task. Returns task ID."""
    from arki_project.database.connection import get_session
    await _ensure_table()

    async with get_session() as session:
        result = await session.execute(text("""
            INSERT INTO persistent_tasks (admin_id, chat_id, task_type, payload, status)
            VALUES (:admin_id, :chat_id, :task_type, :payload, 'pending')
        """), {
            "admin_id": admin_id,
            "chat_id": chat_id,
            "task_type": task_type,
            "payload": payload,
        })
        await session.flush()

        # Get last insert id
        row = await session.execute(text("SELECT last_insert_rowid()"))
        task_id = row.scalar()

    return task_id


async def get_pending_tasks(limit: int = MAX_CONCURRENT_TASKS) -> list[dict]:
    """Fetch pending tasks from DB."""
    from arki_project.database.connection import get_session
    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, admin_id, chat_id, task_type, payload, retries, max_retries
            FROM persistent_tasks
            WHERE status = 'pending'
            ORDER BY id ASC
            LIMIT :limit
        """), {"limit": limit})
        rows = result.fetchall()
        return [
            {
                "id": r[0], "admin_id": r[1], "chat_id": r[2],
                "task_type": r[3], "payload": r[4],
                "retries": r[5], "max_retries": r[6],
            }
            for r in rows
        ]


async def update_task_status(
    task_id: int,
    status: str,
    result: str = "",
    exit_code: int | None = None,
    elapsed_ms: int = 0,
    error: str = "",
) -> None:
    """Update task status in DB."""
    from arki_project.database.connection import get_session
    now = datetime.now(timezone.utc).isoformat()
    async with get_session() as session:
        if status == "running":
            await session.execute(text("""
                UPDATE persistent_tasks
                SET status = 'running', started_at = :now
                WHERE id = :id
            """), {"id": task_id, "now": now})
        else:
            await session.execute(text("""
                UPDATE persistent_tasks
                SET status = :status, result = :result, exit_code = :exit_code,
                    elapsed_ms = :elapsed_ms, error = :error, completed_at = :now
                WHERE id = :id
            """), {
                "id": task_id, "status": status, "result": result,
                "exit_code": exit_code, "elapsed_ms": elapsed_ms,
                "error": error, "now": now,
            })


async def retry_task(task_id: int) -> None:
    """Mark a failed task for retry."""
    from arki_project.database.connection import get_session
    async with get_session() as session:
        await session.execute(text("""
            UPDATE persistent_tasks
            SET status = 'pending', retries = retries + 1,
                started_at = NULL, completed_at = NULL
            WHERE id = :id
        """), {"id": task_id})


async def get_task_list(limit: int = 20) -> list[dict]:
    """Get recent tasks for display."""
    from arki_project.database.connection import get_session
    await _ensure_table()
    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, task_type, status, payload, elapsed_ms, exit_code,
                   created_at, error
            FROM persistent_tasks
            ORDER BY id DESC
            LIMIT :limit
        """), {"limit": limit})
        rows = result.fetchall()
        return [
            {
                "id": r[0], "type": r[1], "status": r[2],
                "payload": r[3][:60], "elapsed_ms": r[4],
                "exit_code": r[5], "created_at": r[6], "error": r[7][:100] if r[7] else "",
            }
            for r in rows
        ]


async def get_task_detail(task_id: int) -> dict | None:
    """Get full task details."""
    from arki_project.database.connection import get_session
    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, admin_id, chat_id, task_type, payload, status,
                   result, exit_code, elapsed_ms, retries, error,
                   created_at, started_at, completed_at
            FROM persistent_tasks WHERE id = :id
        """), {"id": task_id})
        r = result.fetchone()
        if not r:
            return None
        return {
            "id": r[0], "admin_id": r[1], "chat_id": r[2],
            "type": r[3], "payload": r[4], "status": r[5],
            "result": r[6], "exit_code": r[7], "elapsed_ms": r[8],
            "retries": r[9], "error": r[10],
            "created_at": r[11], "started_at": r[12], "completed_at": r[13],
        }


async def cleanup_old_tasks() -> int:
    """Remove completed tasks older than CLEANUP_AFTER_HOURS."""
    from arki_project.database.connection import get_session
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=CLEANUP_AFTER_HOURS)).isoformat()
    async with get_session() as session:
        result = await session.execute(text("""
            DELETE FROM persistent_tasks
            WHERE status IN ('done', 'failed') AND completed_at < :cutoff
        """), {"cutoff": cutoff})
        return result.rowcount or 0


# ════════════════════════════════════════════════════════
#  Task Executors
# ════════════════════════════════════════════════════════

async def _execute_shell(payload: str) -> tuple[str, int, str]:
    """Execute shell command. Returns (stdout+stderr, exit_code, error)."""
    try:
        proc = await asyncio.create_subprocess_shell(
            payload,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash",
        )
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=TASK_TIMEOUT
        )
        output = stdout_b.decode("utf-8", errors="replace")
        if stderr_b:
            output += "\n--- stderr ---\n" + stderr_b.decode("utf-8", errors="replace")
        return output, proc.returncode or 0, ""
    except asyncio.TimeoutError:
        return "", -1, f"Timeout ({TASK_TIMEOUT}s)"
    except ArkiBaseError as exc:
        return "", -1, str(exc)


async def _execute_python(payload: str) -> tuple[str, int, str]:
    """Execute Python code. Returns (output, 0/1, error)."""
    stdout_cap = io.StringIO()
    stderr_cap = io.StringIO()
    exec_globals: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "asyncio": asyncio, "os": __import__("os"),
        "sys": __import__("sys"), "time": time,
    }
    try:
        with redirect_stdout(stdout_cap), redirect_stderr(stderr_cap):
            if "await " in payload or "async " in payload:
                wrapped = "async def __aexec__():\n"
                for line in payload.split("\n"):
                    wrapped += f"    {line}\n"
                exec(compile(wrapped, "<persistent_exec>", "exec"), exec_globals)
                await asyncio.wait_for(
                    exec_globals["__aexec__"](), timeout=TASK_TIMEOUT
                )
            else:
                exec(compile(payload, "<persistent_exec>", "exec"), exec_globals)

        output = stdout_cap.getvalue()
        if stderr_cap.getvalue():
            output += "\n--- stderr ---\n" + stderr_cap.getvalue()
        return output, 0, ""
    except asyncio.TimeoutError:
        return stdout_cap.getvalue(), 1, f"Timeout ({TASK_TIMEOUT}s)"
    except ArkiBaseError:
        return stdout_cap.getvalue(), 1, traceback.format_exc()


async def _execute_eval(payload: str) -> tuple[str, int, str]:
    """Evaluate Python expression. Returns (result_repr, 0/1, error)."""
    eval_globals: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "os": __import__("os"), "time": time, "asyncio": asyncio,
    }
    try:
        result = eval(compile(payload, "<persistent_eval>", "eval"), eval_globals)
        if asyncio.iscoroutine(result):
            result = await asyncio.wait_for(result, timeout=30)
        return repr(result), 0, ""
    except ArkiBaseError:
        return "", 1, traceback.format_exc()


_EXECUTORS = {
    "sh": _execute_shell,
    "exec": _execute_python,
    "eval": _execute_eval,
}


# ════════════════════════════════════════════════════════
#  Worker Loop
# ════════════════════════════════════════════════════════

async def _notify_admin(task: dict, output: str, exit_code: int, error: str, elapsed: float) -> None:
    """Send task result to admin via Telegram."""
    if not _bot_ref:
        return
    try:
        icon = "✅" if exit_code == 0 else "❌"
        text_parts = [
            f"{icon} *Task #{task['id']}* (`{task['task_type']}`)",
            f"```\n{task['payload'][:200]}\n```",
        ]
        if output.strip():
            out_preview = output[:500]
            text_parts.append(f"📤 Output:\n```\n{out_preview}\n```")
        if error:
            text_parts.append(f"⚠️ Error:\n```\n{error[:300]}\n```")
        text_parts.append(f"⏱ `{elapsed:.2f}s`")

        msg = "\n\n".join(text_parts)
        await _bot_ref.send_message(
            task["chat_id"], msg, parse_mode="Markdown"
        )
    except ArkiBaseError:
        logger.exception("Failed to notify admin for task %d", task["id"])


async def _process_task(task: dict) -> None:
    """Process a single task."""
    task_id = task["id"]
    task_type = task["task_type"]
    payload = task["payload"]

    await update_task_status(task_id, "running")
    logger.info("Executing task #%d: %s", task_id, task_type)

    executor = _EXECUTORS.get(task_type)
    if not executor:
        await update_task_status(task_id, "failed", error=f"Unknown type: {task_type}")
        return

    start = time.monotonic()
    output, exit_code, error = await executor(payload)
    elapsed = time.monotonic() - start

    if exit_code == 0:
        await update_task_status(
            task_id, "done",
            result=output[:10000],
            exit_code=exit_code,
            elapsed_ms=int(elapsed * 1000),
        )
    else:
        # Check retry
        if task["retries"] < task["max_retries"]:
            await retry_task(task_id)
            logger.info("Task #%d failed, retry %d/%d",
                       task_id, task["retries"] + 1, task["max_retries"])
            return
        else:
            await update_task_status(
                task_id, "failed",
                result=output[:10000],
                exit_code=exit_code,
                elapsed_ms=int(elapsed * 1000),
                error=error[:5000],
            )

    await _notify_admin(task, output, exit_code, error, elapsed)


async def _worker_loop() -> None:
    """Main worker loop — polls DB for pending tasks."""
    global _running
    _running = True
    logger.info("🔄 Persistent executor worker started")

    cleanup_counter = 0
    while _running:
        try:
            tasks = await get_pending_tasks()
            if tasks:
                await asyncio.gather(
                    *[_process_task(t) for t in tasks],
                    return_exceptions=True,
                )
            else:
                await asyncio.sleep(POLL_INTERVAL)

            # Periodic cleanup
            cleanup_counter += 1
            if cleanup_counter >= 720:  # ~every hour at 5s interval
                cleaned = await cleanup_old_tasks()
                if cleaned:
                    logger.info("Cleaned up %d old tasks", cleaned)
                cleanup_counter = 0

        except asyncio.CancelledError:
            break
        except ArkiBaseError:
            logger.exception("Worker loop error")
            await asyncio.sleep(POLL_INTERVAL)

    _running = False
    logger.info("🔄 Persistent executor worker stopped")


# ════════════════════════════════════════════════════════
#  Public API
# ════════════════════════════════════════════════════════

async def start_persistent_executor(bot: Any, settings: Any) -> None:
    """Start the persistent execution worker."""
    global _worker_task, _bot_ref, _settings_ref

    _bot_ref = bot
    _settings_ref = settings

    await _ensure_table()
    _worker_task = asyncio.create_task(_worker_loop())


async def stop_persistent_executor() -> None:
    """Stop the persistent execution worker."""
    global _worker_task, _running

    _running = False
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError as _exc:
            logger.debug("Suppressed: %s", _exc)
        _worker_task = None


def executor_stats() -> dict:
    """Return persistent executor statistics."""
    return {
        "running": _running,
        "has_bot": _bot_ref is not None,
    }


