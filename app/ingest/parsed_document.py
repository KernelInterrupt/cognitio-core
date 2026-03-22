from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ParsedSpan(BaseModel):
    text: str
    bbox: tuple[float, float, float, float] | None = None


class ParsedBlock(BaseModel):
    block_id: str
    kind: Literal[
        "paragraph",
        "heading",
        "figure",
        "table",
        "equation",
        "code",
        "list",
        "unknown",
    ]
    text: str = ""
    page_no: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    reading_order: int
    spans: list[ParsedSpan] = Field(default_factory=list)
    provenance: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ParsedRelation(BaseModel):
    relation_id: str
    kind: Literal[
        "localized_evidence_for_block",
        "caption_of_figure",
        "caption_of_table",
        "caption_of_equation",
        "nearby_paragraph_for_figure",
        "nearby_paragraph_for_table",
        "nearby_paragraph_for_equation",
    ]
    source_block_id: str
    target_block_id: str
    score: float | None = None
    provenance: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ParsedPage(BaseModel):
    page_no: int
    width: float | None = None
    height: float | None = None
    image_path: str | None = None
    text_layer: str | None = None
    blocks: list[ParsedBlock] = Field(default_factory=list)
    localized_evidence: list[ParsedBlock] = Field(default_factory=list)
    relations: list[ParsedRelation] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    document_id: str
    source_kind: Literal["text", "pdf", "latex"]
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    pages: list[ParsedPage] = Field(default_factory=list)

    @property
    def blocks(self) -> list[ParsedBlock]:
        return [block for page in self.pages for block in page.blocks]

    @property
    def localized_evidence(self) -> list[ParsedBlock]:
        return [block for page in self.pages for block in page.localized_evidence]

    @property
    def relations(self) -> list[ParsedRelation]:
        return [relation for page in self.pages for relation in page.relations]
