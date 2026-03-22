from app.ingest.normalizer import ParsedDocumentNormalizer
from app.ingest.parsed_document import ParsedBlock, ParsedDocument, ParsedPage, ParsedRelation


def test_normalizer_preserves_localized_evidence_and_relations() -> None:
    parsed = ParsedDocument(
        document_id="doc_pdf",
        source_kind="pdf",
        metadata={
            "title": "Sample Paper",
            "page_count": 1,
            "localized_evidence_count": 2,
            "relation_count": 2,
        },
        pages=[
            ParsedPage(
                page_no=1,
                blocks=[
                    ParsedBlock(
                        block_id="p0001_b0001",
                        kind="heading",
                        text="Introduction",
                        page_no=1,
                        reading_order=1,
                    ),
                    ParsedBlock(
                        block_id="p0001_b0002",
                        kind="paragraph",
                        text="The core idea lives here.",
                        page_no=1,
                        reading_order=2,
                    ),
                ],
                localized_evidence=[
                    ParsedBlock(
                        block_id="p0001_b0003",
                        kind="paragraph",
                        text="The core idea lives here.",
                        page_no=1,
                        reading_order=3,
                        provenance={"layer": "supporting"},
                    ),
                    ParsedBlock(
                        block_id="p0001_b0004",
                        kind="figure",
                        text="Figure 1",
                        page_no=1,
                        reading_order=4,
                    ),
                ],
                relations=[
                    ParsedRelation(
                        relation_id="rel_0001_evidence",
                        kind="localized_evidence_for_block",
                        source_block_id="p0001_b0003",
                        target_block_id="p0001_b0002",
                        score=1.0,
                        provenance={"strategy": "text_overlap"},
                    ),
                    ParsedRelation(
                        relation_id="rel_0001_nearby",
                        kind="nearby_paragraph_for_figure",
                        source_block_id="p0001_b0004",
                        target_block_id="p0001_b0002",
                        score=0.5,
                        provenance={"strategy": "nearest_paragraph"},
                    ),
                ],
            )
        ],
    )

    document = ParsedDocumentNormalizer().normalize(parsed)

    assert document.metadata.page_count == 1
    assert document.metadata.localized_evidence_count == 2
    assert document.metadata.relation_count == 2
    assert set(document.localized_evidence) == {"evi_0001", "evi_0002"}
    assert document.localized_evidence["evi_0001"].text == "The core idea lives here."
    assert document.relations[0].source_id == "evi_0001"
    assert document.relations[0].target_id == "para_0001"
    assert document.relations[1].source_id == "evi_0002"
    assert document.relations[1].target_id == "para_0001"
