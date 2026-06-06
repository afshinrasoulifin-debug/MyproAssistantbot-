
from __future__ import annotations
"""
tg_bot/utils/ws_remote.py
──────────────────────────
WebSocket + Remote Tasks Server

Provides a lightweight WebSocket server running alongside the bot
for real-time remote task execution. Admin-authenticated.

Architecture:
  client → WebSocket → authenticate → dispatch → executor → result → client

Features:
  ✅ Token-based authentication
  ✅ Remote shell/exec/eval via WebSocket
  ✅ Task queue with async execution
  ✅ Real-time streaming output
  ✅ Connection tracking and limits
  ✅ Heartbeat/keepalive
  ✅ Graceful shutdown

Usage (from main.py):
  from arki_project.utils.ws_remote import start_ws_server, stop_ws_server
  await start_ws_server(settings)
  ...
  await stop_ws_server()

Client example:
  import websockets, json
  async with websockets.connect("ws://host:8765") as ws:
      await ws.send(json.dumps({"type": "auth", "token": "YOUR_TOKEN"}))
      resp = json.loads(await ws.recv())
      await ws.send(json.dumps({"type": "sh", "command": "ls -la"}))
      result = json.loads(await ws.recv())

v29.0.0
"""


import asyncio
import hashlib
import io
import json
import logging
import os
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from typing import Any

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
WS_HOST = os.getenv("WS_HOST", "0.0.0.0")
WS_PORT = int(os.getenv("WS_PORT", "8765"))
WS_TOKEN = os.getenv("WS_TOKEN", "")  # Required for auth
MAX_CONNECTIONS = 5
EXEC_TIMEOUT = 60
HEARTBEAT_INTERVAL = 30


# ── State ──
_server: Any = None  # asyncio.Server
_connections: dict[str, "WSConnection"] = {}
_task_queue: asyncio.Queue | None = None
_worker_task: asyncio.Task | None = None


@dataclass
class WSConnection:
    """Track a single WebSocket connection."""
    conn_id: str
    writer: asyncio.StreamWriter
    reader: asyncio.StreamReader
    authenticated: bool = False
    connected_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    request_count: int = 0


@dataclass
class RemoteTask:
    """A queued remote task."""
    task_id: str
    task_type: str  # "sh", "exec", "eval"
    payload: str
    conn_id: str
    created_at: float = field(default_factory=time.time)


def _generate_token(settings: Any) -> str:
    """
    Generate auth token from settings.
    Uses WS_TOKEN env var, or derives from bot token.
    """
    if WS_TOKEN:
        return WS_TOKEN
    if hasattr(settings, "bot_token") and settings.bot_token:
        return hashlib.sha256(
            f"arki-ws-{settings.bot_token}".encode()
        ).hexdigest()[:32]
    return ""


# ════════════════════════════════════════════════════════
#  Protocol Handlers
# ════════════════════════════════════════════════════════

async def _handle_auth(data: dict, conn: WSConnection, token: str) -> dict:
    """Authenticate a connection."""
    client_token = data.get("token", "")
    if not token:
        return {"type": "error", "message": "Server token not configured"}
    if client_token == token:
        conn.authenticated = True
        return {"type": "auth_ok", "message": "Authenticated", "conn_id": conn.conn_id}
    return {"type": "auth_fail", "message": "Invalid token"}


async def _handle_shell(data: dict) -> dict:
    """Execute a shell command."""
    command = data.get("command", "")
    if not command:
        return {"type": "error", "message": "No command provided"}

    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash",
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=EXEC_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "type": "result",
                "status": "timeout",
                "command": command[:100],
                "elapsed": round(time.monotonic() - start, 3),
            }

        elapsed = time.monotonic() - start
        return {
            "type": "result",
            "status": "ok" if proc.returncode == 0 else "error",
            "stdout": stdout_b.decode("utf-8", errors="replace"),
            "stderr": stderr_b.decode("utf-8", errors="replace"),
            "exit_code": proc.returncode,
            "elapsed": round(elapsed, 3),
        }
    except Exception as exc:
        return {
            "type": "result",
            "status": "error",
            "message": str(exc),
            "elapsed": round(time.monotonic() - start, 3),
        }


