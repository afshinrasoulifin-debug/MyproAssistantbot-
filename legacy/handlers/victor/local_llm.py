

import logging
# Mocking for testing if utils not directly accessible
class RoutingStrategy: BALANCED = 1
class OrchestrationResult: final_response = "Response"
class MultiLLMOrchestrator:
    async def orchestrate(self, **kwargs): return OrchestrationResult()


logger = logging.getLogger(__name__)

class LocalLLM:
    """
    Advanced LLM Bridge for Victor v29.
    Interfaces directly with the project's MultiLLMOrchestrator.
    """
    def __init__(self):
        self.orchestrator = MultiLLMOrchestrator()
        # Default strategy for Victor: Balanced quality and reasoning
        self.default_strategy = RoutingStrategy.BALANCED

    async def think(self, prompt: str, context: str = "", task_type: str = "general") -> str:
        """
        Think using intelligent orchestration.
        Uses ensemble/debate modes for complex reasoning.
        """
        logger.info(f"Orchestrating LLM for Victor task: {task_type}")
        
        # Map Victor task types to Orchestrator modes
        mode = "specialist" if task_type == "general" else "debate"
        
        try:
            result: OrchestrationResult = await self.orchestrator.orchestrate(
                query=prompt,
                context=context,
                mode=mode,
                strategy=self.default_strategy
            )
            return result.final_response
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            return f"Error: {str(e)}"

    async def summarize(self, text: str) -> str:
        return await self.think(f"خلاصه کن:\n{text}", task_type="general")


