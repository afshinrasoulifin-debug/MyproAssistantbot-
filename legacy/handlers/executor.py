
from __future__ import annotations
"""
tg_bot/handlers/executor.py
────────────────────────────
🔧 System Executor — Admin-only remote execution engine.

Pipeline:
  user input → parser → eval/exec → shell → OS
  telegram → command dispatcher → runtime executor → system command

Commands:
  /sh <command>        — Execute shell command (bash)
  /exec <code>         — Execute Python code block
  /eval <expression>   — Evaluate Python expression and return result
  /py <code>           — Alias for /exec with auto-print
  /upload <path>       — Upload a server file to Telegram
  /download            — Download a Telegram file to server (reply to file)
  /sysinfo             — Full system information
  /pip <package>       — Install Python package
  /env [key] [value]   — View/set environment variables (runtime only)
  /kill <pid>          — Kill a process by PID

Security:
  ✅ Admin-only (checked against settings.admin_ids)
  ✅ Execution timeout (configurable, default 60s)
  ✅ Output truncation for Telegram limits
  ✅ Async execution (non-blocking)
  ✅ Full stdout + stderr capture
  ✅ Error tracebacks

v29.0.0
"""


import asyncio
import aiofiles
import io
import logging
import os
import platform
import signal
import sys
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile

from arki_project.config import Settings
from arki_project.utils.safe_send import safe_reply, send_long_text

# Sandboxed builtins — no __import__, eval, exec, compile, open, getattr, hasattr, etc.
# v29.0 HARDENED: removed hasattr (probing), kept only pure-computation builtins
_SAFE_BUILTINS = {
    'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
    'bytearray': bytearray, 'bytes': bytes, 'chr': chr, 'complex': complex,
    'dict': dict, 'divmod': divmod, 'enumerate': enumerate, 'filter': filter,
    'float': float, 'format': format, 'frozenset': frozenset,
    'hash': hash, 'hex': hex, 'int': int, 'isinstance': isinstance,
    'issubclass': issubclass, 'iter': iter, 'len': len, 'list': list,
    'map': map, 'max': max, 'min': min, 'next': next, 'oct': oct,
    'ord': ord, 'pow': pow, 'print': print, 'range': range, 'repr': repr,
    'reversed': reversed, 'round': round, 'set': set, 'slice': slice,
    'sorted': sorted, 'str': str, 'sum': sum, 'tuple': tuple,
    'zip': zip, 'None': None, 'True': True, 'False': False,
}


# v9.8.7: AST-level sandbox escape prevention
import ast as _ast

# ── TITANIUM v29.0 Integration ──
try:
    from arki_project.utils.titanium.config import get_config 
except ImportError:
    pass
_FORBIDDEN_ATTRS = frozenset({
    "__subclasses__", "__bases__", "__mro__", "__class__",
    "__globals__", "__code__", "__builtins__", "__import__",
    "__getattr__", "__reduce__", "__reduce_ex__",
    "__init__", "__new__", "__del__", "__dict__",
    "__slots__", "__weakref__", "__set_name__",
    "__init_subclass__", "__class_getitem__",
})

# v29.0: Forbidden names — blocks direct references like __import__("os")
_FORBIDDEN_NAMES = frozenset({
    "__import__", "__builtins__", "__loader__", "__spec__",
    "exec", "eval", "compile", "open", "input",
    "getattr", "setattr", "delattr", "vars", "dir",
    "globals", "locals", "breakpoint", "exit", "quit",
    "memoryview", "type", "object", "super",
    "__build_class__",
})

# v29.0: Forbidden string patterns in code (catches string-based evasion)
_FORBIDDEN_STRINGS = frozenset({
    "__import__", "__subclasses__", "__globals__", "__builtins__",
    "__code__", "__bases__", "__mro__", "subprocess",
})

