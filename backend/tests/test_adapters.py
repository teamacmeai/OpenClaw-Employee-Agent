import json
from pathlib import Path
from typing import Any, Dict, List
import pytest

from app.adapters import (
    AdapterRegistry,
    AppFocusAdapter,
    FileActivityAdapter,
    GenericAdapter,
    SourceAdapter,
    UnsupportedSourceError,
    get_default_registry,
)
from app.core.containers import ContainerResolver
from app.core.redaction import (
    is_sensitive_subject,
    redact_attributes,
    redact_event_subject_and_attributes,
    scrub_string,
)
from app.schemas.events import CanonicalEvent, IngestBatch, RawEvent


def test_models_validation() -> None:
    raw = RawEvent(
        source_type="generic",
        source_name="test-source",
        payload={"event_kind": "commit", "metrics": {"count": 1}},
    )
    assert raw.source_type == "generic"

    batch = IngestBatch(
        batch_id="batch-001",
        sent_at="2026-11-26T10:00:00Z",
        events=[raw],
    )
    assert batch.schema_version == "1.0"
    assert len(batch.events) == 1

    # Max 500 events limit
    oversized_events = [raw] * 501
    with pytest.raises(Exception):
        IngestBatch(
            batch_id="batch-002",
            sent_at="2026-11-26T10:00:00Z",
            events=oversized_events,
        )


def test_redaction_sensitive_subjects() -> None:
    assert is_sensitive_subject(".env")
    assert is_sensitive_subject("/path/to/.env")
    assert is_sensitive_subject("C:\\repo\\.env.local")
    assert is_sensitive_subject("certs/server.pem")
    assert is_sensitive_subject("/home/user/.ssh/id_rsa")
    assert is_sensitive_subject("secrets.yaml")
    assert is_sensitive_subject("credentials.json")

    assert not is_sensitive_subject("main.py")
    assert not is_sensitive_subject("/repo/src/App.tsx")
    assert not is_sensitive_subject(None)


def test_redaction_secrets_in_attributes() -> None:
    token_str = "bearer sk-12345678901234567890123456"
    assert "[REDACTED_SECRET]" in scrub_string(token_str)

    attrs = {
        "status": "success",
        "header": "bearer sk-12345678901234567890123456",
        "gh_token": "ghp_123456789012345678901234567890",
        "num": 42,
    }
    cleaned = redact_attributes(attrs)
    assert cleaned["status"] == "success"
    assert cleaned["num"] == 42
    assert cleaned["header"] == "[REDACTED_SECRET]"
    assert cleaned["gh_token"] == "[REDACTED_SECRET]"


def test_container_resolver() -> None:
    rules = [
        {"source_type": "file_activity", "prefix": "/repo/backend/", "container": "backend-ws"},
        {"source_type": "file_activity", "regex": "\\.service$", "container": "services"},
        {"source_type": "*", "regex": "auth", "container": "auth-ws"},
    ]
    resolver = ContainerResolver(rules)

    assert resolver.resolve("file_activity", "/repo/backend/main.py") == "backend-ws"
    assert resolver.resolve("file_activity", "/etc/systemd/app.service") == "services"
    assert resolver.resolve("generic", "auth-token-gen") == "auth-ws"
    assert resolver.resolve("generic", "other-thing") is None
    assert resolver.resolve("generic", None) is None


def test_adapter_registry_and_unsupported_source() -> None:
    registry = AdapterRegistry()
    generic = GenericAdapter()
    registry.register(generic)

    assert registry.get("generic") == generic

    with pytest.raises(UnsupportedSourceError) as exc_info:
        registry.get("unknown_source")
    assert exc_info.value.source_type == "unknown_source"


def test_plug_in_new_adapter() -> None:
    # Demonstrates: Adding a new source requires only a new adapter file and a registry line
    class CustomToolAdapter(SourceAdapter):
        source_type = "custom_tool"
        allowed_attributes = {"step_name"}

        def normalize(
            self, raw: RawEvent, ctx: Any = None
        ) -> List[CanonicalEvent]:
            return [
                CanonicalEvent(
                    source_type=raw.source_type,
                    source_name=raw.source_name,
                    event_kind="custom_step",
                    occurred_at="2026-11-26T10:00:00Z",
                    subject="custom-task",
                    attributes={"step_name": raw.payload.get("step_name")},
                )
            ]

    registry = AdapterRegistry()
    registry.register(CustomToolAdapter())

    raw = RawEvent(
        source_type="custom_tool",
        source_name="tool-runner",
        payload={"step_name": "build"},
    )
    events = registry.get("custom_tool").normalize(raw)
    assert len(events) == 1
    assert events[0].attributes["step_name"] == "build"
    assert events[0].event_kind == "custom_step"


