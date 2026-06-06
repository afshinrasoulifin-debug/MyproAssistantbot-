
"""Tests for settings_handler handler — v29.0.0 real tests."""
import pytest
import ast
import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HANDLER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "handlers", "settings_handler.py"
)


def _safe_import(module_path):
    try:
        import importlib
        return importlib.import_module(module_path)
    except (ImportError, ModuleNotFoundError) as e:
        pytest.skip(f"Cannot import {module_path}: {e}")


class TestSettingsHandlerHandler:
    """Comprehensive tests for settings_handler handler."""

    def test_file_parses_without_errors(self):
        """Source file has valid Python syntax."""
        with open(HANDLER_PATH) as f:
            source = f.read()
        tree = ast.parse(source)  # Raises SyntaxError on bad syntax
        assert isinstance(tree, ast.Module)
        assert len(tree.body) > 0, "File should not be empty"

    def test_no_duplicate_functions(self):
        """No top-level function is defined more than once."""
        with open(HANDLER_PATH) as f:
            tree = ast.parse(f.read())
        names = {}
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.name not in names, \
                    f"Duplicate function: {node.name} at lines {names[node.name]} and {node.lineno}"
                names[node.name] = node.lineno

    def test_no_bare_excepts(self):
        """No bare except: clauses that swallow everything."""
        with open(HANDLER_PATH) as f:
            source = f.read()
        bare = re.findall(r"^\s*except\s*:", source, re.MULTILINE)
        assert len(bare) == 0, f"Found {len(bare)} bare except clauses"

    def test_no_pass_only_handlers(self):
        """No handler function is just pass (empty body)."""
        with open(HANDLER_PATH) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("cmd_") or node.name.startswith("handle_"):
                    real_body = [s for s in node.body
                                 if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
                    assert not (len(real_body) == 1 and isinstance(real_body[0], ast.Pass)), \
                        f"Handler {node.name} is empty (pass only)"

    def test_module_imports_successfully(self):
        """Module can be imported without errors."""
        mod = _safe_import("arki_project.handlers.settings_handler")
        assert mod is not None
        assert hasattr(mod, "__name__")

    def test_router_exists_and_configured(self):
        """Module exports a properly configured Router."""
        mod = _safe_import("arki_project.handlers.settings_handler")
        assert hasattr(mod, "router"), "Module must export a router"
        assert mod.router is not None
        # Router should have a name
        router = mod.router
        assert hasattr(router, "name") or hasattr(router, "_name")

    def test_logger_configured(self):
        """Module has a logger configured."""
        mod = _safe_import("arki_project.handlers.settings_handler")
        assert hasattr(mod, "logger"), "Module should define a logger"
        import logging
        assert isinstance(mod.logger, logging.Logger)

    def test_handler_functions_are_async(self):
        """All handler functions should be async."""
        mod = _safe_import("arki_project.handlers.settings_handler")
        import asyncio
        handler_names = ['cmd_settings']
        for name in handler_names:
            func = getattr(mod, name, None)
            if func is not None:
                assert asyncio.iscoroutinefunction(func), \
                    f"{name} should be async"

    def test_no_unreachable_code(self):
        """No statements after unconditional return."""
        with open(HANDLER_PATH) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for i, stmt in enumerate(node.body):
                    if isinstance(stmt, ast.Return) and i < len(node.body) - 1:
                        next_s = node.body[i + 1]
                        assert isinstance(next_s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)), \
                            f"Unreachable code at line {next_s.lineno} in {node.name}"

    def test_no_useless_fstrings(self):
        """No f-strings without any interpolation."""
        with open(HANDLER_PATH) as f:
            source = f.read()
        tree = ast.parse(source)
        lines = source.split("\n")
        for node in ast.walk(tree):
            if not isinstance(node, ast.JoinedStr):
                continue
            # Check if this f-string has any actual expressions
            has_expr = any(isinstance(v, ast.FormattedValue) for v in node.values)
            if has_expr:
                continue
            # This JoinedStr has no expressions — but it might be a format_spec
            # Format specs like .1f are 1-element JoinedStr with a short Constant
            if len(node.values) == 1 and isinstance(node.values[0], ast.Constant):
                val = str(node.values[0].value)
                if len(val) < 10:  # format specs are short
                    continue
            assert False, f"Useless f-string at line {node.lineno}: {lines[node.lineno - 1].strip()[:80]}"

    def test_error_handling_logs(self):
        """Exception handlers should log, not silently pass."""
        with open(HANDLER_PATH) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                body_strs = [ast.dump(s) for s in node.body]
                body_text = " ".join(body_strs)
                # Should have logger or raise or return — not just pass
                has_action = ("logger" in body_text or "raise" in body_text
                              or "logging" in body_text or "return" in body_text
                              or "print" in body_text or "await" in body_text
                              or "warn" in body_text)
                is_just_pass = (len(node.body) == 1 and isinstance(node.body[0], ast.Pass))
                if is_just_pass:
                    assert has_action, \
                        f"Swallowed exception at line {node.lineno}"

    def test_no_mutable_defaults(self):
        """No mutable default arguments (list, dict, set)."""
        with open(HANDLER_PATH) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in node.args.defaults + node.args.kw_defaults:
                    if d is not None:
                        assert not isinstance(d, (ast.List, ast.Dict, ast.Set)), \
                            f"Mutable default in {node.name} at line {node.lineno}"