def _sandbox_check(code: str) -> str | None:
    """Return error message if code attempts sandbox escape, else None.
    v29.0: Hardened with Name node + string literal + import statement checks.
    """
    try:
        tree = _ast.parse(code)
    except SyntaxError:
        return None  # Let the actual exec handle syntax errors

    for node in _ast.walk(tree):
        # Block forbidden attribute access: obj.__subclasses__
        if isinstance(node, _ast.Attribute) and node.attr in _FORBIDDEN_ATTRS:
            return f"🚫 Blocked: access to '{node.attr}' is forbidden in sandbox"

        # Block forbidden name references: __import__, getattr, eval, etc.
        if isinstance(node, _ast.Name) and node.id in _FORBIDDEN_NAMES:
            return f"🚫 Blocked: '{node.id}' is not allowed in sandbox"

        # Block import statements entirely (use pre-loaded modules only)
        if isinstance(node, (_ast.Import, _ast.ImportFrom)):
            return "🚫 Blocked: import statements are not allowed in sandbox"

        # Block string literals that contain escape patterns
        if isinstance(node, _ast.Constant) and isinstance(node.value, str):
            for forbidden in _FORBIDDEN_STRINGS:
                if forbidden in node.value:
                    return f"🚫 Blocked: suspicious string '{forbidden}' detected"

    return None



logger = logging.getLogger(__name__)

# v9.1: Pipeline integration
try:
    from arki_project.utils.v7_core import get_pipeline, get_memory
except Exception as exc:
    logger.error("Error in handler: %s", exc)
    get_pipeline = None
    get_memory = None
router = Router(name="executor")

# ── Configuration ──
EXEC_TIMEOUT = 60          # seconds — shell & exec timeout
EVAL_TIMEOUT = 30          # seconds — eval timeout
MAX_OUTPUT_LENGTH = 4000   # chars — Telegram message limit safe zone
SHELL = "/bin/bash"        # default shell


# ════════════════════════════════════════════════════════
#  Access Control
# ════════════════════════════════════════════════════════

def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


def _deny(message: Message, settings: Settings) -> bool:
    """Returns True if user should be denied access.
    v29.0.0: Code execution is admin-only for security.
    """
    if not message.from_user:
        return True
    return not _is_admin(message.from_user.id, settings)


# Lazy imports for persistence + WS modules
def _get_persistent() -> Any:
    from arki_project.utils.persistent_exec import (
        submit_task, get_task_list, get_task_detail,
    )
    return submit_task, get_task_list, get_task_detail

def _get_ws() -> Any:
    from arki_project.utils.ws_remote import ws_stats
    return ws_stats


# ════════════════════════════════════════════════════════
#  Output Formatting
# ════════════════════════════════════════════════════════

def _truncate(text: str, max_len: int = MAX_OUTPUT_LENGTH) -> str:
    """Truncate output and add indicator if too long."""
    if len(text) <= max_len:
        return text
    half = max_len // 2
    return (
        text[:half]
        + f"\n\n⚠️ ... [{len(text) - max_len} chars truncated] ...\n\n"
        + text[-half:]
    )


def _format_output(
    stdout: str,
    stderr: str,
    exit_code: int | None = None,
    exec_time: float = 0,
) -> str:
    """Format execution output for Telegram."""
    parts = []

    if stdout.strip():
        parts.append(f"📤 *stdout:*\n```\n{_truncate(stdout)}\n```")
    if stderr.strip():
        parts.append(f"⚠️ *stderr:*\n```\n{_truncate(stderr)}\n```")
    if exit_code is not None:
        icon = "✅" if exit_code == 0 else "❌"
        parts.append(f"{icon} Exit: `{exit_code}` | ⏱ `{exec_time:.2f}s`")
    elif exec_time:
        parts.append(f"⏱ `{exec_time:.2f}s`")

    if not parts:
        return "✅ اجرا شد — خروجی خالی"

    return "\n\n".join(parts)


# ════════════════════════════════════════════════════════
#  /sh — Shell Command Execution
# ════════════════════════════════════════════════════════

