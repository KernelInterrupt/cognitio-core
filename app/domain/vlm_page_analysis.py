from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PageImageRef(BaseModel):
    page_no: int
    image_path: str
    text_layer: str | None = None


class VlmPageBlock(BaseModel):
    kind: Literal["heading", "paragraph", "figure", "table", "equation", "code", "unknown"]
    layer: Literal["primary", "supporting"] = "primary"
    text: str = ""
    bbox: tuple[float, float, float, float] | None = None
    reading_order: int
    rationale: str | None = None


class VlmPageWarning(BaseModel):
    kind: str
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    evidence: list[str] = Field(default_factory=list)


class VlmPageAnalysis(BaseModel):
    page_no: int
    summary: str | None = None
    dominant_page_type: Literal[
        "paper_body",
        "title_page",
        "figure_heavy",
        "table_heavy",
        "appendix",
        "manual_step_page",
        "scan_like",
        "unknown",
    ] = "unknown"
    blocks: list[VlmPageBlock] = Field(default_factory=list)
    warnings: list[VlmPageWarning] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
