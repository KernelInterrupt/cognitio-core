from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Event(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class DocumentIngestedPayload(BaseModel):
    document_id: str
    node_count: int


class ReadingModeInferredPayload(BaseModel):
    value: str
    source: Literal["inferred", "user", "system"]


class ReadingPlanCreatedPayload(BaseModel):
    key_nodes: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    skip_hints: list[str] = Field(default_factory=list)


class RunStartedPayload(BaseModel):
    run_id: str
    provider: str
    permission_tier: str


class ReadingProgressPayload(BaseModel):
    run_id: str
    node_id: str
    stage: str


class AnnotationOpenedPayload(BaseModel):
    annotation_id: str
    target_node_id: str
    type: str
    language: str
    importance_level: str
    status: str
    rendered_content: str | None = None


class AnnotationCompileFailedPayload(BaseModel):
    annotation_id: str
    errors: list[dict[str, Any]] = Field(default_factory=list)


class AnnotationCompiledPayload(BaseModel):
    annotation_id: str
    rendered_content: str
    workspace_id: str


class AdviceGeneratedPayload(BaseModel):
    advice_id: str
    scope: str
    target_id: str
    kind: str
    message: str
    basis: list[str] = Field(default_factory=list)


class RunAwaitingUserInputPayload(BaseModel):
    run_id: str
    node_id: str
    interventions: list[dict[str, Any]] = Field(default_factory=list)


class ResearchRequestedPayload(BaseModel):
    node_id: str
    goal: str
    scope: str | None = None


class RunCompletedPayload(BaseModel):
    run_id: str


def build_event(type_: str, payload: BaseModel | dict[str, Any]) -> Event:
    if isinstance(payload, BaseModel):
        data = payload.model_dump(mode="json")
    else:
        data = payload
    return Event(type=type_, payload=data)
