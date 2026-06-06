
"""Aggregator layer — aggregate data from multiple sources."""
try:
    from arki_project.infrastructure.aggregator.ai_aggregator import AIAggregator
    from arki_project.infrastructure.aggregator.response_aggregator import ResponseAggregator
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.aggregator.ai_aggregator import AIAggregator
        from infrastructure.aggregator.response_aggregator import ResponseAggregator
    except (ImportError, ModuleNotFoundError):
        AIAggregator = None  # type: ignore
        ResponseAggregator = None  # type: ignore


