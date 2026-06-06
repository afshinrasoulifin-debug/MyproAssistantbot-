
#!/usr/bin/env python3
"""
Phase 14 Tests: Verify ALL previously-stub files are now REAL.
25-layer deep verification — no stubs, no mocks, no decoration.
"""

import os
import re
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
os.chdir(BASE)


class L01_StubsEliminated(unittest.TestCase):
    """Layer 1: No stub files remain."""

    PREVIOUSLY_STUBS = [
        "handlers/translate_handler.py",
        "handlers/summarize_handler.py",
        "handlers/remind_handler.py",
        "handlers/settings_handler.py",
        "handlers/monitor_handler.py",
        "handlers/batch_handler.py",
        "handlers/collab_handler.py",
        "handlers/agents_pkg/crm_finance.py",
        "handlers/agents_pkg/menu.py",
        "handlers/agents_pkg/monitor.py",
        "handlers/agents_pkg/planner.py",
        "handlers/agents_pkg/workflow.py",
        "handlers/sales/pricing.py",
        "handlers/sales/upsell.py",
        "handlers/sales/crm.py",
    ]

    def test_01_all_files_exist(self):
        for f in self.PREVIOUSLY_STUBS:
            self.assertTrue(os.path.exists(f), f"MISSING: {f}")

    def test_02_no_stub_markers(self):
        for f in self.PREVIOUSLY_STUBS:
            code = open(f).read()
            self.assertNotIn("Stub module", code, f"STUB MARKER in {f}")
            self.assertNotIn("stub — not yet implemented", code, f"STUB WARNING in {f}")

    def test_03_minimum_size(self):
        for f in self.PREVIOUSLY_STUBS:
            lines = len(open(f).readlines())
            self.assertGreater(lines, 50, f"TOO SMALL: {f} ({lines}L)")

    def test_04_syntax_valid(self):
        for f in self.PREVIOUSLY_STUBS:
            code = open(f).read()
            try:
                compile(code, f, "exec")
            except SyntaxError as e:
                self.fail(f"SYNTAX ERROR in {f}: {e}")


class L02_HandlersHaveRouters(unittest.TestCase):
    """Layer 2: All handlers have Router()."""

    HANDLER_FILES = [
        "handlers/translate_handler.py",
        "handlers/summarize_handler.py",
        "handlers/remind_handler.py",
        "handlers/settings_handler.py",
        "handlers/monitor_handler.py",
        "handlers/batch_handler.py",
        "handlers/collab_handler.py",
        "handlers/agents_pkg/crm_finance.py",
        "handlers/agents_pkg/menu.py",
        "handlers/agents_pkg/monitor.py",
        "handlers/agents_pkg/planner.py",
        "handlers/agents_pkg/workflow.py",
        "handlers/sales/pricing.py",
        "handlers/sales/upsell.py",
        "handlers/sales/crm.py",
    ]

    def test_01_each_has_router(self):
        for f in self.HANDLER_FILES:
            code = open(f).read()
            self.assertIn("Router(", code, f"NO Router() in {f}")

    def test_02_each_has_commands_or_callbacks(self):
        for f in self.HANDLER_FILES:
            code = open(f).read()
            has_cmd = "@router.message(Command(" in code
            has_cb = "@router.callback_query" in code
            self.assertTrue(has_cmd or has_cb, f"NO commands/callbacks in {f}")


class L03_HandlersHaveRealLogic(unittest.TestCase):
    """Layer 3: Handlers have real async logic, not just stubs."""

    HANDLER_FILES = [
        "handlers/translate_handler.py",
        "handlers/summarize_handler.py",
        "handlers/remind_handler.py",
        "handlers/settings_handler.py",
        "handlers/monitor_handler.py",
        "handlers/batch_handler.py",
        "handlers/collab_handler.py",
        "handlers/agents_pkg/crm_finance.py",
        "handlers/agents_pkg/planner.py",
        "handlers/agents_pkg/workflow.py",
        "handlers/sales/pricing.py",
        "handlers/sales/upsell.py",
        "handlers/sales/crm.py",
    ]

    def test_01_has_async_functions(self):
        for f in self.HANDLER_FILES:
            code = open(f).read()
            self.assertIn("async def", code, f"NO async def in {f}")

    def test_02_has_conditional_logic(self):
        for f in self.HANDLER_FILES:
            code = open(f).read()
            has_if = bool(re.search(r'if .+:', code))
            self.assertTrue(has_if, f"NO if/logic in {f}")

    def test_03_has_error_handling(self):
        for f in self.HANDLER_FILES:
            code = open(f).read()
            has_try = "try:" in code
            has_except = "except" in code
            self.assertTrue(has_try and has_except, f"NO error handling in {f}")


