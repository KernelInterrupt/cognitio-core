from app.document.navigator import DocumentNavigator
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


def _build_document() -> DocumentIR:
    return DocumentIR(
        document_id="doc_navigation",
        root_id="doc_root",
        metadata=DocumentMetadata(
            title="Navigator Test",
            source_kind="pdf",
            page_count=1,
            localized_evidence_count=2,
            relation_count=3,
        ),
        nodes={
            "doc_root": DocumentNode(id="doc_root", order_index=0, title="Navigator Test"),
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
            "para_0002": ParagraphNode(
                id="para_0002",
                order_index=3,
                parent_id="sec_0001",
                text="Figure 1: Attention layout overview.",
                provenance=Provenance(source_kind="pdf", pdf_page=1),
            ),
        },
        reading_order=["sec_0001", "para_0001", "para_0002"],
        localized_evidence={
            "evi_0001": LocalizedEvidence(
                id="evi_0001",
                kind="paragraph",
                text="The core idea lives here.",
                page_no=1,
                reading_order=4,
            ),
            "evi_0002": LocalizedEvidence(
                id="evi_0002",
                kind="figure",
                text="Figure 1",
                page_no=1,
                reading_order=5,
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
                relation_id="rel_0001_caption",
                kind="caption_of_figure",
                source_id="para_0002",
                target_id="evi_0002",
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


def test_document_navigator_keeps_document_queries_pure() -> None:
    navigator = DocumentNavigator(_build_document())

    assert navigator.node_ids_on_page(1, kind="paragraph") == ["para_0001", "para_0002"]
    assert navigator.evidence_ids_on_page(1, kind="figure") == ["evi_0002"]
    assert (
        navigator.select_first_node_id(kind="paragraph", text_contains="core idea")
        == "para_0001"
    )
    assert (
        navigator.select_first_evidence_id(kind="figure", text_contains="Figure 1")
        == "evi_0002"
    )


def test_document_navigator_exposes_relation_traversal_without_runtime_actions() -> None:
    navigator = DocumentNavigator(_build_document())

    assert navigator.localized_evidence_ids_for("para_0001") == ["evi_0001"]
    assert navigator.caption_node_ids_for("evi_0002") == ["para_0002"]
    assert navigator.nearby_paragraph_node_ids_for("evi_0002") == ["para_0001"]
    assert len(navigator.relations_for("evi_0002")) == 2
