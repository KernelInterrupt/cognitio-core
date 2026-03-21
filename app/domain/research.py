from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    task_id: str
    node_id: str
    goal: str
    scope: str | None = None
    node_text: str | None = None
    reading_mode: str | None = None


class ResearchFinding(BaseModel):
    kind: Literal["background", "constraint", "transfer_note", "critique", "risk"]
    content: str


class ResearchTask(BaseModel):
    task_id: str
    node_id: str
    goal: str
    scope: str | None = None
    status: Literal["queued", "running", "completed", "failed"] = "queued"


class ResearchResult(BaseModel):
    task_id: str
    node_id: str
    goal: str
    findings: list[ResearchFinding] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

