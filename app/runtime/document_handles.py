from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.document_ir import DocumentIR, DocumentRelation, LocalizedEvidence

if TYPE_CHECKING:
    from app.runtime.node_handle import NodeHandle
    from app.runtime.tool_registry import ToolRegistry


@dataclass
class LocalizedEvidenceHandle:
    evidence_id: str
    tools: ToolRegistry

    @property
    def evidence(self) -> LocalizedEvidence:
        return self.tools.get_evidence(self.evidence_id)

    @property
    def kind(self) -> str:
        return self.evidence.kind

    @property
    def text(self) -> str:
        return self.evidence.text

    @property
    def page_no(self) -> int | None:
        return self.evidence.page_no

    def relations(self, kind: str | None = None) -> list[DocumentRelation]:
        return self.tools.relations_for(self.evidence_id, kind=kind)

    def caption_nodes(self) -> list[NodeHandle]:
        return self.tools.captions_of(self.evidence_id)

    def nearby_paragraphs(self) -> list[NodeHandle]:
        return self.tools.nearby_paragraphs_of(self.evidence_id)


@dataclass
class PageHandle:
    page_no: int
    tools: ToolRegistry

    def nodes(self, kind: str | None = None) -> list[NodeHandle]:
        node_ids = self.tools.node_ids_on_page(self.page_no, kind)
        return [self.tools.select(node_id) for node_id in node_ids]

    def paragraphs(self) -> list[NodeHandle]:
        return self.nodes(kind="paragraph")

    def sections(self) -> list[NodeHandle]:
        return self.nodes(kind="section")

    def localized_evidence(self, kind: str | None = None) -> list[LocalizedEvidenceHandle]:
        return [
            LocalizedEvidenceHandle(evidence_id=evidence_id, tools=self.tools)
            for evidence_id in self.tools.evidence_ids_on_page(self.page_no, kind)
        ]

    def figures(self) -> list[LocalizedEvidenceHandle]:
        return self.localized_evidence(kind="figure")

    def select_paragraph(self, text_contains: str | None = None) -> NodeHandle | None:
        return self.tools.select_first(
            kind="paragraph",
            text_contains=text_contains,
            page_no=self.page_no,
        )

    def select_figure(self, text_contains: str | None = None) -> LocalizedEvidenceHandle | None:
        return self.tools.select_first_evidence(
            kind="figure",
            text_contains=text_contains,
            page_no=self.page_no,
        )


@dataclass
class DocumentHandle:
    document: DocumentIR
    tools: ToolRegistry

    def page(self, page_no: int) -> PageHandle:
        return PageHandle(page_no=page_no, tools=self.tools)

    def pages(self) -> list[PageHandle]:
        page_count = self.document.metadata.page_count or 0
        return [self.page(page_no) for page_no in range(1, page_count + 1)]

    def select(self, node_id: str) -> NodeHandle:
        return self.tools.select(node_id)

    def select_first(
        self,
        *,
        kind: str | None = None,
        text_contains: str | None = None,
        page_no: int | None = None,
    ) -> NodeHandle | None:
        return self.tools.select_first(kind=kind, text_contains=text_contains, page_no=page_no)

    def select_paragraph(
        self,
        text_contains: str | None = None,
        *,
        page_no: int | None = None,
    ) -> NodeHandle | None:
        return self.select_first(kind="paragraph", text_contains=text_contains, page_no=page_no)

    def figures(self, *, page_no: int | None = None) -> list[LocalizedEvidenceHandle]:
        if page_no is None:
            return [
                LocalizedEvidenceHandle(evidence_id=evidence_id, tools=self.tools)
                for evidence_id in self.document.localized_evidence
                if self.document.localized_evidence[evidence_id].kind == "figure"
            ]
        return self.page(page_no).figures()

    def select_figure(
        self,
        text_contains: str | None = None,
        *,
        page_no: int | None = None,
    ) -> LocalizedEvidenceHandle | None:
        return self.tools.select_first_evidence(
            kind="figure",
            text_contains=text_contains,
            page_no=page_no,
        )

    def select_near_figure(
        self,
        text_contains: str | None = None,
        *,
        page_no: int | None = None,
    ) -> NodeHandle | None:
        figure = self.select_figure(text_contains=text_contains, page_no=page_no)
        if figure is None:
            return None
        nearby = figure.nearby_paragraphs()
        return nearby[0] if nearby else None

    def evidence_for(
        self,
        node_id: str,
        kind: str | None = None,
    ) -> list[LocalizedEvidenceHandle]:
        return self.tools.localized_evidence_for(node_id, kind=kind)

    def captions_of(self, target_id: str) -> list[NodeHandle]:
        return self.tools.captions_of(target_id)

    def nearby_paragraphs_of(self, target_id: str) -> list[NodeHandle]:
        return self.tools.nearby_paragraphs_of(target_id)

    def relations_for(self, target_id: str, kind: str | None = None) -> list[DocumentRelation]:
        return self.tools.relations_for(target_id, kind=kind)
