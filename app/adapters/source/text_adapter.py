from __future__ import annotations

from datetime import UTC, datetime

from app.domain.document_ir import DocumentIR, DocumentMetadata, DocumentNode, ParagraphNode


class TextAdapter:
    """Minimal MVP adapter: split by blank lines into paragraph nodes."""

    def parse(self, raw_text: str, document_id: str = "doc_001") -> DocumentIR:
        root_id = "doc_root"
        nodes: dict[str, DocumentNode | ParagraphNode] = {
            root_id: DocumentNode(
                id=root_id,
                order_index=0,
                title=None,
                provenance=None,
            )
        }
        reading_order: list[str] = []

        paragraphs = [chunk.strip() for chunk in raw_text.split("\n\n") if chunk.strip()]
        for index, paragraph in enumerate(paragraphs, start=1):
            node_id = f"p_{index}"
            reading_order.append(node_id)
            nodes[node_id] = ParagraphNode(
                id=node_id,
                order_index=index,
                parent_id=root_id,
                text=paragraph,
            )
            nodes[root_id].children.append(node_id)

        return DocumentIR(
            document_id=document_id,
            root_id=root_id,
            metadata=DocumentMetadata(source_kind="text"),
            nodes=nodes,
            reading_order=reading_order,
            created_at=datetime.now(UTC).isoformat(),
        )

