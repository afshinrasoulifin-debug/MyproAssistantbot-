
"""Agent layer — autonomous AI agents."""
try:
    from arki_project.infrastructure.agents.ai_agent import InfraAIAgent
    from arki_project.infrastructure.agents.workflow_agent import InfraWorkflowAgent
    from arki_project.infrastructure.agents.orchestration_agent import OrchestrationAgent
    from arki_project.infrastructure.agents.assistant_agent import InfraAssistantAgent
    from arki_project.infrastructure.agents.remote_agent import RemoteAgent
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.agents.ai_agent import InfraAIAgent
        from infrastructure.agents.workflow_agent import InfraWorkflowAgent
        from infrastructure.agents.orchestration_agent import OrchestrationAgent
        from infrastructure.agents.assistant_agent import InfraAssistantAgent
        from infrastructure.agents.remote_agent import RemoteAgent
    except (ImportError, ModuleNotFoundError):
        InfraAIAgent = None  # type: ignore
        InfraWorkflowAgent = None  # type: ignore
        OrchestrationAgent = None  # type: ignore
        InfraAssistantAgent = None  # type: ignore
        RemoteAgent = None  # type: ignore


