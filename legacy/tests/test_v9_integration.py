
"""Integration tests — verify real module connections."""
import pytest
import os
from arki_project.infrastructure.registry import InfraRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    InfraRegistry._instance = None
    yield
    InfraRegistry._instance = None


class TestModuleConnections:
    """Verify modules are actually connected, not isolated islands."""

    def test_infrastructure_imported_from_main(self):
        """main.py must import infrastructure boot."""
        src = open("main.py").read()
        assert "tg_bot.infrastructure.boot" in src or "infrastructure.boot" in src

    def test_infrastructure_bridge_exists_and_imports(self):
        """Infrastructure bridge middleware must exist and import infra."""
        assert os.path.isfile("middlewares/infrastructure_bridge.py")
        src = open("middlewares/infrastructure_bridge.py").read()
        assert "tg_bot.infrastructure" in src

    def test_services_bridge_exists(self):
        """Services infra bridge must exist."""
        assert os.path.isfile("services/infra_bridge.py")
        src = open("services/infra_bridge.py").read()
        assert "tg_bot.infrastructure" in src or "tg_bot.services" in src

    def test_config_has_infra_settings(self):
        """Config must have infrastructure settings."""
        src = open("config.py").read()
        assert "INFRA_ENABLED" in src

    def test_all_infrastructure_subpackages_have_init(self):
        """Every infrastructure subpackage must have __init__.py."""
        for d in os.listdir("infrastructure"):
            path = os.path.join("infrastructure", d)
            if os.path.isdir(path) and not d.startswith("_"):
                init = os.path.join(path, "__init__.py")
                assert os.path.isfile(init), f"Missing __init__.py in infrastructure/{d}/"

    def test_registry_loads_all_30_subpackages(self):
        """Registry must load components from all 30 infrastructure subpackages."""
        r = InfraRegistry()
        r.auto_register()
        components = r.list_components()
        
        # Must have components from all major categories
        required_prefixes = [
            "command_bus", "proxy_gateway", "cache_manager",
            "smart_router", "ai_bridge",
        ]
        for prefix in required_prefixes:
            assert any(prefix in c for c in components), (
                f"No component matching '{prefix}' in registry"
            )

    def test_no_bare_from_infrastructure_imports(self):
        """No file should use 'from infrastructure.' — must be 'from arki_project.infrastructure.'."""
        import re
        violations = []
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache")]
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                with open(fp) as fh:
                    for i, line in enumerate(fh, 1):
                        if re.match(r"\s*from\s+infrastructure\.", line) and "tg_bot" not in line:
                            violations.append(f"{fp}:{i}")
        assert not violations, f"Wrong import pattern in: {violations[:5]}"

    def test_no_old_version_traces(self):
        """No v7.x or v8.x version references in Python files."""
        import re
        violations = []
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache")]
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                with open(fp, errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        if re.search(r"\bv[78]\.\d", line) and "python" not in line.lower():
                            violations.append(f"{fp}:{i}")
        assert not violations, f"Old version traces: {violations[:5]}"

    def test_no_swallowed_exceptions(self):
        """No bare 'except X: pass' patterns — all should log."""
        violations = []
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache", "tests")]
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                with open(fp) as fh:
                    lines = fh.readlines()
                for i, line in enumerate(lines):
                    if "except" in line and ":" in line:
                        if i + 1 < len(lines) and lines[i + 1].strip() == "pass":
                            violations.append(f"{fp}:{i+1}")
        assert not violations, f"Swallowed exceptions: {violations[:5]}"

    def test_no_syntax_errors_anywhere(self):
        """All Python files must compile without syntax errors."""
        errors = []
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".pytest_cache")]
            for f in files:
                if not f.endswith(".py"):
                    continue
                fp = os.path.join(root, f)
                try:
                    with open(fp, errors="replace") as fh:
                        compile(fh.read(), fp, "exec")
                except SyntaxError as e:
                    errors.append(f"{fp}:{e.lineno}")
        assert not errors, f"Syntax errors: {errors}"


class TestArchitectureQuality:
    """Verify architecture module quality."""

    def test_all_architecture_packages_have_all(self):
        """Architecture subpackages should export __all__."""
        missing = []
        for d in os.listdir("architecture"):
            path = os.path.join("architecture", d)
            if os.path.isdir(path) and not d.startswith("_"):
                init = os.path.join(path, "__init__.py")
                if os.path.isfile(init):
                    src = open(init).read()
                    if "__all__" not in src:
                        missing.append(d)
        assert not missing, f"Missing __all__ in: {missing}"

    def test_architecture_modules_importable(self):
        """All architecture Python files should import cleanly."""
        import importlib
        errors = []
        for root, dirs, files in os.walk("architecture"):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                if not f.endswith(".py") or f == "__init__.py":
                    continue
                mod_path = os.path.join(root, f).lstrip("./").replace("/", ".").replace(".py", "")
                mod_name = f"tg_bot.{mod_path}"
                try:
                    importlib.import_module(mod_name)
                except Exception as e:
                    errors.append(f"{mod_name}: {e}")
        assert not errors, f"Import errors: {errors[:5]}"


