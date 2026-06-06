
"""
extra/routes/ — Modular route handlers
Split from the monolithic extra/router.py (47k lines).
Each file handles a specific command group.
"""
try:
    from arki_project.extra.routes.apex_mode import router as god_router
    from arki_project.extra.routes.model_select import router as model_router
    from arki_project.extra.routes.eval_routes import router as eval_router
except (ImportError, ModuleNotFoundError):
    try:
        from extra.routes.apex_mode import router as god_router
        from extra.routes.model_select import router as model_router
        from extra.routes.eval_routes import router as eval_router
    except (ImportError, ModuleNotFoundError):
        god_router = None  # type: ignore
        model_router = None  # type: ignore
        eval_router = None  # type: ignore

__all__ = ["god_router", "model_router", "eval_router"]


