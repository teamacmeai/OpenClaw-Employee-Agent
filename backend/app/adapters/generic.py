from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from app.adapters.base import SourceAdapter
from app.core.redaction import redact_event_subject_and_attributes
from app.schemas.events import CanonicalEvent, RawEvent

GENERIC_ALLOWED_ATTRIBUTES: Set[str] = {
    # Commit allow-listed attributes
    "hash",
    "branch",
    "message",
    # Command run allow-listed attributes
    "command",
    "status",
    # Browser activity allow-listed attributes
    "domain",
    "tab_count",
    # Idle block allow-listed attributes
    "reason",
    # Session / generic allow-listed attributes
    "session_id",
    "action",
    "status_code",
    "environment",
}


class GenericAdapter(SourceAdapter):
    """Adapter for payloads that already arrive in canonical shape.

    Drops non-allow-listed attributes and keeps only numeric metrics.
    """

    source_type = "generic"
    allowed_attributes = GENERIC_ALLOWED_ATTRIBUTES

    def __init__(self, allowed_attributes: Optional[Set[str]] = None) -> None:
        if allowed_attributes is not None:
            self.allowed_attributes = allowed_attributes

    def normalize(
        self, raw: RawEvent, ctx: Optional[Dict[str, Any]] = None
    ) -> List[CanonicalEvent]:
        payload = raw.payload

        # Subject check and redaction
        raw_subject = payload.get("subject")
        raw_attrs = payload.get("attributes", {}) or {}

        # Filter attributes by allow-list
        filtered_attrs: Dict[str, Any] = {}
        for k, v in raw_attrs.items():
            if k in self.allowed_attributes and isinstance(v, (str, int, float, bool)):
                filtered_attrs[k] = v

        cleaned_subject, cleaned_attrs = redact_event_subject_and_attributes(
            raw_subject, filtered_attrs
        )
        if raw_subject is not None and cleaned_subject is None:
            # Sensitive subject dropped
            return []

        # Keep only numeric metrics
        raw_metrics = payload.get("metrics", {}) or {}
        cleaned_metrics: Dict[str, float] = {}
        for k, v in raw_metrics.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cleaned_metrics[k] = float(v)

        # Parse occurred_at
        occurred_at_val = payload.get("occurred_at")
        if isinstance(occurred_at_val, str):
            occurred_at = datetime.fromisoformat(occurred_at_val.replace("Z", "+00:00"))
        elif isinstance(occurred_at_val, datetime):
            occurred_at = occurred_at_val
        else:
            occurred_at = datetime.now(timezone.utc)

        # Event ID
        event_id_val = payload.get("event_id")
        if isinstance(event_id_val, str):
            try:
                event_id = UUID(event_id_val)
            except ValueError:
                event_id = uuid4()
        elif isinstance(event_id_val, UUID):
            event_id = event_id_val
        else:
            event_id = uuid4()

        event = CanonicalEvent(
            event_id=event_id,
            source_type=raw.source_type,
            source_name=raw.source_name,
            event_kind=str(payload.get("event_kind", "unknown")),
            occurred_at=occurred_at,
            duration_seconds=float(payload.get("duration_seconds", 0.0) or 0.0),
            subject=cleaned_subject,
            container=payload.get("container"),
            metrics=cleaned_metrics,
            attributes=cleaned_attrs,
        )
        return [event]
