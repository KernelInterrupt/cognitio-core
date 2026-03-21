from app.domain.document_ir import ParagraphNode, SectionNode
from app.ingest import DocumentSource, IngestRouter


def test_text_source_is_ingested_into_ir() -> None:
    router = IngestRouter()
    source = DocumentSource.from_text("Intro\n\nThis is a paragraph.\n\nAnother paragraph.")

    document = router.ingest_to_ir(source)

    assert document.metadata.source_kind == "text"
    assert any(
        isinstance(document.nodes[node_id], ParagraphNode)
        for node_id in document.reading_order
    )


def test_heading_like_block_becomes_section_node() -> None:
    router = IngestRouter()
    source = DocumentSource.from_text("INTRODUCTION\n\nBody paragraph.")

    document = router.ingest_to_ir(source)

    first_node = document.nodes[document.reading_order[0]]
    assert isinstance(first_node, SectionNode)
    assert first_node.title == "INTRODUCTION"
