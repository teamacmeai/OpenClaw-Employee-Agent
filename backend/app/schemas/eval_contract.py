"""Pydantic models for the FastAPI <-> OpenClaw evaluation contract.

These mirror the JSON Schemas in `contracts/` (version 1.0). If you change one,
change the other, the fixtures in `fixtures/`, and the contract tests together.
"""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"

EventType = Literal["CREATE", "MODIFY", "RENAME", "DELETE"]
ContextTag = Literal["IDE", "CLI", "BROWSER_WORK", "DESIGN", "DOCS", "COMMS", "OTHER"]
Category = Literal[
    "FEATURE_DEVELOPMENT",
    "DEBUGGING",
    "CODE_REVIEW",
    "DOCUMENTATION",
    "DESIGN",
    "MEETINGS_COMMUNICATION",
    "RESEARCH",
    "OTHER",
]

Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
RoleId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")]
Summary = Annotated[str, Field(min_length=1, max_length=160)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _check_order(start: AwareDatetime, end: AwareDatetime) -> None:
    if end <= start:
        raise ValueError("end must be after start")


# ---------------------------------------------------------------- request ---


class TimeWindow(_Strict):
    start: AwareDatetime
    end: AwareDatetime

    @model_validator(mode="after")
    def _ordered(self):
        _check_order(self.start, self.end)
        return self


class FileEvent(_Strict):
    path: Annotated[str, Field(min_length=1, max_length=300)]
    extension: Annotated[str, Field(pattern=r"^(\.[A-Za-z0-9_+-]{1,15})?$")]
    event_type: EventType
    edit_count: Annotated[int, Field(ge=1)]
    lines_added: Annotated[int, Field(ge=0)]
    lines_removed: Annotated[int, Field(ge=0)]
    project: Annotated[str, Field(max_length=64)] | None
    last_event_at: AwareDatetime


class AppFocus(_Strict):
    app_name: Annotated[str, Field(min_length=1, max_length=64)]
    context_tag: ContextTag
    start: AwareDatetime
    duration_seconds: Annotated[int, Field(ge=0)]


class ContextBlock(_Strict):
    start: AwareDatetime
    end: AwareDatetime
    category: Category
    summary: Summary

    @model_validator(mode="after")
    def _ordered(self):
        _check_order(self.start, self.end)
        return self


class Activity(_Strict):
    active_seconds: Annotated[int, Field(ge=0)]
    idle_seconds: Annotated[int, Field(ge=0)]
    file_events: Annotated[list[FileEvent], Field(max_length=200)]
    app_focus: Annotated[list[AppFocus], Field(max_length=50)]


class EvalRequest(_Strict):
    schema_version: Literal["1.0"]
    request_id: Identifier
    employee_id: Identifier
    role_id: RoleId
    session_id: Identifier
    timezone: Annotated[str, Field(min_length=1, max_length=64)]
    window: TimeWindow
    activity: Activity
    recent_context: Annotated[list[ContextBlock], Field(max_length=5)]


# --------------------------------------------------------------- response ---


class WorkBlock(_Strict):
    start: AwareDatetime
    end: AwareDatetime
    category: Category
    project: Annotated[str, Field(max_length=64)] | None
    summary: Summary
    active_minutes: Annotated[float, Field(ge=0, le=1440)]
    confidence: Annotated[float, Field(ge=0, le=1)]
    files_referenced: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=300)]],
        Field(max_length=10),
    ]

    @model_validator(mode="after")
    def _valid(self):
        _check_order(self.start, self.end)
        if len(set(self.files_referenced)) != len(self.files_referenced):
            raise ValueError("files_referenced must not contain duplicates")
        return self


class EvalResponse(_Strict):
    schema_version: Literal["1.0"]
    request_id: Identifier
    work_blocks: Annotated[list[WorkBlock], Field(max_length=12)]
    needs_review: bool
    review_reason: Annotated[str, Field(max_length=200)] | None

    @model_validator(mode="after")
    def _review_rules(self):
        if self.needs_review and not self.review_reason:
            raise ValueError("review_reason is required when needs_review is true")
        if not self.needs_review and self.review_reason is not None:
            raise ValueError("review_reason must be null when needs_review is false")
        return self
