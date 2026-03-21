from __future__ import annotations

from app.ingest.base import IngestBackend
from app.ingest.parsed_document import ParsedBlock, ParsedDocument, ParsedPage
from app.ingest.source import DocumentSource


class PlainTextBackend(IngestBackend):
    name = "plain_text"

    def sniff(self, source: DocumentSource) -> bool:
        media_type = source.media_type or ""
        return bool(source.text is not None or media_type.startswith("text/"))

    def ingest(self, source: DocumentSource) -> ParsedDocument:
        raw_text = source.text or ""
        chunks = [chunk.strip() for chunk in raw_text.split("\n\n") if chunk.strip()]
        page = ParsedPage(page_no=1, text_layer=raw_text)
        for index, chunk in enumerate(chunks, start=1):
            block_kind = "heading" if _looks_like_heading(chunk) else "paragraph"
            page.blocks.append(
                ParsedBlock(
                    block_id=f"block_{index}",
                    kind=block_kind,
                    text=chunk,
                    page_no=1,
                    reading_order=index,
                    provenance={"backend": self.name},
                )
            )
        return ParsedDocument(
            document_id=source.filename or "doc_001",
            source_kind="text",
            metadata={"backend": self.name},
            pages=[page],
        )


def _looks_like_heading(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        return False
    line = lines[0]
    if len(line) > 80:
        return False
    alpha_ratio = sum(ch.isalpha() for ch in line) / max(len(line), 1)
    return line == line.title() or (
        alpha_ratio > 0.6 and not line.endswith(":") and line.isupper()
    )