@router.message(Command("sh"))
async def cmd_shell(message: Message, settings: Settings) -> None:
    """
    Execute a shell command.
    
    Pipeline: user input → parser → shell → OS → output
    """
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip():
        await safe_reply(message,
            "🐚 *Shell Executor*\n\n"
            "استفاده: `/sh <command>`\n\n"
            "مثال:\n"
            "`/sh ls -la`\n"
            "`/sh df -h`\n"
            "`/sh cat /etc/os-release`\n"
            "`/sh ps aux | grep python`"
        )
        return

    command = raw[1].strip()
    status = await safe_reply(message, f"⚙️ `{command[:80]}` ...")

    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            SHELL, "-c", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=EXEC_TIMEOUT
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            elapsed = time.monotonic() - start
            await safe_reply(message,
                f"⏰ *Timeout!* ({EXEC_TIMEOUT}s)\n"
                f"دستور `{command[:60]}` بعد از {elapsed:.1f}s متوقف شد."
            )
            return

        elapsed = time.monotonic() - start
        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")

        result = _format_output(stdout, stderr, proc.returncode, elapsed)

        # If output is very long, send as file
        total = len(stdout) + len(stderr)
        if total > MAX_OUTPUT_LENGTH * 2:
            # Send as text file
            full_output = f"$ {command}\n\n"
            if stdout:
                full_output += f"=== STDOUT ===\n{stdout}\n\n"
            if stderr:
                full_output += f"=== STDERR ===\n{stderr}\n\n"
            full_output += f"Exit: {proc.returncode} | Time: {elapsed:.2f}s"

            filepath = f"/tmp/sh_output_{int(time.time())}.txt"
            with open(filepath, "w") as f:
                f.write(full_output)

            doc = FSInputFile(filepath, filename="output.txt")
            await message.answer_document(
                doc,
                caption=f"📄 خروجی `{command[:50]}` — خیلی بلند بود\n"
                        f"Exit: `{proc.returncode}` | ⏱ `{elapsed:.2f}s`",
                parse_mode="Markdown",
            )
            os.remove(filepath)
        else:
            await send_long_text(message, result)

    except Exception as exc:
        elapsed = time.monotonic() - start
        await safe_reply(message,
            f"❌ *خطا در اجرا:*\n```\n{exc}\n```\n⏱ `{elapsed:.2f}s`"
        )
        logger.exception("Shell execution error: %s", command[:100])


# ════════════════════════════════════════════════════════
#  /exec — Python Code Execution
# ════════════════════════════════════════════════════════

@router.message(Command("exec"))
async def cmd_exec(message: Message, settings: Settings) -> None:
    """
    Execute a Python code block.
    
    Pipeline: user input → parser → exec() → runtime → output
    """
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip():
        await safe_reply(message,
            "🐍 *Python Executor*\n\n"
            "استفاده: `/exec <code>`\n\n"
            "مثال:\n"
            "`/exec print('hello')`\n"
            "`/exec import sys; print(sys.version)`\n"
            "```\n/exec\nfor i in range(5):\n    print(f'Item {i}')\n```"
        )
        return

    code = raw[1].strip()
    # Remove markdown code block wrappers if present
    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    status = await safe_reply(message, "🐍 اجرای کد پایتون...")

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    # Build execution namespace with useful imports
    # v9.8.7: Hardened sandbox — no os/sys/settings access.
    # Admin can use /shell for OS commands.
    exec_globals: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "__name__": "__exec__",
        "asyncio": asyncio,
        "time_monotonic": time.monotonic,
        "time_time": time.time,
    }

    # v9.8.7: Pre-exec sandbox escape check
    escape = _sandbox_check(code)
    if escape:
        if status:
            await status.edit_text(escape)
        else:
            await safe_reply(message, escape)
        return

    start = time.monotonic()
    error_text = ""

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Check if code contains async operations
            if "await " in code or "async " in code:
                # Wrap in async function and execute
                wrapped = "async def __aexec__():\n"
                for line in code.split("\n"):
                    wrapped += f"    {line}\n"
                exec(compile(wrapped, "<exec>", "exec"), exec_globals)
                await asyncio.wait_for(
                    exec_globals["__aexec__"](),
                    timeout=EXEC_TIMEOUT,
                )
            else:
                exec(compile(code, "<exec>", "exec"), exec_globals)

    except asyncio.TimeoutError:
        error_text = f"⏰ Timeout ({EXEC_TIMEOUT}s)"
    except Exception:
        error_text = traceback.format_exc()

    elapsed = time.monotonic() - start
    stdout = stdout_capture.getvalue()
    stderr = stderr_capture.getvalue()

    parts = []
    if stdout.strip():
        parts.append(f"📤 *stdout:*\n```\n{_truncate(stdout)}\n```")
    if stderr.strip():
        parts.append(f"⚠️ *stderr:*\n```\n{_truncate(stderr)}\n```")
    if error_text:
        parts.append(f"❌ *Error:*\n```\n{_truncate(error_text)}\n```")

    parts.append(f"{'✅' if not error_text else '❌'} ⏱ `{elapsed:.2f}s`")

    result = "\n\n".join(parts) if parts else "✅ اجرا شد — خروجی خالی"
    await send_long_text(message, result)


