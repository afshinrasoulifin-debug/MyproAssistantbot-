
"""Engine layer — specialized processing engines."""
try:
    from arki_project.infrastructure.engines.inference_engine import InferenceEngine
    from arki_project.infrastructure.engines.reasoning_engine import ReasoningEngine
    from arki_project.infrastructure.engines.completion_engine import CompletionEngine
    from arki_project.infrastructure.engines.optimization_engine import OptimizationEngine
    from arki_project.infrastructure.engines.adaptive_engine import AdaptiveEngine
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.engines.inference_engine import InferenceEngine
        from infrastructure.engines.reasoning_engine import ReasoningEngine
        from infrastructure.engines.completion_engine import CompletionEngine
        from infrastructure.engines.optimization_engine import OptimizationEngine
        from infrastructure.engines.adaptive_engine import AdaptiveEngine
    except (ImportError, ModuleNotFoundError):
        InferenceEngine = None  # type: ignore
        ReasoningEngine = None  # type: ignore
        CompletionEngine = None  # type: ignore
        OptimizationEngine = None  # type: ignore
        AdaptiveEngine = None  # type: ignore


