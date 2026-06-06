
"""architecture.engine — Processing engines for AI bot intelligence"""
from .workflow import WorkflowEngine as ArchWorkflowEngine
from .automation import AutomationEngine
from .orchestration import OrchestrationEngine
from .execution import ExecutionEngine, ProcessingEngine
from .template import TemplateEngine
from .smart import SmartEngine, AdaptiveEngine, PerformanceEngine, ActionEngine

__all__ = ["AutomationRule", "AutomationEngine", "ExecutionResult", "ExecutionEngine", "ProcessingEngine", "OrchestrationPlan", "OrchestrationEngine", "SmartEngine", "AdaptiveEngine", "PerformanceEngine", "ActionEngine", "Template", "TemplateEngine", "StepStatus", "WorkflowStep", "WorkflowRun", "WorkflowEngine"]


