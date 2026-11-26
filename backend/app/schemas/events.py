from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field


class CanonicalEvent(BaseModel):
    """Normalized, canonical activity event."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    source_type: str
    source_name: str
    event_kind: str
    occurred_at: datetime
    duration_seconds: float = Field(default=0.0, ge=0.0)
    subject: Optional[str] = None
    container: Optional[str] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class RawEvent(BaseModel):
    """Raw incoming event from an external source or collector."""

    model_config = ConfigDict(extra="forbid")

    source_type: str
    source_name: str
    payload: Dict[str, Any]


class IngestBatch(BaseModel):
    """Batch of raw events sent to the ingest endpoint."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    batch_id: str
    sent_at: datetime
    events: List[RawEvent] = Field(..., max_length=500)
