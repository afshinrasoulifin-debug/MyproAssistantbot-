
"""Worker layer — background processing."""
try:
    from arki_project.infrastructure.workers.async_worker import AsyncWorker
    from arki_project.infrastructure.workers.background_worker import BackgroundWorker
    from arki_project.infrastructure.workers.queue_worker import QueueWorker
    from arki_project.infrastructure.workers.task_runner import InfraTaskRunner
    from arki_project.infrastructure.workers.scheduler import InfraScheduler
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.workers.async_worker import AsyncWorker
        from infrastructure.workers.background_worker import BackgroundWorker
        from infrastructure.workers.queue_worker import QueueWorker
        from infrastructure.workers.task_runner import InfraTaskRunner
        from infrastructure.workers.scheduler import InfraScheduler
    except (ImportError, ModuleNotFoundError):
        AsyncWorker = None  # type: ignore
        BackgroundWorker = None  # type: ignore
        QueueWorker = None  # type: ignore
        InfraTaskRunner = None  # type: ignore
        InfraScheduler = None  # type: ignore