def test_generic_adapter_filtering_and_event_kinds() -> None:
    adapter = GenericAdapter()

    # file_change
    raw = RawEvent(
        source_type="generic",
        source_name="vcs",
        payload={
            "event_kind": "commit",
            "occurred_at": "2026-11-26T10:00:00Z",
            "subject": "commit/123",
            "metrics": {"files_count": 2, "invalid_str_metric": "not_a_num"},
            "attributes": {
                "hash": "abc1234",
                "branch": "main",
                "message": "fix bug",
                "forbidden_attr": "secret_leak",
            },
        },
    )
    events = adapter.normalize(raw)
    assert len(events) == 1
    ev = events[0]
    assert ev.event_kind == "commit"
    assert ev.metrics == {"files_count": 2.0}
    assert "hash" in ev.attributes and ev.attributes["hash"] == "abc1234"
    assert "branch" in ev.attributes and ev.attributes["branch"] == "main"
    assert "message" in ev.attributes and ev.attributes["message"] == "fix bug"
    assert "forbidden_attr" not in ev.attributes


def test_file_activity_sensitive_subject_dropped() -> None:
    adapter = FileActivityAdapter()
    raw = RawEvent(
        source_type="file_activity",
        source_name="editor",
        payload={
            "file_path": "/app/.env",
            "event_kind": "file_change",
            "occurred_at": "2026-11-26T10:00:00Z",
            "lines_added": 10,
        },
    )
    events = adapter.normalize(raw)
    assert len(events) == 0  # Dropped due to sensitive file


def test_fixtures_normalization_and_container_resolution() -> None:
    fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "ingest_batches.json"
    rules_path = Path(__file__).resolve().parents[2] / "config" / "container_rules.json"

    assert fixture_path.is_file(), f"Missing fixtures file: {fixture_path}"
    assert rules_path.is_file(), f"Missing container rules file: {rules_path}"

    resolver = ContainerResolver.from_file(rules_path)
    registry = get_default_registry()

    with open(fixture_path, "r", encoding="utf-8") as f:
        batches_data = json.load(f)

    assert len(batches_data) == 3, "Expected 3 fixture batches"

    all_normalized_events: List[CanonicalEvent] = []

    for batch_dict in batches_data:
        batch = IngestBatch.model_validate(batch_dict)
        for raw_event in batch.events:
            adapter = registry.get(raw_event.source_type)
            norm_events = adapter.normalize(raw_event)
            for ev in norm_events:
                # If container is not set on event, resolve using container rules
                if not ev.container:
                    ev.container = resolver.resolve(ev.source_type, ev.subject)
                all_normalized_events.append(ev)

    # Check that events from all three sources were normalized
    sources = {ev.source_type for ev in all_normalized_events}
    assert sources == {"file_activity", "generic", "app_focus"}

    # Check required event kinds
    event_kinds = {ev.event_kind for ev in all_normalized_events}
    required_kinds = {
        "file_change",
        "commit",
        "command_run",
        "browser_activity",
        "idle_block",
        "session_start",
        "session_end",
    }
    assert required_kinds.issubset(event_kinds), f"Missing kinds: {required_kinds - event_kinds}"

    # Verify container resolution worked on matched subjects
    frontend_events = [ev for ev in all_normalized_events if ev.subject and "frontend" in ev.subject]
    assert len(frontend_events) > 0
    assert frontend_events[0].container == "frontend-workspace"

    # Verify sensitive subject (.env in batch 1) was dropped
    env_events = [ev for ev in all_normalized_events if ev.subject and ".env" in ev.subject]
    assert len(env_events) == 0

    # Verify secret scrubbing worked on attributes
    cmd_events = [ev for ev in all_normalized_events if ev.event_kind == "command_run"]
    assert len(cmd_events) > 0
    assert "[REDACTED_SECRET]" in cmd_events[0].attributes.get("message", "")
