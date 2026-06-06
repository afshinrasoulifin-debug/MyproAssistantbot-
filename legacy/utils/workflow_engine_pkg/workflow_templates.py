
"""
workflow_engine_pkg/workflow_templates.py — WorkflowTemplates
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class WorkflowTemplates:
    """Pre-built workflow templates for common patterns."""

    @staticmethod
    def scan_and_report(target: str) -> Workflow:
        """Template: Scan target → Analyze → Generate report."""
        wf = Workflow("Scan & Report", f"Automated scan of {target}")
        wf.add_node("recon", "Web Reconnaissance", NodeType.TASK,
                     handler="web_recon", parameters={"target": target})
        wf.add_node("analyze", "Analyze Results", NodeType.TASK,
                     handler="data_analyze", parameters={"source": "${nodes.recon.result}"})
        wf.add_node("report", "Generate Report", NodeType.TASK,
                     handler="report_gen", parameters={"data": "${nodes.analyze.result}"})
        wf.add_edge("recon", "analyze")
        wf.add_edge("analyze", "report")
        return wf

    @staticmethod
    def etl_pipeline(source: str, destination: str) -> Workflow:
        """Template: Extract → Transform → Load."""
        wf = Workflow("ETL Pipeline", f"ETL: {source} → {destination}")
        wf.add_node("extract", "Extract Data", NodeType.TASK,
                     handler="extract", parameters={"source": source})
        wf.add_node("validate", "Validate Data", NodeType.TASK,
                     handler="validate", parameters={"data": "${nodes.extract.result}"})
        wf.add_node("check_valid", "Check Validation", NodeType.CONDITION,
                     parameters={"condition": "${nodes.validate.result.valid}"})
        wf.add_node("transform", "Transform Data", NodeType.TASK,
                     handler="transform", parameters={"data": "${nodes.extract.result}"})
        wf.add_node("load", "Load Data", NodeType.TASK,
                     handler="load", parameters={
                         "data": "${nodes.transform.result}",
                         "destination": destination,
                     })
        wf.add_node("alert_invalid", "Alert: Invalid Data", NodeType.TASK,
                     handler="alert", parameters={"message": "Data validation failed"})

        wf.add_edge("extract", "validate")
        wf.add_edge("validate", "check_valid")
        wf.add_edge("check_valid", "transform", EdgeType.CONDITIONAL_TRUE)
        wf.add_edge("check_valid", "alert_invalid", EdgeType.CONDITIONAL_FALSE)
        wf.add_edge("transform", "load")
        return wf

    @staticmethod
    def monitoring_loop(targets: List[str], interval_seconds: int = 60) -> Workflow:
        """Template: Monitor targets → Alert on issues."""
        wf = Workflow("Monitoring Loop", f"Monitor {len(targets)} targets")
        wf.add_node("check_all", "Check All Targets", NodeType.FOR_EACH,
                     parameters={"items": targets})
        wf.add_node("check_target", "Check Target", NodeType.TASK,
                     handler="health_check", parameters={"target": "${loop.item}"})
        wf.add_node("evaluate", "Evaluate Results", NodeType.CONDITION,
                     parameters={"condition": "${nodes.check_target.result.healthy}"})
        wf.add_node("alert", "Send Alert", NodeType.TASK,
                     handler="alert", parameters={
                         "target": "${loop.item}",
                         "status": "unhealthy",
                     })
        wf.add_edge("check_all", "check_target")
        wf.add_edge("check_target", "evaluate")
        wf.add_edge("evaluate", "alert", EdgeType.CONDITIONAL_FALSE)
        return wf

    @staticmethod
    def parallel_search(query: str, engines: Optional[List[str]] = None) -> Workflow:
        """Template: Search multiple engines in parallel → Merge results."""
        engines = engines or ["google", "bing", "duckduckgo"]
        wf = Workflow("Parallel Search", f"Search: {query}")

        for engine in engines:
            wf.add_node(
                f"search_{engine}", f"Search {engine}",
                NodeType.TASK, handler="web_search",
                parameters={"query": query, "engine": engine},
            )

        wf.add_node("merge", "Merge & Deduplicate", NodeType.MERGE,
                     handler="merge_results")
        wf.add_node("rank", "Rank Results", NodeType.TASK,
                     handler="rank_results")

        for engine in engines:
            wf.add_edge(f"search_{engine}", "merge")
        wf.add_edge("merge", "rank")

        return wf


# ═══════════════════════════════════════════════════════════════════
# Workflow Visualizer (ASCII)
# ═══════════════════════════════════════════════════════════════════



