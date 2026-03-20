from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.signals import HighlightLevel


class Annotation(BaseModel):
    annotation_id: str
    target_node_id: str
    type: Literal["summary", "intuition", "critique", "highlight"]
    language: str = "zh"
    importance_level: HighlightLevel = "normal"
    status: Literal["draft", "editing", "compiled", "failed"] = "draft"
    rendered_content: str | None = None


class CompileError(BaseModel):
    line: int | None = None
    message: str
    snippet: str | None = None
    code: str | None = None


class CompileResult(BaseModel):
    ok: bool
    rendered_content: str | None = None
    errors: list[CompileError] = Field(default_factory=list)