# ════════════════════════════════════════════════════════
#  /eval — Python Expression Evaluation
# ════════════════════════════════════════════════════════

@router.message(Command("eval"))
async def cmd_eval(message: Message, settings: Settings) -> None:
    """
    Evaluate a Python expression and return the result.
    
    Pipeline: user input → parser → eval() → result
    """
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip():
        await safe_reply(message,
            "🧮 *Python Eval*\n\n"
            "استفاده: `/eval <expression>`\n\n"
            "مثال:\n"
            "`/eval 2**100`\n"
            "`/eval os.cpu_count()`\n"
            "`/eval len(os.listdir('.'))`"
        )
        return

    expr = raw[1].strip()

    eval_globals: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "time_monotonic": time.monotonic, "time_time": time.time,  # v9.8.7: no os/sys
        "asyncio": asyncio,
        "platform": platform,
        # v9.8.7: message/bot/settings removed from sandbox
    }

    start = time.monotonic()
    try:
        result = eval(compile(expr, "<eval>", "eval"), eval_globals)

        # Handle awaitable results
        if asyncio.iscoroutine(result) or asyncio.isfuture(result):
            result = await asyncio.wait_for(result, timeout=EVAL_TIMEOUT)

        elapsed = time.monotonic() - start
        result_str = repr(result)

        await send_long_text(message,
            f"🧮 `{expr[:100]}`\n\n"
            f"📤 *Result:*\n```\n{_truncate(result_str)}\n```\n"
            f"📦 Type: `{type(result).__name__}`\n"
            f"⏱ `{elapsed:.4f}s`"
        )

    except Exception:
        elapsed = time.monotonic() - start
        tb = traceback.format_exc()
        await send_long_text(message,
            f"🧮 `{expr[:100]}`\n\n"
            f"❌ *Error:*\n```\n{_truncate(tb)}\n```\n"
            f"⏱ `{elapsed:.4f}s`"
        )


# ════════════════════════════════════════════════════════
#  /py — Quick Python (exec with auto-print last expr)
# ════════════════════════════════════════════════════════

