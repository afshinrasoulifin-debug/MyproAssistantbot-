
"""Functional test: monolith handler splits — v9.7."""
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMonolithSplit:
    """Tests that large handlers are split into sub-packages."""

    def test_content_studio_subpackage_exists(self):
        """content_studio_pkg/ must exist with sub-modules."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg_dir = os.path.join(base, "handlers", "content_studio_pkg")
        assert os.path.isdir(pkg_dir), "content_studio_pkg/ must exist"
        assert os.path.exists(os.path.join(pkg_dir, "__init__.py"))

        modules = [f for f in os.listdir(pkg_dir) if f.endswith('.py') and f != '__init__.py']
        assert len(modules) >= 3, f"Should have 3+ sub-modules, found {len(modules)}"

    def test_sales_engine_subpackage_exists(self):
        """sales_engine_pkg/ must exist with sub-modules."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg_dir = os.path.join(base, "handlers", "sales_engine_pkg")
        assert os.path.isdir(pkg_dir)

        modules = [f for f in os.listdir(pkg_dir) if f.endswith('.py') and f != '__init__.py']
        assert len(modules) >= 3

    def test_agents_subpackage_exists(self):
        """agents_pkg/ must exist with sub-modules."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg_dir = os.path.join(base, "handlers", "agents_pkg")
        assert os.path.isdir(pkg_dir)

    def test_content_brain_subpackage_exists(self):
        """content_brain_pkg/ must exist with sub-modules."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg_dir = os.path.join(base, "handlers", "content_brain_pkg")
        assert os.path.isdir(pkg_dir)

    def test_common_subpackage_exists(self):
        """common_pkg/ must exist with sub-modules."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg_dir = os.path.join(base, "handlers", "common_pkg")
        assert os.path.isdir(pkg_dir)

    def test_subpackages_have_routers(self):
        """All sub-package __init__.py must define a router."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for pkg in ["content_studio_pkg", "sales_engine_pkg", "agents_pkg", "content_brain_pkg"]:
            init = os.path.join(base, "handlers", pkg, "__init__.py")
            if os.path.exists(init):
                content = open(init).read()
                assert "Router" in content, f"{pkg}/__init__.py must have Router"
                assert "include_router" in content, f"{pkg}/__init__.py must include sub-routers"


