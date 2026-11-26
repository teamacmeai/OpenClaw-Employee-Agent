from typing import Any, Dict, List, Optional, Protocol, Set, runtime_checkable
from app.schemas.events import CanonicalEvent, RawEvent


class UnsupportedSourceError(Exception):
    """Raised when an adapter for a source_type is not registered."""

    def __init__(self, source_type: str) -> None:
        super().__init__(f"Unsupported source type: {source_type}")
        self.source_type = source_type


@runtime_checkable
class SourceAdapter(Protocol):
    """Protocol that all source adapters must implement."""

    source_type: str
    allowed_attributes: Set[str]

    def normalize(
        self, raw: RawEvent, ctx: Optional[Dict[str, Any]] = None
    ) -> List[CanonicalEvent]:
        """Normalize a raw event into zero or more canonical events."""
        ...


class AdapterRegistry:
    """Registry for looking up source adapters by source_type."""

    def __init__(self) -> None:
        self._adapters: Dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        self._adapters[adapter.source_type] = adapter

    def get(self, source_type: str) -> SourceAdapter:
        adapter = self._adapters.get(source_type)
        if not adapter:
            raise UnsupportedSourceError(source_type)
        return adapter

    def list_sources(self) -> List[str]:
        return list(self._adapters.keys())