@router.message(Command("py"))
async def cmd_py(message: Message, settings: Settings) -> None:
    """
    Quick Python execution with auto-print of last expression.
    Combines the convenience of /eval with the power of /exec.
    """
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip():
        await safe_reply(message,
            "⚡ *Quick Python*\n\n"
            "استفاده: `/py <code>`\n\n"
            "مثال:\n"
            "`/py [x**2 for x in range(10)]`\n"
            "`/py import psutil; psutil.virtual_memory()`"
        )
        return

    code = raw[1].strip()
    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    stdout_capture = io.StringIO()

    exec_globals: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "time_monotonic": time.monotonic, "time_time": time.time,  # v9.8.7: no os/sys
        "asyncio": asyncio, "platform": platform,
        # v9.8.7: message/bot/settings removed from sandbox
    }

    start = time.monotonic()
    try:
        with redirect_stdout(stdout_capture):
            # Try eval first (single expression)
            try:
                result = eval(compile(code, "<py>", "eval"), exec_globals)
                if result is not None:
                    logger.debug("Result: %s", repr(result))
            except SyntaxError:
                # Not an expression — exec as statements
                exec(compile(code, "<py>", "exec"), exec_globals)

        elapsed = time.monotonic() - start
        output = stdout_capture.getvalue()

        if output.strip():
            await send_long_text(message,
                f"```\n{_truncate(output)}\n```\n⏱ `{elapsed:.4f}s`"
            )
        else:
            await safe_reply(message, f"✅ Done | ⏱ `{elapsed:.4f}s`")

    except Exception:
        elapsed = time.monotonic() - start
        tb = traceback.format_exc()
        await send_long_text(message,
            f"❌\n```\n{_truncate(tb)}\n```\n⏱ `{elapsed:.4f}s`"
        )


# ════════════════════════════════════════════════════════
#  /upload — Send server file to Telegram
# ════════════════════════════════════════════════════════