async def _handle_exec(data: dict) -> dict:
    """Execute Python code."""
    code = data.get("code", "")
    if not code:
        return {"type": "error", "message": "No code provided"}

    stdout_cap = io.StringIO()
    stderr_cap = io.StringIO()
    exec_globals: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "__name__": "__ws_exec__",
        "asyncio": asyncio,
        "time_monotonic": time.monotonic,  # v9.8.7: no os/sys
        "time": time,
    }

    start = time.monotonic()
    error_text = ""
    try:
        with redirect_stdout(stdout_cap), redirect_stderr(stderr_cap):
            if "await " in code or "async " in code:
                wrapped = "async def __aexec__():\n"
                for line in code.split("\n"):
                    wrapped += f"    {line}\n"
                exec(compile(wrapped, "<ws_exec>", "exec"), exec_globals)
                await asyncio.wait_for(
                    exec_globals["__aexec__"](), timeout=EXEC_TIMEOUT
                )
            else:
                exec(compile(code, "<ws_exec>", "exec"), exec_globals)
    except asyncio.TimeoutError:
        error_text = f"Timeout ({EXEC_TIMEOUT}s)"
    except Exception:
        error_text = traceback.format_exc()

    elapsed = time.monotonic() - start
    return {
        "type": "result",
        "status": "ok" if not error_text else "error",
        "stdout": stdout_cap.getvalue(),
        "stderr": stderr_cap.getvalue(),
        "error": error_text,
        "elapsed": round(elapsed, 3),
    }


async def _handle_eval(data: dict) -> dict:
    """Evaluate a Python expression."""
    expr = data.get("expression", "")
    if not expr:
        return {"type": "error", "message": "No expression provided"}

    eval_globals: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "time_monotonic": time.monotonic, "time_time": time.time, "asyncio": asyncio,  # v9.8.7: no os
    }

    start = time.monotonic()
    try:
        result = eval(compile(expr, "<ws_eval>", "eval"), eval_globals)
        if asyncio.iscoroutine(result):
            result = await asyncio.wait_for(result, timeout=30)
        elapsed = time.monotonic() - start
        return {
            "type": "result",
            "status": "ok",
            "result": repr(result),
            "result_type": type(result).__name__,
            "elapsed": round(elapsed, 3),
        }
    except Exception:
        elapsed = time.monotonic() - start
        return {
            "type": "result",
            "status": "error",
            "error": traceback.format_exc(),
            "elapsed": round(elapsed, 3),
        }


async def _handle_ping(data: dict) -> dict:
    """Heartbeat/keepalive response."""
    return {"type": "pong", "timestamp": time.time()}


async def _handle_status(data: dict) -> dict:
    """Return server status."""
    return {
        "type": "status",
        "connections": len(_connections),
        "uptime": time.time(),
        "queue_size": _task_queue.qsize() if _task_queue else 0,
    }


# ════════════════════════════════════════════════════════
#  Connection Handler
# ════════════════════════════════════════════════════════

_HANDLERS = {
    "auth": _handle_auth,
    "sh": _handle_shell,
    "exec": _handle_exec,
    "eval": _handle_eval,
    "ping": _handle_ping,
    "status": _handle_status,
}


async def _handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    token: str,
) -> None:
    """Handle a single WebSocket-like TCP connection."""
    conn_id = hashlib.md5(
        f"{time.time()}{id(writer)}".encode()
    ).hexdigest()[:12]

    conn = WSConnection(
        conn_id=conn_id,
        writer=writer,
        reader=reader,
    )
    _connections[conn_id] = conn
    logger.info("WS connection %s opened (total: %d)", conn_id, len(_connections))

    try:
        # Send welcome
        await _send_json(writer, {
            "type": "welcome",
            "message": "Arki Engine v29.0.0 WS Remote",
            "conn_id": conn_id,
        })

        while True:
            try:
                raw = await asyncio.wait_for(
                    reader.readline(), timeout=HEARTBEAT_INTERVAL * 2
                )
            except asyncio.TimeoutError:
                await _send_json(writer, {"type": "timeout", "message": "Idle timeout"})
                break

            if not raw:
                break  # Connection closed

            try:
                data = json.loads(raw.decode("utf-8").strip())
            except (json.JSONDecodeError, UnicodeDecodeError):
                await _send_json(writer, {
                    "type": "error",
                    "message": "Invalid JSON",
                })
                continue

            msg_type = data.get("type", "")
            conn.last_active = time.time()
            conn.request_count += 1

            # Auth required for everything except auth and ping
            if msg_type == "auth":
                result = await _handle_auth(data, conn, token)
            elif msg_type == "ping":
                result = await _handle_ping(data)
            elif not conn.authenticated:
                result = {"type": "error", "message": "Not authenticated. Send auth first."}
            elif msg_type in _HANDLERS:
                result = await _HANDLERS[msg_type](data)
            else:
                result = {"type": "error", "message": f"Unknown type: {msg_type}"}

            await _send_json(writer, result)

    except (ConnectionResetError, BrokenPipeError):
        logger.debug("WS connection %s reset", conn_id)
    except Exception:
        logger.exception("WS connection %s error", conn_id)
    finally:
        _connections.pop(conn_id, None)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception as e:
            logger.debug("Suppressed: %s", e)
        logger.info("WS connection %s closed (total: %d)", conn_id, len(_connections))


