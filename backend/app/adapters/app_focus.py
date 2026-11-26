from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from app.adapters.base import SourceAdapter
from app.core.redaction import redact_event_subject_and_attributes
from app.schemas.events import CanonicalEvent, RawEvent

APP_FOCUS_ALLOWED_ATTRIBUTES: Set[str] = {
    "app_name",
    "context_tag",
    "domain",
    "tab_count",
}


class AppFocusAdapter(SourceAdapter):
    """Adapter for application focus activity (app name, context tag, start, duration)."""

    source_type = "app_focus"
    allowed_attributes = APP_FOCUS_ALLOWED_ATTRIBUTES

    def normalize(
        self, raw: RawEvent, ctx: Optional[Dict[str, Any]] = None
    ) -> List[CanonicalEvent]:
        payload = raw.payload

        # Subject can be a document/context identifier or app name
        raw_subject = payload.get("subject") or payload.get("context_tag") or payload.get("app_name")

        raw_attrs = payload.get("attributes", {}) or {}
        for key in ("app_name", "context_tag", "domain", "tab_count"):
            if key in payload and key not in raw_attrs:
                raw_attrs[key] = payload[key]

        filtered_attrs = {
            k: v
            for k, v in raw_attrs.items()
            if k in self.allowed_attributes and isinstance(v, (str, int, float, bool))
        }

        cleaned_subject, cleaned_attrs = redact_event_subject_and_attributes(
            raw_subject, filtered_attrs
        )
        if raw_subject is not None and cleaned_subject is None:
            return []

        metrics: Dict[str, float] = {}
        if "focus_percent" in payload and isinstance(payload["focus_percent"], (int, float)) and not isinstance(payload["focus_percent"], bool):
            metrics["focus_percent"] = float(payload["focus_percent"])

        occurred_at_val = payload.get("occurred_at") or payload.get("start_time")
        if isinstance(occurred_at_val, str):
            occurred_at = datetime.fromisoformat(occurred_at_val.replace("Z", "+00:00"))
        elif isinstance(occurred_at_val, datetime):
            occurred_at = occurred_at_val
        else:
            occurred_at = datetime.now(timezone.utc)

        duration = float(payload.get("duration_seconds", 0.0) or payload.get("duration", 0.0) or 0.0)

        event = CanonicalEvent(
            event_id=uuid4(),
            source_type=raw.source_type,
            source_name=raw.source_name,
            event_kind=str(payload.get("event_kind", "app_focus")),
            occurred_at=occurred_at,
            duration_seconds=duration,
            subject=cleaned_subject,
            container=payload.get("container"),
            metrics=metrics,
            attributes=cleaned_attrs,
        )
        return [event]
