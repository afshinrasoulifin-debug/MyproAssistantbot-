
"""
api_builder_pkg/pipeline_executor.py — PipelineExecutor
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PipelineExecutor:
    """Executes multi-step model pipelines."""
    
    def __init__(self, api_builder: "APIBuilderAgent"):
        self._builder = api_builder
        self._pipelines: Dict[str, Pipeline] = {}
        self._execution_log: List[Dict] = []
    
    def create_pipeline(self, name: str, description: str = "") -> Pipeline:
        p = Pipeline(name=name, description=description)
        self._pipelines[p.pipeline_id] = p
        return p
    
    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        return self._pipelines.get(pipeline_id)
    
    def list_pipelines(self) -> List[Dict]:
        return [
            {
                "id": p.pipeline_id,
                "name": p.name,
                "description": p.description,
                "steps": len(p.steps),
                "created_at": p.created_at,
            }
            for p in self._pipelines.values()
        ]
    
    async def execute(self, pipeline_id: str, initial_input: str,
                      user_id: str = "system") -> Dict[str, Any]:
        """Execute a pipeline end-to-end."""
        pipeline = self._pipelines.get(pipeline_id)
        if not pipeline:
            return {"error": f"Pipeline {pipeline_id} not found"}
        
        t0 = time.time()
        results = []
        prev_output = ""
        current_input = initial_input
        
        for i, step in enumerate(pipeline.steps):
            step_t0 = time.time()
            
            # Check condition — v29.0: safe AST evaluator (NO eval())
            if step.condition:
                try:
                    if not _safe_eval_condition(step.condition, prev_output):
                        results.append({
                            "step": i + 1,
                            "name": step.name,
                            "skipped": True,
                            "reason": f"Condition not met: {step.condition}",
                        })
                        continue
                except Exception as cond_err:
                    results.append({
                        "step": i + 1,
                        "name": step.name,
                        "skipped": True,
                        "reason": f"Condition error: {cond_err}",
                    })
                    continue
            
            # Build input
            if step.input_transform:
                prompt = step.input_transform.replace(
                    "{prev_output}", prev_output
                ).replace(
                    "{original_input}", initial_input
                )
            else:
                prompt = prev_output if prev_output else current_input
            
            # Execute
            try:
                response = await self._builder.quick_chat(
                    step.model_key, prompt,
                    system_prompt=step.system_prompt,
                    temperature=step.temperature,
                    max_tokens=step.max_tokens,
                )
                step_latency = (time.time() - step_t0) * 1000
                
                results.append({
                    "step": i + 1,
                    "name": step.name,
                    "model": step.model_key,
                    "success": True,
                    "output_length": len(response),
                    "latency_ms": round(step_latency, 1),
                    "output_preview": response[:200],
                })
                prev_output = response
                
            except Exception as e:
                step_latency = (time.time() - step_t0) * 1000
                results.append({
                    "step": i + 1,
                    "name": step.name,
                    "model": step.model_key,
                    "success": False,
                    "error": str(e),
                    "latency_ms": round(step_latency, 1),
                })
                # Pipeline continues — prev_output stays the same
        
        total_latency = (time.time() - t0) * 1000
        execution_record = {
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline.name,
            "total_steps": len(pipeline.steps),
            "executed_steps": len([r for r in results if not r.get("skipped")]),
            "successful_steps": len([r for r in results if r.get("success")]),
            "total_latency_ms": round(total_latency, 1),
            "final_output": prev_output,
            "steps": results,
        }
        self._execution_log.append(execution_record)
        return execution_record


# ═══════════════════════════════════════════════════════════════════
# Endpoint Persistence — JSON save/load
# ═══════════════════════════════════════════════════════════════════



