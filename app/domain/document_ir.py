from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    source_kind: Literal["text", "pdf", "latex"]
    language: str | None = None


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


class DocumentIR(BaseModel):
    document_id: str
    root_id: str
    metadata: DocumentMetadata
    nodes: dict[str, IRNode]
    reading_order: list[str]
    created_at: str
    ir_version: str = "1.0"

