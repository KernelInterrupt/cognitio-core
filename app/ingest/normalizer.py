from __future__ import annotations

from datetime import UTC, datetime

from app.domain.document_ir import (
    DocumentIR,
    DocumentMetadata,
    DocumentNode,
    EquationNode,
    FigureNode,
    ParagraphNode,
    Provenance,
    SectionNode,
    TableNode,
)
from app.ingest.parsed_document import ParsedBlock, ParsedDocument


class ParsedDocumentNormalizer:
    def normalize(self, parsed: ParsedDocument) -> DocumentIR:
        root_id = "doc_root"
        nodes: dict[
            str, DocumentNode | SectionNode | ParagraphNode | EquationNode | FigureNode | TableNode
        ] = {
            root_id: DocumentNode(
                id=root_id,
                order_index=0,
                title=_as_str(parsed.metadata.get("title")),
                provenance=None,
            )
        }
        reading_order: list[str] = []
        current_parent_id = root_id
        section_index = 0
        paragraph_index = 0
        figure_index = 0
        table_index = 0
        equation_index = 0

        for block in parsed.blocks:
            provenance = _to_provenance(parsed.source_kind, block)
            if block.kind == "heading":
                section_index += 1
                node_id = f"sec_{section_index:04d}"
                node = SectionNode(
                    id=node_id,
                    order_index=block.reading_order,
                    parent_id=root_id,
                    title=block.text.strip(),
                    provenance=provenance,
                )
                nodes[node_id] = node
                nodes[root_id].children.append(node_id)
                reading_order.append(node_id)
                current_parent_id = node_id
                continue

            if block.kind == "paragraph":
                paragraph_index += 1
                node_id = f"para_{paragraph_index:04d}"
                node = ParagraphNode(
                    id=node_id,
                    order_index=block.reading_order,
                    parent_id=current_parent_id,
                    text=block.text,
                    provenance=provenance,
                )
            elif block.kind == "figure":
                figure_index += 1
                node_id = f"fig_{figure_index:04d}"
                node = FigureNode(
                    id=node_id,
                    order_index=block.reading_order,
                    parent_id=current_parent_id,
                    caption=block.text or None,
                    provenance=provenance,
                )
            elif block.kind == "table":
                table_index += 1
                node_id = f"tbl_{table_index:04d}"
                node = TableNode(
                    id=node_id,
                    order_index=block.reading_order,
                    parent_id=current_parent_id,
                    caption=block.text or None,
                    provenance=provenance,
                )
            else:
                equation_index += 1
                node_id = f"eq_{equation_index:04d}"
                node = EquationNode(
                    id=node_id,
                    order_index=block.reading_order,
                    parent_id=current_parent_id,
                    text_repr=block.text or None,
                    provenance=provenance,
                )

            nodes[node_id] = node
            nodes[current_parent_id].children.append(node_id)
            reading_order.append(node_id)

        return DocumentIR(
            document_id=parsed.document_id,
            root_id=root_id,
            metadata=DocumentMetadata(source_kind=parsed.source_kind),
            nodes=nodes,
            reading_order=reading_order,
            created_at=datetime.now(UTC).isoformat(),
        )


def _to_provenance(source_kind: str, block: ParsedBlock) -> Provenance:
    return Provenance(
        source_kind=source_kind,
        pdf_page=block.page_no if source_kind == "pdf" else None,
        pdf_bbox=block.bbox if source_kind == "pdf" else None,
    )


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None
