
"""
api_builder_pkg/pipeline.py — Pipeline
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class Pipeline:
    """Multi-step model pipeline definition."""
    pipeline_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    steps: List[PipelineStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    
    def add_step(self, name: str, model_key: str, **kwargs) -> "Pipeline":
        self.steps.append(PipelineStep(name=name, model_key=model_key, **kwargs))
        return self  # For chaining




