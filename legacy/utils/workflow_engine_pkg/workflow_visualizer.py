
"""
workflow_engine_pkg/workflow_visualizer.py — WorkflowVisualizer
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class WorkflowVisualizer:
    """Generate ASCII visualization of workflows."""

    @staticmethod
    def render(workflow: Workflow) -> str:
        """Render workflow as ASCII diagram."""
        lines = [
            f"╔══ Workflow: {workflow.name} ═══",
            f"║  Status: {workflow.status_code.value}",
            f"║  Nodes: {len(workflow.nodes)} | Edges: {len(workflow.edges)}",
            "╠══════════════════════════════════",
        ]

        groups = workflow.dag.get_independent_groups()
        for level, group in enumerate(groups):
            lines.append(f"║  Level {level}:")
            for node_id in group:
                node = workflow.nodes[node_id]
                status_icon = {
                    NodeStatus.PENDING: "○",
                    NodeStatus.RUNNING: "◉",
                    NodeStatus.COMPLETED: "●",
                    NodeStatus.FAILED: "✗",
                    NodeStatus.SKIPPED: "◌",
                }.get(node.status_code, "?")

                duration = ""
                if node.duration():
                    duration = f" ({node.duration():.2f}s)"

                lines.append(
                    f"║    {status_icon} [{node.node_type.value}] "
                    f"{node.name}{duration}"
                )

            if level < len(groups) - 1:
                lines.append("║      │")
                lines.append("║      ▼")

        lines.append("╚══════════════════════════════════")
        return "\n".join(lines)



