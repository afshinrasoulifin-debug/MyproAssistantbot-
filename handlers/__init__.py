
"""
tg_bot/handlers — All bot command and event handlers.

Router registration order matters! See main.py for the
canonical order (specific commands first, catch-all LAST).
"""

# v10.3: Victor Independent Intelligence
try:
    from arki_project.handlers import victor  # noqa: F401
except (ImportError, ModuleNotFoundError):
    try:
        from handlers import victor  # noqa: F401
    except (ImportError, ModuleNotFoundError):
        victor = None  # type: ignore


