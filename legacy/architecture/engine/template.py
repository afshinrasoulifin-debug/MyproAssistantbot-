
from __future__ import annotations
"""
architecture.engine.template — TemplateEngine
═════════════════════════════════════════════
Prompt template engine with variable substitution, conditionals, and inheritance.
Covers: template-engine
"""
import logging, re, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional



logger = logging.getLogger(__name__)

@dataclass
class Template:
    name: str
    content: str
    parent: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

class TemplateEngine:
    """Template rendering with inheritance, variables, and conditionals."""
    def __init__(self) -> None:
        self._templates: Dict[str, Template] = {}

    def register(self, name: str, content: str, parent: Optional[str] = None,
                 defaults: Optional[Dict[str, Any]] = None) -> Template:
        tmpl = Template(name=name, content=content, parent=parent,
                        variables=defaults or {})
        self._templates[name] = tmpl
        return tmpl

    def render(self, name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        tmpl = self._templates.get(name)
        if not tmpl:
            raise KeyError(f"Template '{name}' not found")
        # Resolve inheritance
        content = tmpl.content
        if tmpl.parent and tmpl.parent in self._templates:
            parent_content = self.render(tmpl.parent, variables)
            content = parent_content.replace("{{CHILD}}", content)
        # Merge variables
        vars_ = {**tmpl.variables, **(variables or {})}
        # Substitute {{var}} patterns
        def _sub(match):
            key = match.group(1).strip()
            return str(vars_.get(key, match.group(0)))
        content = re.sub(r"\{\{(\w+)\}\}", _sub, content)
        # Process conditionals: {%if var%}...{%endif%}
        def _cond(match):
            var_name = match.group(1).strip()
            body = match.group(2)
            if vars_.get(var_name):
                return body
            return ""
        content = re.sub(r"\{%\s*if\s+(\w+)\s*%\}(.*?)\{%\s*endif\s*%\}", _cond, content, flags=re.DOTALL)
        return content

    def render_string(self, template_str: str, variables: Optional[Dict[str, Any]] = None) -> str:
        vars_ = variables or {}
        def _sub(match):
            key = match.group(1).strip()
            return str(vars_.get(key, match.group(0)))
        return re.sub(r"\{\{(\w+)\}\}", _sub, template_str)

    def list_templates(self) -> List[str]:
        return list(self._templates.keys())


