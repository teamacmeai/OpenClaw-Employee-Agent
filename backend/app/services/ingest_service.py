import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from psycopg import Connection

from app.adapters import get_default_registry
from app.adapters.base import AdapterRegistry, UnsupportedSourceError
from app.core.containers import ContainerResolver
from app.core.redaction import is_sensitive_subject, redact_event_subject_and_attributes
from app.repositories.ingest_repo import IngestRepository
from app.schemas.events import CanonicalEvent, IngestBatch
from app.services.auth_service import DeviceIdentity

logger = logging.getLogger(__name__)


@dataclass
class RejectionItem:
    index: int
    reason: str


@dataclass
class IngestResult:
    batch_id: str
    accepted: int
    rejected: List[RejectionItem]
    duplicate: bool


class IngestService:
    """Service to process incoming batches: adapter normalize, redaction, container resolution, and storage."""

    def __init__(
        self,
        conn: Connection,
        registry: Optional[AdapterRegistry] = None,
        container_resolver: Optional[ContainerResolver] = None,
    ) -> None:
        self.conn = conn
        self.repo = IngestRepository(conn)
        self.registry = registry or get_default_registry()
        if container_resolver is not None:
            self.container_resolver = container_resolver
        else:
            # Look for config/container_rules.json from repo root or parent dirs
            candidate = Path("config/container_rules.json")
            if not candidate.is_file():
                candidate = Path(__file__).resolve().parent.parent.parent.parent / "config" / "container_rules.json"
            self.container_resolver = ContainerResolver.from_file(candidate)

    def ingest(self, identity: DeviceIdentity, batch: IngestBatch) -> IngestResult:
        # Check if already ingested as duplicate
        existing = self.repo.get_batch_by_workstation_and_batch_id(
            identity.workstation_id, batch.batch_id
        )
        if existing:
            return IngestResult(
                batch_id=batch.batch_id,
                accepted=existing["event_count"],
                rejected=[],
                duplicate=True,
            )

        valid_canonical_events: List[CanonicalEvent] = []
        rejections: List[RejectionItem] = []

        for idx, raw_event in enumerate(batch.events):
            try:
                adapter = self.registry.get(raw_event.source_type)
            except UnsupportedSourceError as e:
                rejections.append(RejectionItem(index=idx, reason=str(e)))
                continue

            # Check if raw subject or file_path is sensitive before adapter drops it
            raw_subj = raw_event.payload.get("subject") or raw_event.payload.get("file_path")
            if raw_subj and is_sensitive_subject(raw_subj):
                rejections.append(RejectionItem(index=idx, reason="Event dropped due to sensitive subject"))
                continue

            try:
                events = adapter.normalize(raw_event)
            except Exception as e:
                logger.warning("Event normalization failed for index %d: %s", idx, e)
                rejections.append(RejectionItem(index=idx, reason=f"Normalization failed: {type(e).__name__}"))
                continue

            if not events:
                rejections.append(RejectionItem(index=idx, reason="Event produced no canonical events"))
                continue

            # Process each normalized canonical event: redaction + container resolution
            for ev in events:
                # Sensitive subjects (like .env, secrets) are dropped
                clean_subject, clean_attrs = redact_event_subject_and_attributes(ev.subject, ev.attributes)
                if ev.subject and not clean_subject:
                    # Dropped due to sensitive subject
                    rejections.append(RejectionItem(index=idx, reason="Event dropped due to sensitive subject"))
                    break

                # Resolve container if not set or update via resolver
                resolved_container = ev.container
                if not resolved_container and clean_subject:
                    resolved_container = self.container_resolver.resolve(ev.source_type, clean_subject)

                normalized_event = ev.model_copy(
                    update={
                        "subject": clean_subject,
                        "attributes": clean_attrs,
                        "container": resolved_container,
                    }
                )
                valid_canonical_events.append(normalized_event)

        # Insert into database in a single transaction
        batch_record_id = uuid4()
        batch_row, is_duplicate = self.repo.insert_batch_with_events(
            batch_record_id=batch_record_id,
            workstation_id=identity.workstation_id,
            employee_id=identity.employee_id,
            batch_id=batch.batch_id,
            events=valid_canonical_events,
            received_at=None,
        )

        return IngestResult(
            batch_id=batch.batch_id,
            accepted=batch_row["event_count"] if is_duplicate else len(valid_canonical_events),
            rejected=rejections,
            duplicate=is_duplicate,
        )
