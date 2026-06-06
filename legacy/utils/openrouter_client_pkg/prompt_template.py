
"""
openrouter_client_pkg/prompt_template.py — PromptTemplate
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class PromptTemplate:
    """
    Prompt template with variable interpolation.

    Supports {{variable}} syntax and conditional blocks.
    """

    def __init__(self, template: str, name: str = "") -> None:
        self.template = template
        self.name = name

    def render(self, variables: Dict[str, Any]) -> str:
        """Render template with variables."""
        result = self.template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def extract_variables(self) -> List[str]:
        """Extract variable names from template."""
        import re
        return re.findall(r"\{\{(\w+)\}\}", self.template)




