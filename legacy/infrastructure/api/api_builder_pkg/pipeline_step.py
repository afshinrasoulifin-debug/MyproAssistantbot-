
"""
api_builder_pkg/pipeline_step.py — PipelineStep
Arki Engine v29.0.0
"""
from ._base import *  # noqa

@dataclass
class PipelineStep:
    """One step in a model pipeline."""
    name: str
    model_key: str  # or endpoint_id
    system_prompt: str = ""
    input_transform: str = ""  # Template: {prev_output}, {original_input}
    temperature: float = 0.7
    max_tokens: int = 65536
    condition: str = ""  # Simple condition: "len(prev_output) > 100"