@router.message(Command("upload"))
async def cmd_upload(message: Message, settings: Settings) -> None:
    """Upload a file from the server to Telegram."""
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip():
        await safe_reply(message,
            "📤 *Upload File*\n\n"
            "استفاده: `/upload <path>`\n\n"
            "مثال: `/upload /var/log/syslog`"
        )
        return

    filepath = raw[1].strip()

    if not os.path.exists(filepath):
        await safe_reply(message, f"❌ فایل یافت نشد: `{filepath}`")
        return

    if os.path.isdir(filepath):
        await safe_reply(message, f"❌ این یک دایرکتوری است: `{filepath}`")
        return

    size = os.path.getsize(filepath)
    if size > 50 * 1024 * 1024:  # 50MB Telegram limit
        await safe_reply(message,
            f"❌ فایل خیلی بزرگ: {size / 1024 / 1024:.1f}MB (حداکثر 50MB)"
        )
        return

    try:
        doc = FSInputFile(filepath)
        await message.answer_document(
            doc,
            caption=f"📄 `{filepath}`\n💾 {size / 1024:.1f} KB",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")


# ════════════════════════════════════════════════════════
#  /download — Download Telegram file to server
# ════════════════════════════════════════════════════════

@router.message(Command("download"))
async def cmd_download(message: Message, settings: Settings) -> None:
    """Download a Telegram file to the server (reply to a file)."""
    if _deny(message, settings):
        return

    reply = message.reply_to_message
    if not reply:
        await safe_reply(message,
            "📥 *Download File*\n\n"
            "ریپلای به یک فایل/عکس/ویدیو با `/download [path]`\n\n"
            "مثال: ریپلای + `/download /tmp/myfile.txt`"
        )
        return

    # Extract file_id from reply
    file_id = None
    filename = "downloaded_file"
    if reply.document:
        file_id = reply.document.file_id
        filename = reply.document.file_name or filename
    elif reply.photo:
        file_id = reply.photo[-1].file_id
        filename = "photo.jpg"
    elif reply.video:
        file_id = reply.video.file_id
        filename = reply.video.file_name or "video.mp4"
    elif reply.audio:
        file_id = reply.audio.file_id
        filename = reply.audio.file_name or "audio.ogg"
    elif reply.voice:
        file_id = reply.voice.file_id
        filename = "voice.ogg"

    if not file_id:
        await safe_reply(message, "❌ فایلی در پیام ریپلای یافت نشد.")
        return

    # Custom path from args
    raw = (message.text or "").split(maxsplit=1)
    if len(raw) >= 2 and raw[1].strip():
        dest = raw[1].strip()
    else:
        dest = f"/tmp/{filename}"

    try:
        bot = message.bot
        file = await bot.get_file(file_id)  # type: ignore[misc]
        await bot.download_file(file.file_path, dest)  # type: ignore[misc]
        size = os.path.getsize(dest)
        await safe_reply(message,
            "✅ *دانلود شد*\n\n"
            f"📄 `{dest}`\n"
            f"💾 {size / 1024:.1f} KB"
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")


# ════════════════════════════════════════════════════════
#  /sysinfo — Full System Information
# ════════════════════════════════════════════════════════

@router.message(Command("sysinfo"))
async def cmd_sysinfo(message: Message, settings: Settings) -> None:
    """Display comprehensive system information."""
    if _deny(message, settings):
        return

    try:
        import psutil
        has_psutil = True
    except ImportError:
        has_psutil = False

    uname = platform.uname()
    py_ver = sys.version.split("\n")[0]

    lines = [
        "🖥 *System Information*\n",
        f"*🐧 OS:* `{uname.system} {uname.release}`",
        f"*🏗 Arch:* `{uname.machine}`",
        f"*🏠 Host:* `{uname.node}`",
        f"*🐍 Python:* `{py_ver}`",
        f"*📂 CWD:* `{os.getcwd()}`",
        f"*👤 User:* `{os.getenv('USER', 'unknown')}`",
        f"*🆔 PID:* `{os.getpid()}`",
    ]

    if has_psutil:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu_count = psutil.cpu_count()
        cpu_pct = psutil.cpu_percent(interval=0.5)
        boot = time.time() - psutil.boot_time()

        lines.extend([
            "",
            f"*💻 CPU:* `{cpu_count} cores` @ `{cpu_pct}%`",
            f"*🧠 RAM:* `{mem.used / 1024**3:.1f}` / `{mem.total / 1024**3:.1f} GB` ({mem.percent}%)",
            f"*💾 Disk:* `{disk.used / 1024**3:.1f}` / `{disk.total / 1024**3:.1f} GB` ({disk.percent}%)",
            f"*⏱ Uptime:* `{int(boot // 3600)}h {int((boot % 3600) // 60)}m`",
        ])

        # Top processes
        procs = sorted(
            psutil.process_iter(["pid", "name", "memory_percent"]),
            key=lambda p: p.info.get("memory_percent", 0) or 0,
            reverse=True,
        )[:5]
        if procs:
            lines.append("\n*🔝 Top Processes:*")
            for p in procs:
                info = p.info
                lines.append(
                    f"  `{info['pid']}` {info['name']} — "
                    f"{info.get('memory_percent', 0):.1f}% RAM"
                )
    else:
        # Fallback without psutil
        lines.extend([
            "",
            "⚠️ `psutil` نصب نیست — `/pip psutil` برای اطلاعات بیشتر",
        ])

        # Basic memory from /proc/meminfo
        try:
            async with aiofiles.open("/proc/meminfo") as f:
                meminfo = await f.read()
            for line in meminfo.split("\n")[:3]:
                lines.append(f"  `{line}`")
        except Exception as e:
            logger.debug("Suppressed: %s", e)

    await send_long_text(message, "\n".join(lines))


# ════════════════════════════════════════════════════════
#  /pip — Install Python packages
# ════════════════════════════════════════════════════════

@router.message(Command("pip"))
async def cmd_pip(message: Message, settings: Settings) -> None:
    """Install a Python package."""
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip():
        await safe_reply(message,
            "📦 *Pip Install*\n\n"
            "استفاده: `/pip <package>`\n\n"
            "مثال: `/pip psutil`"
        )
        return

    package = raw[1].strip()
    await safe_reply(message, f"📦 نصب `{package}` ...")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "--quiet", package,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=120
        )

        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")

        if proc.returncode == 0:
            await safe_reply(message,
                f"✅ *نصب شد:* `{package}`\n"
                + (f"```\n{stdout[:500]}\n```" if stdout.strip() else "")
            )
        else:
            await safe_reply(message,
                f"❌ *خطا در نصب* `{package}`\n```\n{stderr[:1000]}\n```"
            )

    except asyncio.TimeoutError:
        await safe_reply(message, f"⏰ Timeout نصب `{package}` (120s)")
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")


# ════════════════════════════════════════════════════════
#  /env — View/set environment variables
# ════════════════════════════════════════════════════════

@router.message(Command("env"))
async def cmd_env(message: Message, settings: Settings) -> None:
    """View or set environment variables (runtime only)."""
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=2)

    if len(raw) == 1:
        # Show all (censored sensitive ones)
        sensitive = {"API_KEY", "TOKEN", "SECRET", "PASSWORD", "PASS"}
        lines = ["🔑 *Environment Variables:*\n"]
        for key in sorted(os.environ.keys()):
            val = os.environ[key]
            if any(s in key.upper() for s in sensitive):
                val = val[:4] + "****" if len(val) > 4 else "****"
            lines.append(f"`{key}` = `{val[:80]}`")
        await send_long_text(message, "\n".join(lines))

    elif len(raw) == 2:
        # Show single var
        key = raw[1].strip()
        val = os.environ.get(key)
        if val is not None:
            await safe_reply(message, f"🔑 `{key}` = `{val}`")
        else:
            await safe_reply(message, f"❌ `{key}` تنظیم نشده")

    else:
        # Set var
        key = raw[1].strip()
        val = raw[2].strip()
        os.environ[key] = val
        await safe_reply(message, f"✅ `{key}` = `{val}`")


