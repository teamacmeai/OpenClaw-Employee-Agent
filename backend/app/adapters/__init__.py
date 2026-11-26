from app.adapters.app_focus import AppFocusAdapter
from app.adapters.base import AdapterRegistry, SourceAdapter, UnsupportedSourceError
from app.adapters.file_activity import FileActivityAdapter
from app.adapters.generic import GenericAdapter


def get_default_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(GenericAdapter())
    registry.register(FileActivityAdapter())
    registry.register(AppFocusAdapter())
    return registry


__all__ = [
    "AdapterRegistry",
    "SourceAdapter",
    "UnsupportedSourceError",
    "GenericAdapter",
    "FileActivityAdapter",
    "AppFocusAdapter",
    "get_default_registry",
]
