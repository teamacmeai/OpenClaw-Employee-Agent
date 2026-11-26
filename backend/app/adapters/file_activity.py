from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from app.adapters.base import SourceAdapter
from app.core.redaction import redact_event_subject_and_attributes
from app.schemas.events import CanonicalEvent, RawEvent

FILE_ACTIVITY_ALLOWED_ATTRIBUTES: Set[str] = {
    "change_type",
    "language_id",
    "extension",
}


class FileActivityAdapter(SourceAdapter):
    """Adapter for file-based activity (file change counts, line deltas).

    Maps to v1.0 contract fields conceptually without coupling other components.
    """

    source_type = "file_activity"
    allowed_attributes = FILE_ACTIVITY_ALLOWED_ATTRIBUTES

    def normalize(
        self, raw: RawEvent, ctx: Optional[Dict[str, Any]] = None
    ) -> List[CanonicalEvent]:
        payload = raw.payload
        raw_subject = payload.get("file_path") or payload.get("subject")
        if not raw_subject:
            return []

        raw_attrs = payload.get("attributes", {}) or {}
        # Also map explicit top-level fields into attributes if present
        if "change_type" in payload and "change_type" not in raw_attrs:
            raw_attrs["change_type"] = payload["change_type"]
        if "language_id" in payload and "language_id" not in raw_attrs:
            raw_attrs["language_id"] = payload["language_id"]
        if "extension" in payload and "extension" not in raw_attrs:
            raw_attrs["extension"] = payload["extension"]

        filtered_attrs = {
            k: v
            for k, v in raw_attrs.items()
            if k in self.allowed_attributes and isinstance(v, (str, int, float, bool))
        }

        cleaned_subject, cleaned_attrs = redact_event_subject_and_attributes(
            raw_subject, filtered_attrs
        )
        if cleaned_subject is None:
            # Sensitive subject dropped (e.g. .env, *.pem)
            return []

        metrics: Dict[str, float] = {}
        for key in ("lines_added", "lines_removed", "lines_changed"):
            if key in payload and isinstance(payload[key], (int, float)) and not isinstance(payload[key], bool):
                metrics[key] = float(payload[key])

        occurred_at_val = payload.get("occurred_at") or payload.get("timestamp")
        if isinstance(occurred_at_val, str):
            occurred_at = datetime.fromisoformat(occurred_at_val.replace("Z", "+00:00"))
        elif isinstance(occurred_at_val, datetime):
            occurred_at = occurred_at_val
        else:
            occurred_at = datetime.now(timezone.utc)

        duration = float(payload.get("duration_seconds", 0.0) or 0.0)

        event = CanonicalEvent(
            event_id=uuid4(),
            source_type=raw.source_type,
            source_name=raw.source_name,
            event_kind=str(payload.get("event_kind", "file_change")),
            occurred_at=occurred_at,
            duration_seconds=duration,
            subject=cleaned_subject,
            container=payload.get("container") or payload.get("workspace"),
            metrics=metrics,
            attributes=cleaned_attrs,
        )
        return [event]
