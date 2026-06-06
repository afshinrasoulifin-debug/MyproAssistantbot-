
"""Client layer — AI client wrappers."""
try:
    from arki_project.infrastructure.clients.unified_client import UnifiedClient
    from arki_project.infrastructure.clients.multi_client import MultiClient
    from arki_project.infrastructure.clients.smart_client import SmartClient
    from arki_project.infrastructure.clients.stealth_client import StealthClient
    from arki_project.infrastructure.clients.headless_client import HeadlessClient
    from arki_project.infrastructure.clients.automation_client import AutomationClient
    from arki_project.infrastructure.clients.cloud_client import CloudClient
except (ImportError, ModuleNotFoundError):
    try:
        from infrastructure.clients.unified_client import UnifiedClient
        from infrastructure.clients.multi_client import MultiClient
        from infrastructure.clients.smart_client import SmartClient
        from infrastructure.clients.stealth_client import StealthClient
        from infrastructure.clients.headless_client import HeadlessClient
        from infrastructure.clients.automation_client import AutomationClient
        from infrastructure.clients.cloud_client import CloudClient
    except (ImportError, ModuleNotFoundError):
        UnifiedClient = None  # type: ignore
        MultiClient = None  # type: ignore
        SmartClient = None  # type: ignore
        StealthClient = None  # type: ignore
        HeadlessClient = None  # type: ignore
        AutomationClient = None  # type: ignore
        CloudClient = None  # type: ignore


