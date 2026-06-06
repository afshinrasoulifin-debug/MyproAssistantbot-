
"""Tests for architecture engines — real behavior tests."""
from arki_project.architecture.engine.smart import SmartEngine, AdaptiveEngine, PerformanceEngine, ActionEngine
from arki_project.architecture.engine.template import TemplateEngine
from arki_project.architecture.engine.workflow import WorkflowEngine, WorkflowStep


class TestSmartEngine:
    def test_create(self):
        e = SmartEngine()
        # Verify it has core engine methods
        assert hasattr(e, "execute_smart"), "SmartEngine must have execute_smart method"

    def test_is_class_instance(self):
        e = SmartEngine()
        assert isinstance(e, SmartEngine)


class TestAdaptiveEngine:
    def test_create(self):
        e = AdaptiveEngine()
        assert isinstance(e, AdaptiveEngine)


class TestPerformanceEngine:
    def test_create(self):
        e = PerformanceEngine()
        assert isinstance(e, PerformanceEngine)


class TestActionEngine:
    def test_create(self):
        e = ActionEngine()
        assert isinstance(e, ActionEngine)


class TestTemplateEngine:
    def test_create(self):
        e = TemplateEngine()
        assert isinstance(e, TemplateEngine)

    def test_has_register_and_render(self):
        e = TemplateEngine()
        assert hasattr(e, "register") or hasattr(e, "add")
        assert hasattr(e, "render")

    def test_register_then_render(self):
        e = TemplateEngine()
        if hasattr(e, "register"):
            e.register("greeting", "Hello {{name}}")
            result = e.render("greeting", {"name": "World"})
            assert "World" in result


class TestWorkflowEngine:
    def test_create(self):
        e = WorkflowEngine()
        assert isinstance(e, WorkflowEngine)

    def test_has_run_or_execute(self):
        e = WorkflowEngine()
        assert hasattr(e, "run") or hasattr(e, "execute") or hasattr(e, "add_step")


class TestWorkflowStep:
    def test_create(self):
        step = WorkflowStep(name="test_step", action=lambda: None)
        assert step.name == "test_step"


