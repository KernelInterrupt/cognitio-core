from app.domain.document_ir import (
    DocumentIR,
    DocumentMetadata,
    DocumentNode,
    DocumentRelation,
    LocalizedEvidence,
    ParagraphNode,
    Provenance,
    SectionNode,
)
from app.runtime.tool_registry import ToolRegistry


def _build_document() -> DocumentIR:
    return DocumentIR(
        document_id="doc_runtime",
        root_id="doc_root",
        metadata=DocumentMetadata(
            title="Runtime Test",
            source_kind="pdf",
            page_count=1,
            localized_evidence_count=2,
            relation_count=2,
        ),
        nodes={
            "doc_root": DocumentNode(id="doc_root", order_index=0, title="Runtime Test"),
            "sec_0001": SectionNode(
                id="sec_0001",
                order_index=1,
                parent_id="doc_root",
                title="Introduction",
                provenance=Provenance(source_kind="pdf", pdf_page=1),
            ),
            "para_0001": ParagraphNode(
                id="para_0001",
                order_index=2,
                parent_id="sec_0001",
                text="The core idea lives here.",
                provenance=Provenance(source_kind="pdf", pdf_page=1),
            ),
        },
        reading_order=["sec_0001", "para_0001"],
        localized_evidence={
            "evi_0001": LocalizedEvidence(
                id="evi_0001",
                kind="paragraph",
                text="The core idea lives here.",
                page_no=1,
                reading_order=3,
                provenance={"layer": "supporting"},
            ),
            "evi_0002": LocalizedEvidence(
                id="evi_0002",
                kind="figure",
                text="Figure 1",
                page_no=1,
                reading_order=4,
            ),
        },
        relations=[
            DocumentRelation(
                relation_id="rel_0001_evidence",
                kind="localized_evidence_for_block",
                source_id="evi_0001",
                target_id="para_0001",
                score=1.0,
            ),
            DocumentRelation(
                relation_id="rel_0001_nearby",
                kind="nearby_paragraph_for_figure",
                source_id="evi_0002",
                target_id="para_0001",
                score=0.5,
            ),
        ],
        created_at="2026-03-23T00:00:00+00:00",
    )


def test_document_handle_supports_page_and_evidence_queries() -> None:
    tools = ToolRegistry()
    document = tools.bind_document(_build_document())

    page = document.page(1)
    assert [node.node_id for node in page.paragraphs()] == ["para_0001"]
    assert [evidence.evidence_id for evidence in page.localized_evidence()] == [
        "evi_0001",
        "evi_0002",
    ]

    paragraph = document.select("para_0001")
    assert paragraph.kind == "paragraph"
    assert paragraph.page_no == 1
    assert paragraph.text_content() == "The core idea lives here."
    assert [evidence.evidence_id for evidence in paragraph.localized_evidence()] == ["evi_0001"]


def test_document_handle_supports_text_selection_and_relation_lookup() -> None:
    tools = ToolRegistry()
    document = tools.bind_document(_build_document())

    paragraph = document.select_first(kind="paragraph", text_contains="core idea")
    assert paragraph is not None
    assert paragraph.node_id == "para_0001"

    figure_relations = document.relations_for("evi_0002", kind="nearby_paragraph_for_figure")
    assert len(figure_relations) == 1
    assert figure_relations[0].target_id == "para_0001"