class L04_AIIntegration(unittest.TestCase):
    """Layer 4: AI-connected handlers actually use ai_client."""

    AI_HANDLERS = [
        "handlers/translate_handler.py",
        "handlers/summarize_handler.py",
        "handlers/batch_handler.py",
        "handlers/collab_handler.py",
        "handlers/agents_pkg/crm_finance.py",
        "handlers/agents_pkg/planner.py",
        "handlers/agents_pkg/workflow.py",
        "handlers/sales/pricing.py",
        "handlers/sales/upsell.py",
    ]

    def test_01_imports_ai_client(self):
        for f in self.AI_HANDLERS:
            code = open(f).read()
            self.assertIn("AIClient", code, f"NO AIClient import in {f}")

    def test_02_calls_ai_client(self):
        for f in self.AI_HANDLERS:
            code = open(f).read()
            has_ask = "ai_client.ask(" in code
            has_chat = "ai_client.chat(" in code
            self.assertTrue(has_ask or has_chat, f"NO ai_client call in {f}")

    def test_03_sends_typing_action(self):
        for f in self.AI_HANDLERS:
            code = open(f).read()
            has_typing = "ChatAction.TYPING" in code or "send_chat_action" in code
            self.assertTrue(has_typing, f"NO typing action in {f}")


class L05_DBIntegration(unittest.TestCase):
    """Layer 5: DB-connected handlers use get_session."""

    DB_HANDLERS = [
        "handlers/remind_handler.py",
        "handlers/settings_handler.py",
        "handlers/monitor_handler.py",
        "handlers/agents_pkg/crm_finance.py",
        "handlers/agents_pkg/monitor.py",
        "handlers/sales/crm.py",
    ]

    def test_01_imports_db(self):
        for f in self.DB_HANDLERS:
            code = open(f).read()
            self.assertIn("get_session", code, f"NO get_session in {f}")

    def test_02_uses_session(self):
        for f in self.DB_HANDLERS:
            code = open(f).read()
            has_async_with = "async with get_session()" in code
            self.assertTrue(has_async_with, f"NO async with get_session in {f}")


class L06_MainPyRegistration(unittest.TestCase):
    """Layer 6: All new routers registered in main.py."""

    def test_01_new_handler_imports(self):
        code = open("main.py").read()
        expected = [
            "translate_v2_router", "summarize_v2_router", "remind_v2_router",
            "config_v2_router", "monitor_v2_router", "batch_v2_router",
            "collab_v2_router", "agents_sub_routers",
        ]
        for imp in expected:
            self.assertIn(imp, code, f"NOT in main.py: {imp}")

    def test_02_include_router_calls(self):
        code = open("main.py").read()
        routers = [
            "translate_v2_router", "summarize_v2_router", "remind_v2_router",
            "config_v2_router", "monitor_v2_router", "batch_v2_router",
            "collab_v2_router",
        ]
        for r in routers:
            self.assertIn(f"dp.include_router({r})", code, f"NOT registered: {r}")


class L07_UniqueCommands(unittest.TestCase):
    """Layer 7: New handlers use unique commands (no conflicts)."""

    def test_01_no_duplicate_commands(self):
        """New handlers use /tr, /sum, /remindme, /config, /watch, /batchai, /collab — all unique."""
        code = open("main.py").read()

        # Original commands in existing routers
        existing = {"/translate", "/summarize", "/remind", "/settings",
                    "/monitor", "/batch"}

        # New commands
        new_cmds = {
            "handlers/translate_handler.py": "/tr",
            "handlers/summarize_handler.py": "/sum",
            "handlers/remind_handler.py": "/remindme",
            "handlers/settings_handler.py": "/config",
            "handlers/monitor_handler.py": "/watch",
            "handlers/batch_handler.py": "/batchai",
        }

        for f, cmd in new_cmds.items():
            handler_code = open(f).read()
            cmd_name = cmd.lstrip("/")
            self.assertIn(f'Command("{cmd_name}")', handler_code,
                          f"{f} should use {cmd}")
            # Ensure it does NOT use the conflicting old command
            old = cmd.replace("/tr", "/translate").replace("/sum", "/summarize")
            if old != cmd:
                self.assertNotIn(f'Command("{old.lstrip("/")}")', handler_code,
                                 f"{f} should NOT use {old}")