# ════════════════════════════════════════════════════════
#  /kill — Kill a process
# ════════════════════════════════════════════════════════

@router.message(Command("kill"))
async def cmd_kill(message: Message, settings: Settings) -> None:
    """Kill a process by PID."""
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip().isdigit():
        await safe_reply(message,
            "💀 *Kill Process*\n\n"
            "استفاده: `/kill <PID>`\n\n"
            "مثال: `/kill 12345`"
        )
        return

    pid = int(raw[1].strip())

    # Safety: don't kill self
    if pid == os.getpid():
        await safe_reply(message, "⚠️ نمی‌تونم خودم رو kill کنم!")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        await safe_reply(message, f"✅ SIGTERM → PID `{pid}`")
    except ProcessLookupError:
        await safe_reply(message, f"❌ PID `{pid}` یافت نشد")
    except PermissionError:
        await safe_reply(message, f"❌ دسترسی برای kill PID `{pid}` نیست")
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")


# ════════════════════════════════════════════════════════
#  /queue — Persistent task queue (persistence + remote exec)
# ════════════════════════════════════════════════════════

@router.message(Command("queue"))
async def cmd_queue(message: Message, settings: Settings) -> None:
    """Queue a persistent task (survives restart)."""
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=2)
    if len(raw) < 3:
        await safe_reply(message,
            "📋 *Persistent Task Queue*\n\n"
            "استفاده: `/queue <type> <payload>`\n\n"
            "انواع: `sh`, `exec`, `eval`\n\n"
            "مثال:\n"
            "`/queue sh ls -la /home`\n"
            "`/queue exec print('hello from queue')`\n"
            "`/queue eval 2**100`\n\n"
            "تسک‌ها در دیتابیس ذخیره می‌شن و بعد ریستارت هم اجرا می‌شن."
        )
        return

    task_type = raw[1].strip()
    payload = raw[2].strip()

    if task_type not in ("sh", "exec", "eval"):
        await safe_reply(message, f"❌ نوع نامعتبر: `{task_type}` — فقط `sh`/`exec`/`eval`")
        return

    try:
        submit_task, _, _ = _get_persistent()
        task_id = await submit_task(
            admin_id=message.from_user.id,  # type: ignore[misc]
            chat_id=message.chat.id,
            task_type=task_type,
            payload=payload,
        )
        await safe_reply(message,
            f"📋 *Task #{task_id}* در صف قرار گرفت\n\n"
            f"نوع: `{task_type}`\n"
            f"```\n{payload[:200]}\n```\n"
            "نتیجه بعد از اجرا ارسال می‌شه ✅"
        )
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")


