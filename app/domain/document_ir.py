from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

JsonScalar = str | int | float | bool | None


class DocumentMetadata(BaseModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    source_kind: Literal["text", "pdf", "latex"]
    language: str | None = None
    page_count: int | None = None
    localized_evidence_count: int = 0
    relation_count: int = 0


class Provenance(BaseModel):
    source_kind: Literal["text", "pdf", "latex"]
    pdf_page: int | None = None
    pdf_bbox: tuple[float, float, float, float] | None = None
    latex_file: str | None = None
    latex_line_start: int | None = None
    latex_line_end: int | None = None


class TextSpan(BaseModel):
    start: int
    end: int
    type: Literal["plain", "emphasis", "math", "citation_ref", "term"]
    text: str


class BaseNode(BaseModel):
    id: str
    kind: Literal["document", "section", "paragraph", "equation", "figure", "table"]
    parent_id: str | None = None
    children: list[str] = Field(default_factory=list)
    order_index: int
    provenance: Provenance | None = None


class DocumentNode(BaseNode):
    kind: Literal["document"] = "document"
    title: str | None = None


class SectionNode(BaseNode):
    kind: Literal["section"] = "section"
    title: str
    level: int = 1


class ParagraphNode(BaseNode):
    kind: Literal["paragraph"] = "paragraph"
    text: str
    spans: list[TextSpan] = Field(default_factory=list)


class EquationNode(BaseNode):
    kind: Literal["equation"] = "equation"
    latex: str | None = None
    text_repr: str | None = None


class FigureNode(BaseNode):
    kind: Literal["figure"] = "figure"
    caption: str | None = None


class TableNode(BaseNode):
    kind: Literal["table"] = "table"
    caption: str | None = None


IRNode = Annotated[
    DocumentNode | SectionNode | ParagraphNode | EquationNode | FigureNode | TableNode,
    Field(discriminator="kind"),
]


class LocalizedEvidence(BaseModel):
    id: str
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
    provenance: dict[str, JsonScalar] = Field(default_factory=dict)


class DocumentRelation(BaseModel):
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
    source_id: str
    target_id: str
    score: float | None = None
    provenance: dict[str, JsonScalar] = Field(default_factory=dict)


class DocumentIR(BaseModel):
    document_id: str
    root_id: str
    metadata: DocumentMetadata
    nodes: dict[str, IRNode]
    reading_order: list[str]
    localized_evidence: dict[str, LocalizedEvidence] = Field(default_factory=dict)
    relations: list[DocumentRelation] = Field(default_factory=list)
    created_at: str
    ir_version: str = "1.0"