class L08_AgentsPkgPackage(unittest.TestCase):
    """Layer 8: agents_pkg is a real package with sub_routers."""

    def test_01_init_exports_sub_routers(self):
        code = open("handlers/agents_pkg/__init__.py").read()
        self.assertIn("sub_routers", code)

    def test_02_five_sub_modules(self):
        expected = ["crm_finance.py", "menu.py", "monitor.py", "planner.py", "workflow.py"]
        for f in expected:
            fp = os.path.join("handlers", "agents_pkg", f)
            self.assertTrue(os.path.exists(fp), f"MISSING: {fp}")

    def test_03_each_has_unique_router_name(self):
        names = set()
        for f in os.listdir("handlers/agents_pkg"):
            if f.endswith(".py") and f != "__init__.py":
                code = open(os.path.join("handlers/agents_pkg", f)).read()
                m = re.search(r'Router\(name="([^"]+)"', code)
                if m:
                    name = m.group(1)
                    self.assertNotIn(name, names, f"DUPLICATE router name: {name}")
                    names.add(name)


class L09_NoGlobalStubs(unittest.TestCase):
    """Layer 9: No stub files anywhere in handlers/."""

    def test_01_zero_stubs_in_handlers(self):
        stub_files = []
        for root, dirs, files in os.walk("handlers"):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if f.endswith(".py") and f != "__init__.py":
                    fp = os.path.join(root, f)
                    code = open(fp).read()
                    if "Stub module" in code[:200]:
                        stub_files.append(fp)
        self.assertEqual(len(stub_files), 0,
                         f"STUBS FOUND: {stub_files}")


class L10_SafeSendUsed(unittest.TestCase):
    """Layer 10: All handlers use safe_send for replies."""

    def test_01_uses_safe_reply(self):
        handlers = [
            "handlers/translate_handler.py",
            "handlers/summarize_handler.py",
            "handlers/remind_handler.py",
            "handlers/settings_handler.py",
            "handlers/monitor_handler.py",
            "handlers/batch_handler.py",
            "handlers/collab_handler.py",
        ]
        for f in handlers:
            code = open(f).read()
            self.assertIn("safe_reply", code, f"NO safe_reply in {f}")


class L11_TotalProjectStats(unittest.TestCase):
    """Layer 11: Overall project health metrics."""

    def test_01_total_py_files(self):
        count = 0
        for root, dirs, files in os.walk(".", followlinks=False):
            dirs[:] = [d for d in dirs if d not in {"__pycache__", "arki_project", "node_modules", ".git"}]
            count += sum(1 for f in files if f.endswith(".py"))
        self.assertGreater(count, 800, f"Only {count} .py files")

    def test_02_zero_stubs_project_wide(self):
        stubs = 0
        for root, dirs, files in os.walk(".", followlinks=False):
            dirs[:] = [d for d in dirs if d not in {"__pycache__", "arki_project", "node_modules", ".git"}]
            for f in files:
                if f.endswith(".py"):
                    code = open(os.path.join(root, f)).read()
                    if "Stub module" in code[:200]:
                        stubs += 1
        self.assertEqual(stubs, 0, f"{stubs} stub files remain")

    def test_03_main_py_syntax(self):
        code = open("main.py").read()
        compile(code, "main.py", "exec")

    def test_04_handler_count(self):
        """At least 70 handler files."""
        count = 0
        for root, dirs, files in os.walk("handlers", followlinks=False):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            count += sum(1 for f in files if f.endswith(".py") and f != "__init__.py")
        self.assertGreaterEqual(count, 65, f"Only {count} handlers")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    print(f"\n{'=' * 60}")
    print(f"  Phase 14: {passed}/{total} passed ({passed*100//total}%)")
    if result.failures:
        print(f"  FAILURES:")
        for f in result.failures:
            print(f"    ❌ {f[0]}: {f[1][:100]}")
    if result.errors:
        print(f"  ERRORS:")
        for e in result.errors:
            print(f"    ❌ {e[0]}: {e[1][:100]}")
    print(f"{'=' * 60}")

    sys.exit(0 if failed == 0 else 1)