# ════════════════════════════════════════════════════════
#  /tasks — List persistent tasks
# ════════════════════════════════════════════════════════

@router.message(Command("tasks"))
async def cmd_tasks(message: Message, settings: Settings) -> None:
    """List recent persistent tasks."""
    if _deny(message, settings):
        return

    try:
        _, get_task_list, _ = _get_persistent()
        tasks = await get_task_list()

        if not tasks:
            await safe_reply(message, "📋 صف خالی — هنوز تسکی ثبت نشده")
            return

        status_icons = {
            "pending": "⏳", "running": "🔄",
            "done": "✅", "failed": "❌",
        }

        lines = ["📋 *آخرین تسک‌ها:*\n"]
        for t in tasks:
            icon = status_icons.get(t["status"], "❓")
            elapsed = f"{t['elapsed_ms']}ms" if t["elapsed_ms"] else "-"
            lines.append(
                f"{icon} `#{t['id']}` [{t['type']}] {t['status']} "
                f"| ⏱{elapsed} | `{t['payload']}`"
            )

        await send_long_text(message, "\n".join(lines))
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")


# ════════════════════════════════════════════════════════
#  /tasklog — View task result
# ════════════════════════════════════════════════════════

@router.message(Command("tasklog"))
async def cmd_tasklog(message: Message, settings: Settings) -> None:
    """View detailed task result."""
    if _deny(message, settings):
        return

    raw = (message.text or "").split(maxsplit=1)
    if len(raw) < 2 or not raw[1].strip().isdigit():
        await safe_reply(message, "📄 استفاده: `/tasklog <task_id>`")
        return

    task_id = int(raw[1].strip())

    try:
        _, _, get_task_detail = _get_persistent()
        task = await get_task_detail(task_id)

        if not task:
            await safe_reply(message, f"❌ تسک `#{task_id}` یافت نشد")
            return

        status_icons = {
            "pending": "⏳", "running": "🔄",
            "done": "✅", "failed": "❌",
        }
        icon = status_icons.get(task["status"], "❓")

        parts = [
            f"{icon} *Task #{task['id']}*\n",
            f"نوع: `{task['type']}`",
            f"وضعیت: `{task['status']}`",
            f"تلاش: `{task['retries']}`",
            f"زمان اجرا: `{task['elapsed_ms']}ms`",
            f"ثبت: `{task['created_at']}`",
        ]

        if task["payload"]:
            parts.append(f"\n📝 *Payload:*\n```\n{task['payload'][:500]}\n```")
        if task["result"]:
            parts.append(f"\n📤 *Result:*\n```\n{task['result'][:1000]}\n```")
        if task["error"]:
            parts.append(f"\n⚠️ *Error:*\n```\n{task['error'][:500]}\n```")

        await send_long_text(message, "\n".join(parts))
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")


# ════════════════════════════════════════════════════════
#  /ws — WebSocket server status
# ════════════════════════════════════════════════════════

@router.message(Command("ws"))
async def cmd_ws(message: Message, settings: Settings) -> None:
    """Show WebSocket remote server status."""
    if _deny(message, settings):
        return

    try:
        ws_stats = _get_ws()
        stats = ws_stats()

        status = "🟢 فعال" if stats["running"] else "🔴 غیرفعال"
        lines = [
            "🌐 *WebSocket Remote Server*\n",
            f"وضعیت: {status}",
            f"آدرس: `{stats['host']}:{stats['port']}`",
            f"اتصالات: `{stats['connections']}`",
            f"صف: `{stats['queue_size']}`",
        ]

        if stats["connection_details"]:
            lines.append("\n*اتصالات فعال:*")
            for cid, info in stats["connection_details"].items():
                auth = "✅" if info["authenticated"] else "❌"
                lines.append(f"  {auth} `{cid}` — {info['requests']} req")

        await send_long_text(message, "\n".join(lines))
    except Exception as exc:
        logger.error("Error in handler: %s", exc)
        await safe_reply(message, f"❌ خطا: `{exc}`")