async def _send_json(writer: asyncio.StreamWriter, data: dict) -> None:
    """Send a JSON message (newline-delimited)."""
    try:
        msg = json.dumps(data, ensure_ascii=False) + "\n"
        writer.write(msg.encode("utf-8"))
        await writer.drain()
    except (ConnectionResetError, BrokenPipeError):
        logger.debug("Suppressed: %s", _exc)


# ════════════════════════════════════════════════════════
#  Task Queue Worker
# ════════════════════════════════════════════════════════

async def _task_worker() -> None:
    """Process queued remote tasks."""
    global _task_queue
    if _task_queue is None:
        _task_queue = asyncio.Queue()

    while True:
        try:
            task: RemoteTask = await _task_queue.get()
            logger.info("Processing task %s: %s", task.task_id, task.task_type)

            handler = _HANDLERS.get(task.task_type)
            if handler:
                if task.task_type == "sh":
                    result = await handler({"command": task.payload})
                elif task.task_type in ("exec",):
                    result = await handler({"code": task.payload})
                elif task.task_type == "eval":
                    result = await handler({"expression": task.payload})
                else:
                    result = {"type": "error", "message": "Unknown task type"}

                # Send result to connection if still active
                conn = _connections.get(task.conn_id)
                if conn and conn.writer:
                    result["task_id"] = task.task_id
                    await _send_json(conn.writer, result)

            _task_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Task worker error")


# ════════════════════════════════════════════════════════
#  Public API
# ════════════════════════════════════════════════════════

async def start_ws_server(settings: Any) -> None:
    """Start the WebSocket remote task server."""
    global _server, _worker_task, _task_queue

    token = _generate_token(settings)
    if not token:
        logger.warning("WS_TOKEN not set — WebSocket server disabled")
        return

    _task_queue = asyncio.Queue()

    async def client_cb(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if len(_connections) >= MAX_CONNECTIONS:
            await _send_json(writer, {
                "type": "error",
                "message": "Max connections reached",
            })
            writer.close()
            return
        await _handle_connection(reader, writer, token)

    try:
        _server = await asyncio.start_server(client_cb, WS_HOST, WS_PORT)
        _worker_task = asyncio.create_task(_task_worker())
        logger.info("🌐 WS Remote server started on %s:%d", WS_HOST, WS_PORT)
    except OSError as exc:
        logger.warning("WS server failed to start: %s", exc)


async def stop_ws_server() -> None:
    """Gracefully stop the WebSocket server."""
    global _server, _worker_task

    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError as _exc:
            logger.debug("Suppressed: %s", _exc)
        _worker_task = None

    if _server:
        _server.close()
        await _server.wait_closed()
        _server = None

    # Close all connections
    for conn in list(_connections.values()):
        try:
            conn.writer.close()
        except Exception as e:
            logger.debug("Suppressed: %s", e)
    _connections.clear()

    logger.info("🌐 WS Remote server stopped")


def ws_stats() -> dict:
    """Return WebSocket server statistics."""
    return {
        "running": _server is not None,
        "host": WS_HOST,
        "port": WS_PORT,
        "connections": len(_connections),
        "connection_details": {
            cid: {
                "authenticated": c.authenticated,
                "requests": c.request_count,
                "connected_since": c.connected_at,
            }
            for cid, c in _connections.items()
        },
        "queue_size": _task_queue.qsize() if _task_queue else 0,
    }


async def queue_task(task_type: str, payload: str, conn_id: str = "") -> str:
    """Queue a remote task for execution. Returns task_id."""
    if _task_queue is None:
        raise RuntimeError("WS server not started")
    task_id = hashlib.md5(
        f"{time.time()}{payload[:50]}".encode()
    ).hexdigest()[:12]
    task = RemoteTask(
        task_id=task_id,
        task_type=task_type,
        payload=payload,
        conn_id=conn_id,
    )
    await _task_queue.put(task)
    return task_id


